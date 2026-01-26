"""Config flow for Homedics SereneScent integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult

from .const import DEVICE_NAME_PREFIX, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HomedicsSereneScentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Homedics SereneScent.

    Supports auto-discovery of multiple devices and manual selection.
    """

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    def _get_configured_addresses(self) -> set[str]:
        """Get set of already configured device addresses."""
        return {
            entry.data.get(CONF_ADDRESS)
            for entry in self._async_current_entries()
            if entry.data.get(CONF_ADDRESS)
        }

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle bluetooth discovery.

        Called automatically when a matching device is discovered.
        Each device triggers a separate flow instance.
        """
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Check if already configured via data (belt and suspenders)
        if discovery_info.address in self._get_configured_addresses():
            return self.async_abort(reason="already_configured")

        self._discovery_info = discovery_info
        _LOGGER.debug(
            "Discovered SereneScent device: %s (%s)",
            discovery_info.name,
            discovery_info.address,
        )

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm bluetooth discovery."""
        assert self._discovery_info is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name,
                data={CONF_ADDRESS: self._discovery_info.address},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name,
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device.

        Scans for all available SereneScent devices and presents a list
        for selection. If only one unconfigured device is found, it will
        be automatically selected.
        """
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()

            discovery_info = self._discovered_devices[address]

            return self.async_create_entry(
                title=discovery_info.name,
                data={CONF_ADDRESS: address},
            )

        # Get already configured addresses
        configured_addresses = self._get_configured_addresses()
        current_flow_ids = self._async_current_ids()

        # Scan for all SereneScent devices
        self._discovered_devices = {}
        for discovery_info in async_discovered_service_info(self.hass):
            # Skip if already configured
            if discovery_info.address in configured_addresses:
                continue

            # Skip if already in another flow
            if discovery_info.address in current_flow_ids:
                continue

            # Skip if already in our list
            if discovery_info.address in self._discovered_devices:
                continue

            # Check if it's a SereneScent device
            if self._is_homedics_device(discovery_info.name):
                self._discovered_devices[discovery_info.address] = discovery_info
                _LOGGER.debug(
                    "Found unconfigured device: %s (%s)",
                    discovery_info.name,
                    discovery_info.address,
                )

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        # If only one device found, skip selection and go directly to confirm
        if len(self._discovered_devices) == 1:
            address = next(iter(self._discovered_devices))
            self._discovery_info = self._discovered_devices[address]
            return await self.async_step_bluetooth_confirm()

        # Multiple devices found - let user select
        data_schema = vol.Schema(
            {
                vol.Required(CONF_ADDRESS): vol.In(
                    {
                        address: f"{info.name} ({address})"
                        for address, info in self._discovered_devices.items()
                    }
                )
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            description_placeholders={
                "count": str(len(self._discovered_devices)),
            },
        )

    @staticmethod
    def _is_homedics_device(name: str | None) -> bool:
        """Check if device name matches Homedics SereneScent pattern.

        Device advertises as 'ARPRP-xxx' where xxx is device-specific.
        """
        if name is None:
            return False
        return name.startswith(DEVICE_NAME_PREFIX)
