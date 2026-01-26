# Homedics SereneScent

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/john-k-mcdowell/Homedics-SereneScent?include_prereleases)](https://github.com/john-k-mcdowell/Homedics-SereneScent/releases)
[![License](https://img.shields.io/github/license/john-k-mcdowell/Homedics-SereneScent)](LICENSE)

A Home Assistant custom integration for the **Homedics SereneScent Aromatherapy Diffuser** (Model ARMH-973).

This integration communicates with the diffuser over Bluetooth Low Energy (BLE) using a reverse-engineered protocol, allowing full local control without cloud connectivity.

## Features

- **Power Control** - Turn the diffuser on/off
- **Intensity Control** - Set mist intensity (Low, Medium, High)
- **Light Control** - Change LED colors (White, Red, Blue, Violet, Green, Orange, Rotating)
- **Schedule Control** - Enable/disable the device's built-in schedule mode
- **Auto Discovery** - Automatically discovers SereneScent devices via Bluetooth
- **Multi-Device Support** - Configure multiple diffusers independently

## Supported Devices

| Model | Firmware | Status |
|-------|----------|--------|
| ARMH-973 | BEKEN BK-BLE-1.0 v6.1.2 | Tested |

The device advertises via Bluetooth as `ARPRP-xxx` where `xxx` is device-specific.

## Requirements

- Home Assistant 2023.1.0 or newer
- Bluetooth adapter on your Home Assistant host
- Home Assistant Bluetooth integration enabled

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) and select **Custom repositories**
3. Add `https://github.com/john-k-mcdowell/Homedics-SereneScent` as an **Integration**
4. Click **Add**
5. Search for "Homedics SereneScent" in HACS and install it
6. Restart Home Assistant

#### Installing Beta Releases

To install pre-release versions for testing:

1. In HACS, go to **Settings**
2. Enable **Show beta versions**
3. Install or update the integration

### Manual Installation

1. Download the latest release from the [Releases](https://github.com/john-k-mcdowell/Homedics-SereneScent/releases) page
2. Extract and copy the `custom_components/homedics_serenescent` folder to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### Automatic Discovery

Once installed, Home Assistant will automatically discover SereneScent devices when they are powered on and within Bluetooth range. You'll receive a notification to configure the discovered device.

### Manual Setup

1. Go to **Settings** > **Devices & Services**
2. Click **Add Integration**
3. Search for "Homedics SereneScent"
4. Select your device from the list of discovered devices
5. Confirm the setup

## Entities

The integration creates the following entities for each device:

### Fan
| Entity | Description |
|--------|-------------|
| `fan.serenescent_diffuser` | Main power control with intensity presets |

**Preset Modes:** `low`, `medium`, `high`

### Light
| Entity | Description |
|--------|-------------|
| `light.serenescent_light` | LED light with color effects |

**Effects:** `white`, `red`, `blue`, `violet`, `green`, `orange`, `rotating`

### Switch
| Entity | Description |
|--------|-------------|
| `switch.serenescent_schedule` | Toggle device's built-in schedule mode |

### Sensor
| Entity | Description |
|--------|-------------|
| `sensor.serenescent_intensity` | Current intensity level |
| `sensor.serenescent_color` | Current light color |

## Example Automations

### Turn on diffuser at sunset with blue light

```yaml
automation:
  - alias: "Evening Diffuser"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: fan.turn_on
        target:
          entity_id: fan.serenescent_diffuser
        data:
          preset_mode: medium
      - service: light.turn_on
        target:
          entity_id: light.serenescent_light
        data:
          effect: blue
```

### Turn off diffuser at bedtime

```yaml
automation:
  - alias: "Bedtime Diffuser Off"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: fan.turn_off
        target:
          entity_id: fan.serenescent_diffuser
```

## Troubleshooting

### Device not discovered

- Ensure the diffuser is powered on
- Check that your Home Assistant host has a Bluetooth adapter
- Verify the Bluetooth integration is enabled in Home Assistant
- Move the diffuser closer to your Home Assistant host

### Connection drops frequently

- BLE connections can be affected by distance and interference
- The integration automatically reconnects when needed
- Consider using a Bluetooth proxy (ESPHome) for better range

### Commands not working

- The device has two modes: HOME and SCHEDULE
- Power/intensity/color commands only work in HOME mode
- The integration handles mode switching automatically

## Protocol Documentation

This integration uses a reverse-engineered BLE protocol. Full protocol documentation is available in [docs/PROTOCOL.md](docs/PROTOCOL.md).

### Protocol Summary

- **Service UUID:** `53527aa4-29f7-ae11-4e74-997334782568`
- **Command Format:** `FF FA [cmd] [params]`
- **Response Format:** `FF FB [cmd_echo] [data]`

## Development

### Project Structure

```
custom_components/homedics_serenescent/
├── __init__.py          # Integration setup
├── config_flow.py       # Device discovery and configuration
├── coordinator.py       # BLE communication coordinator
├── const.py             # Constants and protocol definitions
├── fan.py               # Fan entity (power/intensity)
├── light.py             # Light entity (colors)
├── switch.py            # Switch entity (schedule)
├── sensor.py            # Sensor entities (status)
├── manifest.json        # Integration manifest
├── strings.json         # UI strings
├── translations/        # Localization
│   └── en.json
└── version.py           # Version info
```

### Tools

The `tools/` directory contains Python scripts used for protocol reverse engineering:

- `ble_discover.py` - Enumerate device services/characteristics
- `ble_command_test.py` - Test command patterns
- `ble_protocol_test.py` - Test known protocol patterns
- `ble_state_compare.py` - Compare device state before/after changes
- `ble_verified_test.py` - Test verified commands

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch from `development`
3. Make your changes
4. Submit a pull request to `development`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Homedics. Use at your own risk. The BLE protocol was reverse-engineered for personal use and home automation purposes.

## Credits

- Protocol reverse-engineered using [bleak](https://github.com/hbldh/bleak) and Apple PacketLogger
- Built for [Home Assistant](https://www.home-assistant.io/)
