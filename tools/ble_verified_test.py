#!/usr/bin/env python3
"""BLE Verified Command Test for Homedics SereneScent.

Tests the verified protocol commands discovered through reverse engineering.
This script can control the actual device.
"""

import asyncio
import os
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Target device - on macOS use UUID, on Linux/Windows use MAC address
DEVICE_ADDRESS = "389C3434-C52A-4D66-8DDD-0063FBDF755C"

# Discovered UUIDs from the device
SERVICE_UUID = "53527aa4-29f7-ae11-4e74-997334782568"
CHAR_TX_UUID = "ee684b1a-1e9b-ed3e-ee55-f894667e92ac"  # Write commands TO device
CHAR_RX_UUID = "654b749c-e37f-ae1f-ebab-40ca133e3690"  # Receive FROM device (notify)

# Path to scratch_pad
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_PAD = os.path.join(SCRIPT_DIR, "..", "scratch_pad")

# =============================================================================
# VERIFIED PROTOCOL COMMANDS
# =============================================================================

# Header for all commands
HEADER = bytes([0xFF, 0xFA])

# Power commands
CMD_POWER_ON = bytes([0xFF, 0xFA, 0x10, 0x04])
CMD_POWER_OFF = bytes([0xFF, 0xFA, 0x11, 0x04])

# Intensity commands (with pre-calculated checksums)
CMD_INTENSITY_LOW = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x0A, 0x00, 0xF0])
CMD_INTENSITY_MEDIUM = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x14, 0x00, 0x82])
CMD_INTENSITY_HIGH = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x1E, 0x00, 0x3C])

# Color commands
CMD_COLOR_OFF = bytes([0xFF, 0xFA, 0x16, 0x05, 0x00])  # Light off (testing)
CMD_COLOR_ROTATING = bytes([0xFF, 0xFA, 0x16, 0x05, 0x01])
CMD_COLOR_WHITE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x02])
CMD_COLOR_RED = bytes([0xFF, 0xFA, 0x16, 0x05, 0x03])
CMD_COLOR_BLUE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x04])
CMD_COLOR_VIOLET = bytes([0xFF, 0xFA, 0x16, 0x05, 0x05])
CMD_COLOR_GREEN = bytes([0xFF, 0xFA, 0x16, 0x05, 0x06])
CMD_COLOR_ORANGE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x07])

# Schedule commands
CMD_SCHEDULE_ON = bytes([0xFF, 0xFA, 0x14, 0x04])
CMD_SCHEDULE_OFF = bytes([0xFF, 0xFA, 0x13, 0x04])  # Note: 0x13 for actual schedule off
CMD_SCHEDULE_SYNC = bytes([0xFF, 0xFA, 0x15, 0x04])  # 0x15 used for mode sync

# Schedule sequence helper commands (required for schedule to actually work)
CMD_SETTINGS_SYNC = bytes([0xFF, 0xFA, 0x20, 0x0E, 0x06, 0x00, 0x16, 0x00, 0x00, 0x1E, 0x00, 0x3C, 0x7F, 0x01])
CMD_SCHEDULE_UNKNOWN1 = bytes([0xFF, 0xFA, 0x12, 0x04])
CMD_SCHEDULE_UNKNOWN2 = bytes([0xFF, 0xFA, 0x46, 0x04])

# App mode switch
CMD_MODE_SCHEDULE = bytes([0xFF, 0xFA, 0x43, 0x05, 0x01])
CMD_MODE_HOME = bytes([0xFF, 0xFA, 0x43, 0x05, 0x00])

# Status query (last byte indicates mode: 00=home, 01=schedule)
CMD_STATUS_QUERY_HOME = bytes([0xFF, 0xFA, 0x40, 0x05, 0x00])
CMD_STATUS_QUERY_SCHEDULE = bytes([0xFF, 0xFA, 0x40, 0x05, 0x01])
CMD_STATUS_QUERY = CMD_STATUS_QUERY_HOME  # Default to home mode

# Command mappings for easy access
INTENSITY_COMMANDS = {
    "low": CMD_INTENSITY_LOW,
    "medium": CMD_INTENSITY_MEDIUM,
    "high": CMD_INTENSITY_HIGH,
}

COLOR_COMMANDS = {
    "lightoff": CMD_COLOR_OFF,
    "rotating": CMD_COLOR_ROTATING,
    "white": CMD_COLOR_WHITE,
    "red": CMD_COLOR_RED,
    "blue": CMD_COLOR_BLUE,
    "violet": CMD_COLOR_VIOLET,
    "green": CMD_COLOR_GREEN,
    "orange": CMD_COLOR_ORANGE,
}


class DualLogger:
    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []

    def print(self, msg=""):
        print(msg)
        self.lines.append(msg)

    def save(self, title="BLE VERIFIED TEST"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"{title} - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for line in self.lines:
                f.write(line + "\n")
        print(f"\n[Output appended to {self.filepath}]")


log = DualLogger(SCRATCH_PAD)


async def send_command(client, cmd: bytes, description: str):
    """Send a command and wait for response."""
    log.print(f"\n>> Sending: {description}")
    log.print(f"   Command: {cmd.hex()} (bytes: {list(cmd)})")

    try:
        await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)
        await asyncio.sleep(0.5)
        return True
    except Exception as e:
        log.print(f"   Error: {e}")
        return False


async def run_test_sequence():
    """Run a sequence of verified commands to test the device."""

    log.print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        log.print(f"Could not find device {DEVICE_ADDRESS}")
        log.save()
        return

    log.print(f"Found device: {device.name}")
    log.print("Connecting...")

    # Retry connection up to 3 times
    client = None
    for attempt in range(3):
        try:
            client = BleakClient(device)
            await client.connect()
            log.print(f"Connected on attempt {attempt + 1}")
            break
        except Exception as e:
            log.print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                log.print("Waiting 5 seconds before retry...")
                await asyncio.sleep(5)
            else:
                log.print("All connection attempts failed")
                log.save()
                return

    if not client or not client.is_connected:
        log.print("Failed to connect")
        log.save()
        return

    responses = []

    def notification_handler(sender, data):
        hex_data = data.hex()
        byte_list = list(data)

        if all(b == 0 for b in data):
            log.print(f"   << [all zeros - {len(data)} bytes]")
        elif all(b == 255 for b in data):
            log.print(f"   << [all 0xFF - {len(data)} bytes]")
        else:
            log.print(f"   << RESPONSE: {hex_data}")
            log.print(f"      bytes: {byte_list}")
            responses.append((hex_data, byte_list))

    try:
        log.print(f"Connected: {client.is_connected}")
        log.print()

        # Subscribe to notifications
        log.print("Subscribing to RX notifications...")
        await client.start_notify(CHAR_RX_UUID, notification_handler)
        await asyncio.sleep(1.0)

        log.print()
        log.print("=" * 60)
        log.print("TESTING VERIFIED COMMANDS")
        log.print("=" * 60)

        # Test sequence
        log.print("\n--- Power Control ---")
        await send_command(client, CMD_POWER_ON, "Power ON")
        await asyncio.sleep(1.0)

        log.print("\n--- Intensity Control ---")
        await send_command(client, CMD_INTENSITY_LOW, "Intensity: LOW")
        await asyncio.sleep(1.5)

        await send_command(client, CMD_INTENSITY_MEDIUM, "Intensity: MEDIUM")
        await asyncio.sleep(1.5)

        await send_command(client, CMD_INTENSITY_HIGH, "Intensity: HIGH")
        await asyncio.sleep(1.5)

        log.print("\n--- Color Control ---")
        await send_command(client, CMD_COLOR_RED, "Color: RED")
        await asyncio.sleep(1.5)

        await send_command(client, CMD_COLOR_BLUE, "Color: BLUE")
        await asyncio.sleep(1.5)

        await send_command(client, CMD_COLOR_GREEN, "Color: GREEN")
        await asyncio.sleep(1.5)

        await send_command(client, CMD_COLOR_ROTATING, "Color: ROTATING")
        await asyncio.sleep(1.5)

        log.print("\n--- Status Query ---")
        await send_command(client, CMD_STATUS_QUERY, "Query Status")
        await asyncio.sleep(1.0)

        # Stop notifications
        await client.stop_notify(CHAR_RX_UUID)

        log.print()
        log.print("=" * 60)
        log.print("SUMMARY")
        log.print("=" * 60)
        log.print(f"Received {len(responses)} meaningful responses")

        if responses:
            log.print("\nAll responses:")
            for i, (hex_data, byte_list) in enumerate(responses):
                log.print(f"  {i+1}: {hex_data}")
                log.print(f"      {byte_list}")

    finally:
        if client and client.is_connected:
            await client.disconnect()
            log.print("\nDisconnected")

    log.save()


async def interactive_control():
    """Interactive mode to control the device with mode tracking."""

    print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        print(f"Could not find device {DEVICE_ADDRESS}")
        return

    print(f"Found device: {device.name}")
    print("Connecting...")

    # Track current mode (0=home, 1=schedule)
    current_mode = {"value": 0}  # Use dict to allow modification in nested function

    # Store last status for analysis
    last_status = {"data": None}

    def parse_status_response(data):
        """Parse and display status response fields."""
        if len(data) < 16:
            print(f"     (Status response too short: {len(data)} bytes)")
            return

        # Intensity (byte 8)
        intensity_val = data[8]
        intensity_map = {10: "LOW", 20: "MEDIUM", 30: "HIGH"}
        intensity_str = intensity_map.get(intensity_val, f"UNKNOWN({intensity_val})")

        # Color (byte 12)
        color_val = data[12]
        color_map = {
            0: "OFF", 1: "ROTATING", 2: "WHITE", 3: "RED",
            4: "BLUE", 5: "VIOLET", 6: "GREEN", 7: "ORANGE"
        }
        color_str = color_map.get(color_val, f"UNKNOWN({color_val})")

        # Schedule status (byte 13)
        schedule_on = data[13] == 1
        schedule_str = "ON" if schedule_on else "OFF"

        # Power/running status (byte 14) - appears to always be 1 when running
        power_on = data[14] == 1
        power_str = "ON" if power_on else "OFF"

        print("     === STATUS PARSED ===")
        print(f"     Intensity: {intensity_str}")
        print(f"     Color: {color_str}")
        print(f"     Schedule: {schedule_str}")
        print(f"     Power: {power_str}")
        print("     ======================")

    def notification_handler(sender, data):
        if all(b == 0 for b in data):
            print(f"\n  << [all zeros - {len(data)} bytes]")
        elif all(b == 255 for b in data):
            print(f"\n  << [all 0xFF - {len(data)} bytes]")
        else:
            print(f"\n  << Response: {data.hex()}")
            print(f"     bytes: {list(data)}")
            # Parse responses based on command echo byte
            if len(data) >= 3 and data[0] == 0xFF and data[1] == 0xFB:
                cmd_echo = data[2]
                if cmd_echo == 0x43:  # Mode switch response
                    print("     (Mode switch acknowledged)")
                elif cmd_echo == 0x40 and len(data) >= 16:  # Status response
                    last_status["data"] = data
                    parse_status_response(data)

    async def send_cmd(cmd, desc, delay=0.2):
        """Helper to send command with logging."""
        print(f"  Sending: {desc}")
        print(f"  Command: {cmd.hex()}")
        await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)
        await asyncio.sleep(delay)

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")

        await client.start_notify(CHAR_RX_UUID, notification_handler)

        print("\n" + "=" * 60)
        print("INTERACTIVE CONTROL MODE (with mode tracking)")
        print("=" * 60)
        print("\nCommands:")
        print("  on / off              - Power control")
        print("  low / medium / high   - Intensity")
        print("  lightoff / red / blue / green / white / violet / orange / rotating - Color")
        print("  scheduleon / scheduleoff - Schedule control (full sequence)")
        print("  modehome / modeschedule  - App mode switch")
        print("  status                - Query device status")
        print("  mode                  - Show current tracked mode")
        print("  quit                  - Exit")
        print("=" * 60)
        print(f"Current mode: {'SCHEDULE' if current_mode['value'] else 'HOME'}")
        print()

        while True:
            try:
                user_input = input(">> ").strip().lower()

                if user_input in ('quit', 'exit', 'q'):
                    break

                if not user_input:
                    continue

                cmd = None
                desc = ""

                # Show current mode
                if user_input == "mode":
                    print(f"  Current tracked mode: {'SCHEDULE' if current_mode['value'] else 'HOME'}")
                    continue

                # Power (ensure home mode first)
                if user_input == "on":
                    if current_mode["value"] != 0:
                        await send_cmd(CMD_MODE_HOME, "Switching to HOME mode first")
                        current_mode["value"] = 0
                    cmd, desc = CMD_POWER_ON, "Power ON"
                elif user_input == "off":
                    if current_mode["value"] != 0:
                        await send_cmd(CMD_MODE_HOME, "Switching to HOME mode first")
                        current_mode["value"] = 0
                    cmd, desc = CMD_POWER_OFF, "Power OFF"

                # Intensity (ensure home mode first)
                elif user_input in INTENSITY_COMMANDS:
                    if current_mode["value"] != 0:
                        await send_cmd(CMD_MODE_HOME, "Switching to HOME mode first")
                        current_mode["value"] = 0
                    cmd = INTENSITY_COMMANDS[user_input]
                    desc = f"Intensity: {user_input.upper()}"

                # Color (ensure home mode first)
                elif user_input in COLOR_COMMANDS:
                    if current_mode["value"] != 0:
                        await send_cmd(CMD_MODE_HOME, "Switching to HOME mode first")
                        current_mode["value"] = 0
                    cmd = COLOR_COMMANDS[user_input]
                    desc = f"Color: {user_input.upper()}"

                # Schedule ON - Full 4-command sequence from app capture
                elif user_input == "scheduleon":
                    print("  === SCHEDULE ON SEQUENCE (4 commands) ===")
                    # Ensure we're in schedule mode first
                    if current_mode["value"] != 1:
                        await send_cmd(CMD_MODE_SCHEDULE, "Switching to SCHEDULE mode first")
                        current_mode["value"] = 1
                    await send_cmd(CMD_SCHEDULE_ON, "1/4: Schedule ON command")
                    await send_cmd(CMD_SETTINGS_SYNC, "2/4: Settings sync")
                    await send_cmd(CMD_SCHEDULE_UNKNOWN1, "3/4: Unknown command 0x12")
                    await send_cmd(CMD_SCHEDULE_UNKNOWN2, "4/4: Unknown command 0x46")
                    print("  === SCHEDULE ON SEQUENCE COMPLETE ===")
                    continue

                # Schedule OFF - Simple 2-command sequence from app capture
                elif user_input == "scheduleoff":
                    print("  === SCHEDULE OFF SEQUENCE ===")
                    # Ensure we're in schedule mode first
                    if current_mode["value"] != 1:
                        await send_cmd(CMD_MODE_SCHEDULE, "Switching to SCHEDULE mode first")
                        current_mode["value"] = 1
                    await send_cmd(CMD_SCHEDULE_OFF, "Schedule OFF (0x13)")
                    await send_cmd(CMD_STATUS_QUERY_SCHEDULE, "Status query")
                    print("  === SCHEDULE OFF SEQUENCE COMPLETE ===")
                    # Stay in schedule mode like scheduleon does
                    continue

                # Mode switch
                elif user_input == "modehome":
                    await send_cmd(CMD_MODE_HOME, "Mode: HOME")
                    await send_cmd(CMD_SCHEDULE_SYNC, "Schedule sync (0x15)")
                    current_mode["value"] = 0
                    continue
                elif user_input == "modeschedule":
                    await send_cmd(CMD_MODE_SCHEDULE, "Mode: SCHEDULE")
                    await send_cmd(CMD_SCHEDULE_SYNC, "Schedule sync (0x15)")
                    current_mode["value"] = 1
                    continue

                # Status - use correct query based on mode
                elif user_input == "status":
                    if current_mode["value"] == 0:
                        cmd, desc = CMD_STATUS_QUERY_HOME, "Query Status (HOME mode)"
                    else:
                        cmd, desc = CMD_STATUS_QUERY_SCHEDULE, "Query Status (SCHEDULE mode)"

                else:
                    print(f"  Unknown command: {user_input}")
                    continue

                if cmd:
                    print(f"  Sending: {desc}")
                    print(f"  Command: {cmd.hex()}")
                    await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)
                    await asyncio.sleep(0.5)

            except EOFError:
                break

        await client.stop_notify(CHAR_RX_UUID)
        print("\nDisconnected.")


def print_usage():
    """Print usage information."""
    print("Homedics SereneScent Verified Command Tester")
    print("-" * 45)
    print("\nUsage:")
    print("  python ble_verified_test.py          - Run automated test sequence")
    print("  python ble_verified_test.py -i       - Interactive control mode")
    print("  python ble_verified_test.py -h       - Show this help")
    print("\nVerified Commands:")
    print("  Power:     ON, OFF")
    print("  Intensity: LOW, MEDIUM, HIGH")
    print("  Colors:    LIGHTOFF, ROTATING, WHITE, RED, BLUE, VIOLET, GREEN, ORANGE")
    print("  Schedule:  SCHEDULEON, SCHEDULEOFF")
    print("  Status:    Query device state")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('-h', '--help', 'help'):
            print_usage()
        elif arg == '-i':
            print("Starting interactive control mode...\n")
            asyncio.run(interactive_control())
        else:
            print(f"Unknown argument: {arg}")
            print_usage()
    else:
        print("Running automated test sequence...\n")
        print("(Use -i flag for interactive mode)\n")
        asyncio.run(run_test_sequence())
