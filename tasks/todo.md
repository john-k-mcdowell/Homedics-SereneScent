# Light Entity Color Wheel - Task Plan

## Goal
Replace the effects-based color selection with a color wheel UI, mapping user-selected colors to the closest available device color. Keep "rotating" as an effect since it's a behavior mode, not a static color.

## Current Behavior
- Light entity uses `ColorMode.ONOFF` with `LightEntityFeature.EFFECT`
- Colors presented as dropdown: white, red, blue, violet, green, orange, rotating
- No visual color representation

## New Behavior
- Light entity uses `ColorMode.HS` (hue/saturation) for color wheel UI
- User picks any color from wheel → mapped to closest device color
- "Rotating" remains as an effect option (separate from color wheel)
- Current color displayed visually on the wheel

---

## Todo Items

### Phase 1: Add Color RGB Definitions
- [x] Add `COLOR_RGB_MAP` to const.py with RGB tuples for each device color
- [x] Add `COLOR_HS_MAP` to const.py with HS values for each device color (for reporting current color)

### Phase 2: Update Light Entity
- [x] Change `_attr_supported_color_modes` from `{ColorMode.ONOFF}` to `{ColorMode.HS}`
- [x] Change `_attr_color_mode` to `ColorMode.HS`
- [x] Update `_attr_effect_list` to only include `["rotating"]`
- [x] Add `hs_color` property to report current color as HS values
- [x] Add helper function to find closest device color from HS input
- [x] Update `async_turn_on()` to handle `hs_color` parameter
- [x] Update `effect` property to only return "rotating" when active

### Phase 3: Version & Testing
- [x] Update version number (0.1.0 → 0.2.0-beta.1)
- [x] Update manifest.json version
- [x] Verify syntax with Python compile check

---

## Technical Details

### RGB Values for Device Colors
| Color   | RGB             | Hue (approx) |
|---------|-----------------|--------------|
| white   | (255, 255, 255) | N/A (no sat) |
| red     | (255, 0, 0)     | 0°           |
| orange  | (255, 165, 0)   | 39°          |
| green   | (0, 255, 0)     | 120°         |
| blue    | (0, 0, 255)     | 240°         |
| violet  | (148, 0, 211)   | 282°         |

### Color Matching Algorithm
1. Convert incoming HS to RGB
2. Calculate Euclidean distance to each device color in RGB space
3. Return the device color with smallest distance
4. Special case: low saturation (< 25%) → white

### Effect Handling
- `effect="rotating"` → send CMD_COLOR_ROTATING
- When static color is set → clear effect, report effect as None

---

## Files to Modify
- `custom_components/homedics_serenescent/const.py` - Add RGB/HS color maps
- `custom_components/homedics_serenescent/light.py` - Update entity implementation
- `custom_components/homedics_serenescent/version.py` - Bump version
- `custom_components/homedics_serenescent/manifest.json` - Bump version

---

## Version Change
- Previous: 0.1.0
- New: 0.2.0-beta.1 (new feature, experimental release)

---

## Review

### Changes Made

1. **const.py** - Added color mapping constants:
   - `COLOR_RGB_MAP`: RGB tuples for 6 static colors (white, red, orange, green, blue, violet)
   - `COLOR_HS_MAP`: HS values for all colors including off and rotating (for UI display)

2. **light.py** - Complete rewrite of color handling:
   - Changed color mode from `ONOFF` to `HS` (enables color wheel UI)
   - Added `_hs_to_rgb()` helper to convert HS to RGB
   - Added `_color_distance()` helper for Euclidean distance calculation
   - Added `_find_closest_color()` to map any HS input to nearest device color
   - Low saturation (<25%) automatically maps to white
   - Effect list reduced to just `["rotating"]`
   - `hs_color` property returns current color as HS tuple
   - `effect` property only returns "rotating" when active, None otherwise
   - `async_turn_on()` handles both `hs_color` and `effect` parameters

3. **version.py & manifest.json** - Version bumped to 0.2.0-beta.1

### Files Modified
- `custom_components/homedics_serenescent/const.py`
- `custom_components/homedics_serenescent/light.py`
- `custom_components/homedics_serenescent/version.py`
- `custom_components/homedics_serenescent/manifest.json`

### User Experience
- Light entity now shows a color wheel instead of dropdown
- Picking any color maps to the closest of 6 device colors
- "Rotating" available as an effect option (separate from color wheel)
- Current color displayed visually on the wheel
