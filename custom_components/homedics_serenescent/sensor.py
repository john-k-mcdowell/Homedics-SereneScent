"""Sensor platform for Homedics SereneScent integration."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_STATUS,
)
from .coordinator import HomedicsSereneScentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homedics SereneScent sensors."""
    coordinator: HomedicsSereneScentCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    sensors = [
        # TODO: Add sensor entities based on device capabilities
        HomedicsSereneScentStatusSensor(coordinator),
    ]

    async_add_entities(sensors)


class HomedicsSereneScentSensor(CoordinatorEntity[HomedicsSereneScentCoordinator], SensorEntity):
    """Base class for Homedics SereneScent sensors."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HomedicsSereneScentCoordinator, sensor_type: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{sensor_type}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return (
            self.coordinator.monitoring_enabled
            and self.coordinator.last_update_success
        )


class HomedicsSereneScentStatusSensor(HomedicsSereneScentSensor):
    """Status sensor for Homedics SereneScent."""

    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize status sensor."""
        super().__init__(coordinator, SENSOR_STATUS)
        self._attr_name = "Status"

    @property
    def native_value(self) -> str | None:
        """Return the status value."""
        return self.coordinator.data.get(self._sensor_type)
