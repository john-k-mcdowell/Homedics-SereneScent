"""Light platform for Homedics SereneScent integration.

Provides color control using a color wheel (HS mode) that maps to the closest
available device color (white, red, blue, violet, green, orange).
The "rotating" color cycle is available as an effect.
"""

from __future__ import annotations

import colorsys
import logging
import math
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

from .const import COLOR_HS_MAP, COLOR_RGB_MAP, DOMAIN
from .coordinator import HomedicsSereneScentCoordinator

_LOGGER = logging.getLogger(__name__)

# Effects available
# - "solid": static color (uses current/last selected color)
# - "rotating": cycles through all colors
EFFECT_LIST = ["solid", "rotating"]

# Saturation threshold below which we consider the color to be white
WHITE_SATURATION_THRESHOLD = 25


def _hs_to_rgb(hue: float, saturation: float) -> tuple[int, int, int]:
    """Convert HS color to RGB.

    Args:
        hue: Hue value 0-360
        saturation: Saturation value 0-100

    Returns:
        RGB tuple with values 0-255
    """
    # colorsys uses 0-1 range
    h = hue / 360.0
    s = saturation / 100.0
    r, g, b = colorsys.hsv_to_rgb(h, s, 1.0)
    return (int(r * 255), int(g * 255), int(b * 255))


def _color_distance(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int]) -> float:
    """Calculate Euclidean distance between two RGB colors."""
    return math.sqrt(
        (rgb1[0] - rgb2[0]) ** 2
        + (rgb1[1] - rgb2[1]) ** 2
        + (rgb1[2] - rgb2[2]) ** 2
    )


def _find_closest_color(hue: float, saturation: float) -> str:
    """Find the closest device color to the given HS values.

    Args:
        hue: Hue value 0-360
        saturation: Saturation value 0-100

    Returns:
        Device color name (white, red, orange, green, blue, violet)
    """
    # Low saturation means white
    if saturation < WHITE_SATURATION_THRESHOLD:
        return "white"

    # Convert input HS to RGB
    input_rgb = _hs_to_rgb(hue, saturation)

    # Find closest color by RGB distance
    closest_color = "white"
    min_distance = float("inf")

    for color_name, color_rgb in COLOR_RGB_MAP.items():
        if color_name == "white":
            continue  # Skip white, already handled by saturation check
        distance = _color_distance(input_rgb, color_rgb)
        if distance < min_distance:
            min_distance = distance
            closest_color = color_name

    return closest_color


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

    Controls the LED light with a color wheel interface.
    Colors are mapped to the closest available device color.
    """

    _attr_has_entity_name = True
    _attr_name = "Light"
    _attr_icon = "mdi:lightbulb"
    _attr_supported_color_modes = {ColorMode.HS}
    _attr_color_mode = ColorMode.HS
    _attr_supported_features = LightEntityFeature.EFFECT
    _attr_effect_list = EFFECT_LIST

    def __init__(self, coordinator: HomedicsSereneScentCoordinator) -> None:
        """Initialize the light entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_light"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available.

        Always available when monitoring is enabled, even if device hasn't
        responded yet. This allows users to attempt control when device is off.
        """
        return self.coordinator.monitoring_enabled

    @property
    def is_on(self) -> bool:
        """Return True if light is on (not 'off' color)."""
        return self.coordinator.color != "off"

    @property
    def brightness(self) -> int:
        """Return brightness (always 255 as device has no intensity control for light)."""
        return 255

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the current color as HS values."""
        color = self.coordinator.color
        if color in COLOR_HS_MAP:
            return COLOR_HS_MAP[color]
        return None

    @property
    def effect(self) -> str | None:
        """Return the current effect ('solid' or 'rotating')."""
        color = self.coordinator.color
        if color == "rotating":
            return "rotating"
        if color != "off":
            return "solid"
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        # Check for effect
        effect = kwargs.get("effect")
        if effect == "rotating":
            await self.coordinator.async_set_color("rotating")
            return
        if effect == "solid":
            # If currently rotating or off, switch to last solid color (default white)
            if self.coordinator.color in ("rotating", "off"):
                await self.coordinator.async_set_color("white")
            # Otherwise keep current color (already solid)
            return

        # Check for color from color wheel
        hs_color = kwargs.get("hs_color")
        if hs_color is not None:
            hue, saturation = hs_color
            closest_color = _find_closest_color(hue, saturation)
            _LOGGER.debug(
                "Color wheel input HS(%s, %s) mapped to device color: %s",
                hue,
                saturation,
                closest_color,
            )
            await self.coordinator.async_set_color(closest_color)
            return

        # Brightness is ignored (device doesn't support light intensity)

        # No color specified - if currently off, default to white
        if self.coordinator.color == "off":
            await self.coordinator.async_set_color("white")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.async_set_color("off")
