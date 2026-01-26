"""Light platform for Homedics SereneScent integration.

Provides color control using effect presets (white, red, blue, violet, green, orange, rotating).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COLOR_MAP, DOMAIN
from .coordinator import HomedicsSereneScentCoordinator

_LOGGER = logging.getLogger(__name__)

# Available color effects (excluding 'off')
EFFECT_LIST = ["white", "red", "blue", "violet", "green", "orange", "rotating"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homedics SereneScent light."""
    coordinator: HomedicsSereneScentCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ]

    async_add_entities([HomedicsSereneScentLight(coordinator)])


class HomedicsSereneScentLight(
    CoordinatorEntity[HomedicsSereneScentCoordinator], LightEntity
):
    """Light entity for Homedics SereneScent diffuser.

    Controls the LED light with color presets via effects.
    """

    _attr_has_entity_name = True
    _attr_name = "Light"
    _attr_icon = "mdi:lightbulb"
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_light"
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
        """Return True if light is on (not 'off' color)."""
        return self.coordinator.color != "off"

    @property
    def effect(self) -> str | None:
        """Return the current color effect."""
        color = self.coordinator.color
        if color in EFFECT_LIST:
            return color
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        effect = kwargs.get("effect")

        if effect and effect in EFFECT_LIST:
            await self.coordinator.async_set_color(effect)
        elif self.coordinator.color == "off":
            # Default to white when turning on from off
            await self.coordinator.async_set_color("white")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_set_color("off")
