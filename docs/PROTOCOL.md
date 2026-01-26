# Homedics SereneScent BLE Protocol Documentation

**Reverse Engineered:** January 25, 2026
**Device Model:** ARMH-973
**Firmware:** BEKEN BK-BLE-1.0, Version 6.1.2

## Overview

The Homedics SereneScent aromatherapy diffuser uses Bluetooth Low Energy (BLE) for communication with the SereneScent mobile app. This document describes the protocol discovered through packet capture analysis using Apple's PacketLogger.

## BLE Characteristics

| Characteristic | UUID | Purpose |
|----------------|------|---------|
| **Service** | `53527aa4-29f7-ae11-4e74-997334782568` | Main control service |
| **TX (Write)** | `ee684b1a-1e9b-ed3e-ee55-f894667e92ac` | Send commands to device |
| **RX (Notify)** | `654b749c-e37f-ae1f-ebab-40ca133e3690` | Receive responses from device |

**Note:** The device advertises service UUID `0000fff0-0000-1000-8000-00805f9b34fb` but the actual control service uses a different UUID discovered during connection.

## Protocol Format

### Commands (Send to Device)

All commands use a 2-byte header:

```
[FF FA] [Command] [Parameters...]
```

- **Header:** `0xFF 0xFA` (always)
- **Command:** 1-2 bytes identifying the operation
- **Parameters:** Variable length depending on command

### Responses (Received from Device)

Device responses use a similar format with a different header:

```
[FF FB] [Command Echo] [Data...]
```

- **Header:** `0xFF 0xFB` (response indicator)
- **Command Echo:** Echoes the command byte that was sent
- **Data:** Response payload (varies by command)

#### Acknowledgment Responses

Simple commands return a 3-byte acknowledgment:

| Command Sent | Response | Meaning |
|--------------|----------|---------|
| Power ON (`10 04`) | `FF FB 10` | Power command acknowledged |
| Power OFF (`11 04`) | `FF FB 11` | Power command acknowledged |
| Schedule ON (`14 04`) | `FF FB 14` | Schedule command acknowledged |
| Schedule OFF (`13 04`) | `FF FB 13` | Schedule OFF acknowledged |
| Schedule Sync (`15 04`) | `FF FB 15 08` | Schedule sync acknowledged (4 bytes) |
| Intensity (`17 08...`) | `FF FB 17` | Intensity command acknowledged |
| Color (`16 05...`) | `FF FB 16` | Color command acknowledged |

#### Status Query Response

The status query returns a 16-byte response with device state:

```
FF FB 40 06 00 16 00 00 0A 00 F0 7F 02 00 01 00
```

| Offset | Value | Field | Description |
|--------|-------|-------|-------------|
| 0-1 | `FF FB` | Header | Response header |
| 2 | `40` | Command | Command echo (status query) |
| 3 | `06` | Length | Sub-command/length indicator |
| 4-5 | `00 16` | Device ID | Constant device identifier |
| 6-7 | `00 00` | Reserved | Always zero |
| 8 | `0A` | **Intensity** | 10=LOW, 20=MEDIUM, 30=HIGH |
| 9-10 | `00 F0` | Checksum | Intensity checksum (mirrors command) |
| 11 | `7F` | Constant | Always 127 (0x7F) |
| 12 | `02` | **Color** | Color index (see table below) |
| 13 | `00` | **Schedule** | 0=OFF, 1=ON |
| 14 | `01` | **Power** | 0=OFF, 1=ON (running) |
| 15 | `00` | **Mode** | 0=HOME mode, 1=SCHEDULE mode |

**Color Index Values (byte 12):**

| Value | Color |
|-------|-------|
| 0 | Light Off |
| 1 | Rotating (cycle) |
| 2 | White |
| 3 | Red |
| 4 | Blue |
| 5 | Violet |
| 6 | Green |
| 7 | Orange |

## Commands

### Power Control

| Command | Bytes | Description |
|---------|-------|-------------|
| Power ON | `FF FA 10 04` | Turn diffuser on |
| Power OFF | `FF FA 11 04` | Turn diffuser off |

**Format:** `FF FA [10=ON / 11=OFF] 04`

### Intensity Control

| Level | Command | Intensity Value |
|-------|---------|-----------------|
| LOW | `FF FA 17 08 00 0A 00 F0` | 0x0A (10) |
| MEDIUM | `FF FA 17 08 00 14 00 82` | 0x14 (20) |
| HIGH | `FF FA 17 08 00 1E 00 3C` | 0x1E (30) |

**Format:** `FF FA 17 08 00 [intensity] 00 [checksum]`

- Command identifier: `0x17 0x08`
- Intensity values: 10 (low), 20 (medium), 30 (high)
- Last byte is a checksum (algorithm TBD)

### Light Color Control

| Color | Command | Index |
|-------|---------|-------|
| Rotating (cycle) | `FF FA 16 05 01` | 0x01 |
| White | `FF FA 16 05 02` | 0x02 |
| Red | `FF FA 16 05 03` | 0x03 |
| Blue | `FF FA 16 05 04` | 0x04 |
| Violet | `FF FA 16 05 05` | 0x05 |
| Green | `FF FA 16 05 06` | 0x06 |
| Orange | `FF FA 16 05 07` | 0x07 |

**Format:** `FF FA 16 05 [color_index]`

### Schedule Control

**Important:** The device operates in two modes: HOME and SCHEDULE. Commands like intensity and color only work in HOME mode. Schedule commands require a specific sequence.

| Command | Bytes | Description |
|---------|-------|-------------|
| Schedule ON | `FF FA 14 04` | Enable scheduled operation |
| Schedule OFF | `FF FA 13 04` | Disable scheduled operation |
| Schedule Sync | `FF FA 15 04` | Sync command (used during mode switches) |

**Format:** `FF FA [14=ON / 13=OFF / 15=Sync] 04`

#### Schedule ON Sequence

To successfully enable the schedule, the app sends a 4-command sequence:

1. `FF FA 14 04` - Schedule ON command
2. `FF FA 20 0E 06 00 16 00 00 1E 00 3C 7F 01` - Settings sync
3. `FF FA 12 04` - Unknown helper command
4. `FF FA 46 04` - Unknown helper command

Each command is sent with ~200ms delay between them.

#### Schedule OFF Sequence

To disable the schedule, the app sends a simpler 2-command sequence:

1. `FF FA 13 04` - Schedule OFF command
2. `FF FA 40 05 01` - Status query (schedule mode)

#### Settings Sync Command

The settings sync command contains device state data:

```
FF FA 20 0E 06 00 16 00 00 1E 00 3C 7F 01
```

- `20` - Command type (settings sync)
- `0E` - Length (14 bytes)
- Remaining bytes contain intensity, color, and other state values

### App Mode Switch

The device must be in the correct mode for commands to work:
- **HOME mode**: Power, intensity, and color commands work
- **SCHEDULE mode**: Schedule commands work

| Mode | Command | Description |
|------|---------|-------------|
| Schedule Mode | `FF FA 43 05 01` | Switch to schedule mode |
| Home Mode | `FF FA 43 05 00` | Switch to home mode |

**Format:** `FF FA 43 05 [mode]` where 01=Schedule, 00=Home

When switching modes, the app also sends `FF FA 15 04` (schedule off) to synchronize state.

### Status Query

| Command | Bytes | Description |
|---------|-------|-------------|
| Query Status (HOME) | `FF FA 40 05 00` | Poll device state in home mode |
| Query Status (SCHEDULE) | `FF FA 40 05 01` | Poll device state in schedule mode |

**Format:** `FF FA 40 05 [mode]` - Last byte indicates current mode (00=home, 01=schedule)

The mobile app sends this command repeatedly (approximately every 5 seconds) to keep the connection alive and retrieve device status. The mode byte must match the current app mode.

## Connection Handling

### Connection Timeout

The BLE connection will be dropped by the device after a period of inactivity. The mobile app maintains the connection by sending periodic status queries (`FF FA 40 05 00`).

### Implementation Requirements

1. **Reconnection Logic:** Must check connection state before sending commands and reconnect if needed
2. **Keepalive (Optional):** Send status query every ~5 seconds to maintain connection
3. **Retry Logic:** Connection attempts may fail; implement retry with backoff
4. **Graceful Disconnect:** Explicitly disconnect when done to free resources

### Recommended Connection Pattern

```python
async def ensure_connected(client):
    if not client.is_connected:
        await client.connect()
        await client.start_notify(CHAR_RX_UUID, notification_handler)
    return client.is_connected
```

## Device Information

From the Device Information Service:

| Attribute | Value |
|-----------|-------|
| Manufacturer | BEKEN SAS |
| Model | BK-BLE-1.0 |
| Firmware Version | 6.1.2 |

## macOS BLE Notes

On macOS, BLE devices are identified by a system-assigned UUID rather than MAC address:

- **MAC Address:** `E5:FC:00:07:F9:C7`
- **macOS UUID:** `389C3434-C52A-4D66-8DDD-0063FBDF755C`

The UUID is persistent for a given device on a given Mac but differs between machines.

## Checksum Analysis

The intensity commands include a checksum byte. Analysis of captured values:

| Intensity | Value | Checksum | XOR Result |
|-----------|-------|----------|------------|
| LOW | 0x0A | 0xF0 | - |
| MEDIUM | 0x14 | 0x82 | - |
| HIGH | 0x1E | 0x3C | - |

The exact checksum algorithm has not been fully determined. For implementation, the known command bytes can be used directly.

## Reverse Engineering Methodology

1. **Initial Discovery:** Used `bleak` Python library to enumerate services and characteristics
2. **Protocol Sniffing:** Used Apple PacketLogger to capture BLE traffic between iOS app and device
3. **Command Identification:** Systematically changed settings in app while capturing packets
4. **Verification:** Commands were extracted from ATT Write Command packets

## Tools Used

- **bleak** - Python BLE library for device enumeration
- **PacketLogger** (Apple) - BLE packet capture on macOS
- **nRF Connect** (Nordic) - Initial BLE exploration on iOS

## Files

| File | Purpose |
|------|---------|
| `tools/ble_discover.py` | Enumerate device services/characteristics |
| `tools/ble_command_test.py` | Test command patterns |
| `tools/ble_protocol_test.py` | Test known protocol patterns |
| `tools/ble_state_compare.py` | Compare device state before/after changes |
| `tools/ble_verified_test.py` | Test verified commands from this document |

## Version History

| Date | Change |
|------|--------|
| 2026-01-25 | Initial protocol documentation |
| 2026-01-25 | Added response format, acknowledgments, status response, and connection handling |
| 2026-01-25 | Added schedule control commands |
| 2026-01-25 | Confirmed schedule OFF, added mode switch and other observed commands |
| 2026-01-25 | Corrected schedule OFF command: 0x13 (not 0x15), 0x15 is sync command |
| 2026-01-25 | Complete status response mapping: intensity, color, schedule, power fields |
