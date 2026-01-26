"""Data coordinator for Homedics SereneScent integration."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CHAR_RX_UUID,
    CHAR_TX_UUID,
    CMD_MODE_HOME,
    CMD_MODE_SCHEDULE,
    CMD_POWER_OFF,
    CMD_POWER_ON,
    CMD_SCHEDULE_OFF,
    CMD_SCHEDULE_ON,
    CMD_SCHEDULE_SYNC,
    CMD_SCHEDULE_UNKNOWN1,
    CMD_SCHEDULE_UNKNOWN2,
    CMD_SETTINGS_SYNC,
    CMD_STATUS_HOME,
    CMD_STATUS_SCHEDULE,
    COLOR_COMMANDS,
    COLOR_MAP,
    COMMAND_DELAY,
    CONNECTION_DELAY_REDUCTION,
    CONNECTION_IDLE_TIMEOUT,
    CONNECTION_MAX_ATTEMPTS,
    CONNECTION_MAX_DELAY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    INTENSITY_COMMANDS,
    INTENSITY_MAP,
    RESP_HEADER,
    STATUS_BYTE_COLOR,
    STATUS_BYTE_INTENSITY,
    STATUS_BYTE_MODE,
    STATUS_BYTE_POWER,
    STATUS_BYTE_SCHEDULE,
)

_LOGGER = logging.getLogger(__name__)


class HomedicsSereneScentCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Homedics SereneScent BLE communication.

    Manages BLE connection, sends commands, and parses status responses.
    Uses a command queue to serialize device communication.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.address: str = config_entry.data["address"]
        self.device_name: str = config_entry.title
        self.config_entry = config_entry

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.address}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

        # Connection management
        self._client: BleakClient | None = None
        self._connection_lock = asyncio.Lock()
        self._last_activity_time: float = 0

        # Response handling
        self._response_event = asyncio.Event()
        self._last_response: bytes | None = None

        # Device state tracking
        self._current_mode: int = 0  # 0=HOME, 1=SCHEDULE
        self._is_on: bool = False
        self._intensity: str = "low"
        self._color: str = "white"
        self._schedule_on: bool = False

        # Background tasks
        self._health_monitor_task: asyncio.Task | None = None

        # Monitoring state
        self._monitoring_enabled: bool = True

        # Adaptive retry delays
        self._connect_delay: float = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            name=self.device_name,
            manufacturer="Homedics",
            model="SereneScent ARMH-973",
            connections={(dr.CONNECTION_BLUETOOTH, self.address)},
        )

    @property
    def monitoring_enabled(self) -> bool:
        """Return True if monitoring is enabled."""
        return self._monitoring_enabled

    @property
    def is_on(self) -> bool:
        """Return True if device is on."""
        return self._is_on

    @property
    def intensity(self) -> str:
        """Return current intensity level."""
        return self._intensity

    @property
    def color(self) -> str:
        """Return current color."""
        return self._color

    @property
    def schedule_on(self) -> bool:
        """Return True if schedule is enabled."""
        return self._schedule_on

    async def _ensure_connected(self) -> BleakClient:
        """Ensure BLE connection is active."""
        async with self._connection_lock:
            if self._client and self._client.is_connected:
                return self._client

            ble_device = bluetooth.async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )

            if not ble_device:
                raise UpdateFailed(f"Device {self.address} not found")

            last_error: Exception | None = None
            for attempt in range(CONNECTION_MAX_ATTEMPTS):
                try:
                    _LOGGER.debug(
                        "Connecting to %s (attempt %d/%d)",
                        self.address,
                        attempt + 1,
                        CONNECTION_MAX_ATTEMPTS,
                    )

                    self._client = await establish_connection(
                        BleakClient, ble_device, self.address
                    )

                    # Subscribe to notifications
                    await self._client.start_notify(
                        CHAR_RX_UUID, self._notification_handler
                    )

                    self._connect_delay = max(
                        self._connect_delay * CONNECTION_DELAY_REDUCTION, 0
                    )
                    self._last_activity_time = time.time()

                    # Start health monitor if not running
                    if self._health_monitor_task is None or self._health_monitor_task.done():
                        self._health_monitor_task = asyncio.create_task(
                            self._monitor_connection_health()
                        )

                    _LOGGER.debug("Connected to %s", self.address)
                    return self._client

                except BleakError as err:
                    last_error = err
                    _LOGGER.debug("Connection attempt %d failed: %s", attempt + 1, err)

                    if self._connect_delay == 0:
                        self._connect_delay = 1.0
                    else:
                        self._connect_delay = min(
                            self._connect_delay * 2, CONNECTION_MAX_DELAY
                        )

                    if attempt < CONNECTION_MAX_ATTEMPTS - 1:
                        await asyncio.sleep(self._connect_delay)

            _LOGGER.warning(
                "Failed to connect to %s after %d attempts: %s (device may be in use by another app)",
                self.address,
                CONNECTION_MAX_ATTEMPTS,
                last_error,
            )
            raise HomeAssistantError(
                f"Cannot connect to device (may be in use by another app): {last_error}"
            )

    async def _disconnect(self) -> None:
        """Disconnect from device."""
        async with self._connection_lock:
            if self._client and self._client.is_connected:
                try:
                    await self._client.stop_notify(CHAR_RX_UUID)
                except BleakError:
                    pass
                try:
                    await self._client.disconnect()
                except BleakError as err:
                    _LOGGER.debug("Error disconnecting: %s", err)
                finally:
                    self._client = None

    def _notification_handler(self, sender: int, data: bytes) -> None:
        """Handle BLE notifications from device."""
        if all(b == 0xFF for b in data) or all(b == 0 for b in data):
            return  # Ignore empty/filler responses

        _LOGGER.debug("Received: %s", data.hex())
        self._last_response = bytes(data)
        self._response_event.set()

    async def _send_command(self, cmd: bytes, wait_response: bool = True) -> bytes | None:
        """Send command to device and optionally wait for response."""
        client = await self._ensure_connected()

        self._response_event.clear()
        self._last_response = None

        _LOGGER.debug("Sending: %s", cmd.hex())
        await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)

        self._last_activity_time = time.time()

        if wait_response:
            try:
                await asyncio.wait_for(self._response_event.wait(), timeout=2.0)
                return self._last_response
            except asyncio.TimeoutError:
                _LOGGER.debug("No response received for command")
                return None

        await asyncio.sleep(COMMAND_DELAY)
        return None

    def _parse_status_response(self, data: bytes) -> None:
        """Parse 16-byte status response."""
        if len(data) < 16:
            _LOGGER.debug("Status response too short: %d bytes", len(data))
            return

        if data[0:2] != RESP_HEADER or data[2] != 0x40:
            _LOGGER.debug("Not a status response: %s", data.hex())
            return

        # Parse intensity
        intensity_val = data[STATUS_BYTE_INTENSITY]
        self._intensity = INTENSITY_MAP.get(intensity_val, "low")

        # Parse color
        color_val = data[STATUS_BYTE_COLOR]
        self._color = COLOR_MAP.get(color_val, "white")

        # Parse schedule status
        self._schedule_on = data[STATUS_BYTE_SCHEDULE] == 1

        # Parse power status
        self._is_on = data[STATUS_BYTE_POWER] == 1

        # Parse mode
        self._current_mode = data[STATUS_BYTE_MODE]

        _LOGGER.debug(
            "Status: power=%s, intensity=%s, color=%s, schedule=%s, mode=%d",
            self._is_on,
            self._intensity,
            self._color,
            self._schedule_on,
            self._current_mode,
        )

    async def async_request_status(self) -> bool:
        """Request current status from device.

        Returns True if a valid status response was received.
        """
        cmd = CMD_STATUS_SCHEDULE if self._current_mode == 1 else CMD_STATUS_HOME
        response = await self._send_command(cmd)
        if response:
            self._parse_status_response(response)
            return True
        return False

    async def async_set_power(self, on: bool) -> None:
        """Turn device on or off."""
        try:
            # Ensure HOME mode for power commands
            if self._current_mode != 0:
                await self._send_command(CMD_MODE_HOME, wait_response=False)
                self._current_mode = 0

            cmd = CMD_POWER_ON if on else CMD_POWER_OFF
            await self._send_command(cmd)

            # Request status to confirm
            status_ok = await self.async_request_status()
            await self._disconnect()

            # Verify we got a response and state changed
            if not status_ok:
                raise HomeAssistantError(
                    "No response from device - may be in use by another app"
                )
            if self._is_on != on:
                raise HomeAssistantError(
                    "Command failed - device state did not change"
                )

            self.async_set_updated_data(self._build_data_dict())
        except (BleakError, HomeAssistantError) as err:
            await self._disconnect()
            _LOGGER.warning("Failed to set power: %s", err)
            raise HomeAssistantError(f"Failed to set power: {err}") from err

    async def async_set_intensity(self, intensity: str) -> None:
        """Set diffuser intensity (low, medium, high)."""
        if intensity not in INTENSITY_COMMANDS:
            _LOGGER.warning("Invalid intensity: %s", intensity)
            return

        try:
            # Ensure HOME mode
            if self._current_mode != 0:
                await self._send_command(CMD_MODE_HOME, wait_response=False)
                self._current_mode = 0

            await self._send_command(INTENSITY_COMMANDS[intensity])

            # Request status to confirm
            status_ok = await self.async_request_status()
            await self._disconnect()

            # Verify we got a response and state changed
            if not status_ok:
                raise HomeAssistantError(
                    "No response from device - may be in use by another app"
                )
            if self._intensity != intensity:
                raise HomeAssistantError(
                    "Command failed - device state did not change"
                )

            self.async_set_updated_data(self._build_data_dict())
        except (BleakError, HomeAssistantError) as err:
            await self._disconnect()
            _LOGGER.warning("Failed to set intensity: %s", err)
            raise HomeAssistantError(f"Failed to set intensity: {err}") from err

    async def async_set_color(self, color: str) -> None:
        """Set light color."""
        if color not in COLOR_COMMANDS:
            _LOGGER.warning("Invalid color: %s", color)
            return

        try:
            # Ensure HOME mode
            if self._current_mode != 0:
                await self._send_command(CMD_MODE_HOME, wait_response=False)
                self._current_mode = 0

            await self._send_command(COLOR_COMMANDS[color])

            # Request status to confirm
            status_ok = await self.async_request_status()
            await self._disconnect()

            # Verify we got a response and state changed
            if not status_ok:
                raise HomeAssistantError(
                    "No response from device - may be in use by another app"
                )
            if self._color != color:
                raise HomeAssistantError(
                    "Command failed - device state did not change"
                )

            self.async_set_updated_data(self._build_data_dict())
        except (BleakError, HomeAssistantError) as err:
            await self._disconnect()
            _LOGGER.warning("Failed to set color: %s", err)
            raise HomeAssistantError(f"Failed to set color: {err}") from err

    async def async_set_schedule(self, on: bool) -> None:
        """Enable or disable schedule."""
        try:
            # Ensure SCHEDULE mode
            if self._current_mode != 1:
                await self._send_command(CMD_MODE_SCHEDULE, wait_response=False)
                await self._send_command(CMD_SCHEDULE_SYNC, wait_response=False)
                self._current_mode = 1

            if on:
                # Schedule ON requires 4-command sequence
                await self._send_command(CMD_SCHEDULE_ON, wait_response=False)
                await self._send_command(CMD_SETTINGS_SYNC, wait_response=False)
                await self._send_command(CMD_SCHEDULE_UNKNOWN1, wait_response=False)
                await self._send_command(CMD_SCHEDULE_UNKNOWN2, wait_response=False)
            else:
                # Schedule OFF is simpler
                await self._send_command(CMD_SCHEDULE_OFF)

            # Request status to confirm
            status_ok = await self.async_request_status()
            await self._disconnect()

            # Verify we got a response and state changed
            if not status_ok:
                raise HomeAssistantError(
                    "No response from device - may be in use by another app"
                )
            if self._schedule_on != on:
                raise HomeAssistantError(
                    "Command failed - device state did not change"
                )

            self.async_set_updated_data(self._build_data_dict())
        except (BleakError, HomeAssistantError) as err:
            await self._disconnect()
            _LOGGER.warning("Failed to set schedule: %s", err)
            raise HomeAssistantError(f"Failed to set schedule: {err}") from err

    def _build_data_dict(self) -> dict[str, Any]:
        """Build data dictionary for entities."""
        return {
            "power": self._is_on,
            "intensity": self._intensity,
            "color": self._color,
            "schedule": self._schedule_on,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from device."""
        try:
            await self.async_request_status()
            # Disconnect immediately after polling to free the device for other apps
            await self._disconnect()
            return self._build_data_dict()
        except HomeAssistantError as err:
            await self._disconnect()
            # Don't log again - already logged in _ensure_connected
            raise UpdateFailed(str(err)) from err
        except BleakError as err:
            await self._disconnect()
            _LOGGER.debug("BLE error during status update: %s", err)
            raise UpdateFailed(f"BLE error: {err}") from err
        except Exception as err:
            await self._disconnect()
            _LOGGER.warning("Unexpected error during status update: %s", err)
            raise UpdateFailed(f"Error: {err}") from err

    async def _monitor_connection_health(self) -> None:
        """Monitor connection and disconnect if idle."""
        while True:
            try:
                await asyncio.sleep(30)

                if self._client and self._client.is_connected:
                    idle_time = time.time() - self._last_activity_time
                    if idle_time > CONNECTION_IDLE_TIMEOUT:
                        _LOGGER.debug("Connection idle for %ds, disconnecting", int(idle_time))
                        await self._disconnect()

            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.error("Health monitor error: %s", err)

    def start_monitoring(self) -> None:
        """Start monitoring."""
        self._monitoring_enabled = True

    async def async_disconnect(self) -> None:
        """Disconnect and cleanup."""
        self._monitoring_enabled = False

        if self._health_monitor_task and not self._health_monitor_task.done():
            self._health_monitor_task.cancel()
            try:
                await self._health_monitor_task
            except asyncio.CancelledError:
                pass

        await self._disconnect()
