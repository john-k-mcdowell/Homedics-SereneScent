"""Sensor platform for Homedics SereneScent integration.

Provides read-only sensors for device state (intensity, color).
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_COLOR, SENSOR_INTENSITY
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

    async_add_entities([
        HomedicsSereneScentIntensitySensor(coordinator),
        HomedicsSereneScentColorSensor(coordinator),
    ])


class HomedicsSereneScentBaseSensor(
    CoordinatorEntity[HomedicsSereneScentCoordinator], SensorEntity
):
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


class HomedicsSereneScentIntensitySensor(HomedicsSereneScentBaseSensor):
    """Intensity sensor for Homedics SereneScent."""

    _attr_name = "Intensity"
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize intensity sensor."""
        super().__init__(coordinator, SENSOR_INTENSITY)

    @property
    def native_value(self) -> str | None:
        """Return the intensity level."""
        return self.coordinator.intensity.capitalize()


class HomedicsSereneScentColorSensor(HomedicsSereneScentBaseSensor):
    """Color sensor for Homedics SereneScent."""

    _attr_name = "Color"
    _attr_icon = "mdi:palette"

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize color sensor."""
        super().__init__(coordinator, SENSOR_COLOR)

    @property
    def native_value(self) -> str | None:
        """Return the current color."""
        return self.coordinator.color.capitalize()
