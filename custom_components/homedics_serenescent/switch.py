"""Switch platform for Homedics SereneScent integration.

Provides schedule control and monitoring toggle switches.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SWITCH_MONITORING, SWITCH_SCHEDULE
from .coordinator import HomedicsSereneScentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homedics SereneScent switches."""
    coordinator: HomedicsSereneScentCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities([
        HomedicsSereneScentScheduleSwitch(coordinator),
        HomedicsSereneScentMonitoringSwitch(coordinator),
    ])


class HomedicsSereneScentScheduleSwitch(
    CoordinatorEntity[HomedicsSereneScentCoordinator], SwitchEntity
):
    """Schedule switch for Homedics SereneScent.

    Controls the device's built-in schedule feature.
    """

    _attr_has_entity_name = True
    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize the schedule switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{SWITCH_SCHEDULE}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.monitoring_enabled
            and self.coordinator.last_update_success
        )

    @property
    def is_on(self) -> bool:
        """Return True if schedule is enabled."""
        return self.coordinator.schedule_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the schedule."""
        await self.coordinator.async_set_schedule(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the schedule."""
        await self.coordinator.async_set_schedule(False)


class HomedicsSereneScentMonitoringSwitch(
    CoordinatorEntity[HomedicsSereneScentCoordinator], SwitchEntity
):
    """Monitoring switch for Homedics SereneScent.

    Controls whether the integration actively polls the device.
    """

    _attr_has_entity_name = True
    _attr_name = "Monitoring"
    _attr_icon = "mdi:connection"
    _attr_entity_registry_enabled_default = False  # Hidden by default

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize the monitoring switch."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{SWITCH_MONITORING}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return True if monitoring is enabled."""
        return self.coordinator.update_interval is not None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable monitoring."""
        self.coordinator.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
        self.coordinator.start_monitoring()
        await self.coordinator.async_refresh()
        self.async_write_ha_state()
        _LOGGER.debug("Monitoring enabled for %s", self.coordinator.address)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable monitoring."""
        self.coordinator.update_interval = None
        await self.coordinator.async_disconnect()
        self.async_write_ha_state()
        _LOGGER.debug("Monitoring disabled for %s", self.coordinator.address)
