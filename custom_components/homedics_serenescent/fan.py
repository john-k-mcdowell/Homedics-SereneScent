"""Fan platform for Homedics SereneScent integration.

Provides power on/off and intensity control (low/medium/high) as fan speed presets.
"""

from __future__ import annotations

import math
import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import DOMAIN
from .coordinator import HomedicsSereneScentCoordinator

_LOGGER = logging.getLogger(__name__)

# Map preset modes to intensity values
PRESET_MODES = ["low", "medium", "high"]

# Speed range for percentage calculation (1=low, 2=medium, 3=high)
SPEED_RANGE = (1, 3)

# Map intensity names to speed values
INTENSITY_TO_SPEED = {"low": 1, "medium": 2, "high": 3}
SPEED_TO_INTENSITY = {1: "low", 2: "medium", 3: "high"}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homedics SereneScent fan."""
    coordinator: HomedicsSereneScentCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities([HomedicsSereneScentFan(coordinator)])


class HomedicsSereneScentFan(
    CoordinatorEntity[HomedicsSereneScentCoordinator], FanEntity
):
    """Fan entity for Homedics SereneScent diffuser.

    Controls power on/off and intensity via preset modes (low, medium, high).
    """

    _attr_has_entity_name = True
    _attr_name = "Diffuser"
    _attr_icon = "mdi:air-humidifier"
    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES
    _attr_speed_count = 3

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize the fan entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_fan"
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
        """Return True if the diffuser is on."""
        return self.coordinator.is_on

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode (intensity level)."""
        return self.coordinator.intensity if self.is_on else None

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        if not self.is_on:
            return 0
        intensity = self.coordinator.intensity
        speed = INTENSITY_TO_SPEED.get(intensity, 1)
        return ranged_value_to_percentage(SPEED_RANGE, speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the diffuser."""
        await self.coordinator.async_set_power(True)

        # If percentage specified, convert to intensity
        if percentage is not None and percentage > 0:
            speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
            intensity = SPEED_TO_INTENSITY.get(speed, "low")
            await self.coordinator.async_set_intensity(intensity)
        # If preset_mode specified, set it
        elif preset_mode and preset_mode in PRESET_MODES:
            await self.coordinator.async_set_intensity(preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the diffuser."""
        await self.coordinator.async_set_power(False)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the intensity preset mode."""
        if preset_mode not in PRESET_MODES:
            _LOGGER.warning("Invalid preset mode: %s", preset_mode)
            return

        # Turn on if not already on
        if not self.is_on:
            await self.coordinator.async_set_power(True)

        await self.coordinator.async_set_intensity(preset_mode)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage."""
        if percentage == 0:
            await self.coordinator.async_set_power(False)
            return

        # Convert percentage to intensity level
        speed = math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage))
        intensity = SPEED_TO_INTENSITY.get(speed, "low")

        # Turn on if not already on
        if not self.is_on:
            await self.coordinator.async_set_power(True)

        await self.coordinator.async_set_intensity(intensity)
