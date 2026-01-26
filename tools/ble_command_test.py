#!/usr/bin/env python3
"""BLE Command Testing Script for Homedics SereneScent reverse engineering.

Tries various common command patterns to discover the device protocol.
Output is written to both terminal and appended to scratch_pad.
"""

import asyncio
import sys
import os
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Target device - on macOS use UUID, on Linux/Windows use MAC address
DEVICE_ADDRESS = "389C3434-C52A-4D66-8DDD-0063FBDF755C"

# Discovered UUIDs from the device
SERVICE_UUID = "53527aa4-29f7-ae11-4e74-997334782568"
CHAR_TX_UUID = "ee684b1a-1e9b-ed3e-ee55-f894667e92ac"  # Write commands TO device
CHAR_RX_UUID = "654b749c-e37f-ae1f-ebab-40ca133e3690"  # Receive FROM device (notify)

# OAD service characteristics (TI Over-the-Air Download, sometimes repurposed)
CHAR_OAD1_UUID = "f000ffc1-0451-4000-b000-000000000000"
CHAR_OAD2_UUID = "f000ffc2-0451-4000-b000-000000000000"

# All writable characteristics to try
WRITE_CHARACTERISTICS = [
    ("Main TX", CHAR_TX_UUID),
    ("OAD 1", CHAR_OAD1_UUID),
    ("OAD 2", CHAR_OAD2_UUID),
]

# Path to scratch_pad (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_PAD = os.path.join(SCRIPT_DIR, "..", "scratch_pad")

# Common command patterns to try
TEST_COMMANDS = [
    # Simple single-byte commands
    ("Status query (0x00)", bytes([0x00])),
    ("Status query (0x01)", bytes([0x01])),
    ("Status query (0xFF)", bytes([0xFF])),

    # Common header patterns
    ("Header 0xAA", bytes([0xAA])),
    ("Header 0xAA 0x00", bytes([0xAA, 0x00])),
    ("Header 0xAA 0x01", bytes([0xAA, 0x01])),
    ("Header 0x55", bytes([0x55])),
    ("Header 0x55 0xAA", bytes([0x55, 0xAA])),

    # Common status request patterns
    ("Get status pattern 1", bytes([0x01, 0x00])),
    ("Get status pattern 2", bytes([0x00, 0x01])),
    ("Get status pattern 3", bytes([0xFE, 0x01])),
    ("Get status pattern 4", bytes([0x01, 0x01, 0x01])),

    # Longer command patterns (some devices need fixed length)
    ("8-byte zeros", bytes([0x00] * 8)),
    ("8-byte query", bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])),

    # Common Chinese BLE device patterns
    ("Pattern 0xA5", bytes([0xA5, 0x01])),
    ("Pattern 0x5A", bytes([0x5A, 0x01])),
    ("Pattern AT", b"AT\r\n"),
    ("Pattern GET", b"GET"),
]


class DualLogger:
    """Logger that writes to both terminal and file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []

    def print(self, msg=""):
        """Print to terminal and store for file."""
        print(msg)
        self.lines.append(msg)

    def save(self):
        """Append all output to scratch_pad with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"BLE COMMAND TEST - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for line in self.lines:
                f.write(line + "\n")
        print(f"\n[Output appended to {self.filepath}]")


# Global logger instance
log = DualLogger(SCRATCH_PAD)


async def test_commands():
    """Connect and test various commands."""

    log.print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        log.print(f"Could not find device {DEVICE_ADDRESS}")
        log.save()
        return

    log.print(f"Found device: {device.name}")
    log.print(f"Connecting...")

    notifications = []

    def notification_handler(sender, data):
        """Handle incoming notifications."""
        hex_data = data.hex()
        byte_list = list(data)
        # Filter out all-zeros and all-FF responses
        if all(b == 0 for b in data):
            log.print(f"    Response: [all zeros - {len(data)} bytes]")
        elif all(b == 255 for b in data):
            log.print(f"    Response: [all 0xFF - {len(data)} bytes]")
        else:
            log.print(f"    Response: hex={hex_data}")
            log.print(f"             bytes={byte_list}")
            notifications.append((hex_data, byte_list))

    async with BleakClient(device) as client:
        log.print(f"Connected: {client.is_connected}")
        log.print()

        # Subscribe to notifications
        log.print("Subscribing to notifications...")
        await client.start_notify(CHAR_RX_UUID, notification_handler)
        await asyncio.sleep(0.5)

        log.print()
        log.print("=" * 60)
        log.print("TESTING COMMANDS ON ALL WRITABLE CHARACTERISTICS")
        log.print("=" * 60)

        for char_name, char_uuid in WRITE_CHARACTERISTICS:
            log.print()
            log.print(f"--- Testing {char_name} ({char_uuid[:8]}...) ---")

            for name, cmd in TEST_COMMANDS:
                log.print(f"\nTrying: {name}")
                log.print(f"  Sending to {char_name}: {cmd.hex()} (bytes: {list(cmd)})")

                try:
                    await client.write_gatt_char(char_uuid, cmd, response=False)
                    # Wait for response
                    await asyncio.sleep(0.5)
                except Exception as e:
                    log.print(f"  Error: {e}")
                    break  # If one command fails on this char, skip to next characteristic

        # Unsubscribe
        await client.stop_notify(CHAR_RX_UUID)

        log.print()
        log.print("=" * 60)
        log.print("SUMMARY")
        log.print("=" * 60)
        log.print(f"Received {len(notifications)} meaningful responses")
        for i, (hex_data, byte_list) in enumerate(notifications):
            log.print(f"\n  Response {i+1}:")
            log.print(f"    Hex: {hex_data}")
            log.print(f"    Bytes: {byte_list}")

    log.save()


async def interactive_mode():
    """Interactive mode to send custom commands."""
    # Note: Interactive mode only logs to terminal, not to file

    print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        print(f"Could not find device {DEVICE_ADDRESS}")
        return

    print(f"Found device: {device.name}")
    print(f"Connecting...")

    def notification_handler(sender, data):
        """Handle incoming notifications."""
        hex_data = data.hex()
        if all(b == 0 for b in data):
            print(f"\n  << [all zeros - {len(data)} bytes]")
        elif all(b == 255 for b in data):
            print(f"\n  << [all 0xFF - {len(data)} bytes]")
        else:
            print(f"\n  << hex: {hex_data}")
            print(f"     bytes: {list(data)}")

    async with BleakClient(device) as client:
        print(f"Connected: {client.is_connected}")

        # Subscribe to notifications
        await client.start_notify(CHAR_RX_UUID, notification_handler)

        print("\n" + "=" * 60)
        print("INTERACTIVE MODE")
        print("=" * 60)
        print("Enter hex bytes to send (e.g., 'aa 01 ff' or 'aa01ff')")
        print("Type 'quit' to exit")
        print("=" * 60 + "\n")

        while True:
            try:
                user_input = input(">> ").strip()

                if user_input.lower() in ('quit', 'exit', 'q'):
                    break

                if not user_input:
                    continue

                # Parse hex input
                hex_str = user_input.replace(" ", "").replace("0x", "")
                try:
                    cmd = bytes.fromhex(hex_str)
                    print(f"  Sending: {cmd.hex()} (bytes: {list(cmd)})")
                    await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)
                    await asyncio.sleep(0.5)
                except ValueError:
                    print("  Invalid hex format. Use format like 'aa 01 ff' or 'aa01ff'")

            except EOFError:
                break

        await client.stop_notify(CHAR_RX_UUID)
        print("\nDisconnected.")


if __name__ == "__main__":
    print("Homedics SereneScent BLE Command Tester")
    print("-" * 40)

    if len(sys.argv) > 1 and sys.argv[1] == "-i":
        print("Starting interactive mode...\n")
        asyncio.run(interactive_mode())
    else:
        print("Running automated command tests...\n")
        print("(Use -i flag for interactive mode)\n")
        asyncio.run(test_commands())
