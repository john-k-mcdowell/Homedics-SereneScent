# Light Entity Improvements - Task Plan

## Issues Fixed

### Issue 1: Brightness Slider
- Added `brightness` property that always returns 255
- Brightness changes from UI are ignored (device has no light intensity control)

### Issue 2: Preset Colors
- All device colors now available in effects dropdown: white, red, orange, green, blue, violet, rotating
- Users can use either the color wheel OR the effects dropdown for quick selection

### Issue 3: Startup Availability
- Removed `last_update_success` check from all entities
- Entities are now available whenever monitoring is enabled
- Users can attempt control even when device is powered off
- Errors only shown when commands actually fail

---

## Todo Items

### Light Entity Fixes
- [x] Add `brightness` property that always returns 255
- [x] Handle brightness parameter in `async_turn_on()` (ignore it)
- [x] Add all device colors to effect list (white, red, orange, green, blue, violet, rotating)
- [x] Update effect property to return current color as effect

### Availability Fix
- [x] Fix availability in light.py - remove `last_update_success` check
- [x] Fix availability in fan.py - remove `last_update_success` check
- [x] Fix availability in switch.py - remove `last_update_success` check

### Version & Testing
- [x] Update version to 0.2.0-beta.10
- [x] Verify Python syntax

---

## Version Change
- Previous: 0.2.0-beta.9
- New: 0.2.0-beta.10

---

## Review

### Changes Made

1. **light.py**:
   - Added `brightness` property that always returns 255
   - Added all device colors to `EFFECT_LIST`: white, red, orange, green, blue, violet, rotating
   - Updated `effect` property to return current color (not just "rotating")
   - Changed `available` to only check `monitoring_enabled` (not `last_update_success`)

2. **fan.py**:
   - Changed `available` to only check `monitoring_enabled`

3. **switch.py**:
   - Changed `available` to only check `monitoring_enabled` (schedule switch)

4. **version.py & manifest.json**:
   - Updated version to 0.2.0-beta.10

### Files Modified
- `custom_components/homedics_serenescent/light.py`
- `custom_components/homedics_serenescent/fan.py`
- `custom_components/homedics_serenescent/switch.py`
- `custom_components/homedics_serenescent/version.py`
- `custom_components/homedics_serenescent/manifest.json`

### User Experience Improvements
- Brightness slider always at 100% (device doesn't support light dimming)
- Device colors available as preset effects for quick selection
- Entities remain available even when device is powered off at startup
- Users can attempt to turn on device without needing it to be on first
