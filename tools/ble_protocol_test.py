#!/usr/bin/env python3
"""BLE Protocol Testing Script for Homedics SereneScent.

Tests common Chinese BLE device protocol patterns based on reverse
engineering of similar devices (Govee, etc.).
"""

import asyncio
import os
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Target device
DEVICE_ADDRESS = "389C3434-C52A-4D66-8DDD-0063FBDF755C"

# Characteristics
CHAR_TX_UUID = "ee684b1a-1e9b-ed3e-ee55-f894667e92ac"
CHAR_RX_UUID = "654b749c-e37f-ae1f-ebab-40ca133e3690"

# Path to scratch_pad
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_PAD = os.path.join(SCRIPT_DIR, "..", "scratch_pad")


def xor_checksum(data: bytes) -> int:
    """Calculate XOR checksum of all bytes."""
    result = 0
    for b in data:
        result ^= b
    return result


def build_govee_style_cmd(cmd_type: int, cmd_sub: int, *data) -> bytes:
    """Build a Govee-style 20-byte command with XOR checksum.

    Format: [0x33, cmd_type, cmd_sub, data..., 0x00 padding, checksum]
    """
    cmd = bytearray(20)
    cmd[0] = 0x33  # Command identifier
    cmd[1] = cmd_type
    cmd[2] = cmd_sub

    # Fill in data bytes
    for i, d in enumerate(data):
        if i + 3 < 19:
            cmd[3 + i] = d

    # Calculate checksum (XOR of bytes 0-18)
    cmd[19] = xor_checksum(cmd[:19])
    return bytes(cmd)


def build_simple_cmd(header: int, *data, length: int = 20) -> bytes:
    """Build a simple command with header and optional checksum."""
    cmd = bytearray(length)
    cmd[0] = header

    for i, d in enumerate(data):
        if i + 1 < length - 1:
            cmd[1 + i] = d

    # XOR checksum in last byte
    cmd[length - 1] = xor_checksum(cmd[:length - 1])
    return bytes(cmd)


# Protocol patterns to test
TEST_PROTOCOLS = [
    # Govee-style commands (0x33 header, 20 bytes, XOR checksum)
    ("Govee: Power ON", build_govee_style_cmd(0x01, 0x01)),
    ("Govee: Power OFF", build_govee_style_cmd(0x01, 0x00)),
    ("Govee: Status query", build_govee_style_cmd(0x00, 0x00)),
    ("Govee: Intensity Low (1)", build_govee_style_cmd(0x04, 0x01)),
    ("Govee: Intensity Med (2)", build_govee_style_cmd(0x04, 0x02)),
    ("Govee: Intensity High (3)", build_govee_style_cmd(0x04, 0x03)),

    # 0x55 header style (common preamble)
    ("0x55: Power ON", build_simple_cmd(0x55, 0x01, 0x01)),
    ("0x55: Power OFF", build_simple_cmd(0x55, 0x01, 0x00)),
    ("0x55: Status query", build_simple_cmd(0x55, 0x00, 0x00)),
    ("0x55: Intensity 1", build_simple_cmd(0x55, 0x04, 0x01)),
    ("0x55: Intensity 2", build_simple_cmd(0x55, 0x04, 0x02)),
    ("0x55: Intensity 3", build_simple_cmd(0x55, 0x04, 0x03)),

    # 0xAA header style
    ("0xAA: Power ON", build_simple_cmd(0xAA, 0x01, 0x01)),
    ("0xAA: Power OFF", build_simple_cmd(0xAA, 0x01, 0x00)),
    ("0xAA: Status query", build_simple_cmd(0xAA, 0x00, 0x00)),
    ("0xAA: Intensity 1", build_simple_cmd(0xAA, 0x04, 0x01)),
    ("0xAA: Intensity 2", build_simple_cmd(0xAA, 0x04, 0x02)),
    ("0xAA: Intensity 3", build_simple_cmd(0xAA, 0x04, 0x03)),

    # Short commands (8 bytes)
    ("Short 0x33: Status", build_simple_cmd(0x33, 0x00, length=8)),
    ("Short 0x33: Power ON", build_simple_cmd(0x33, 0x01, 0x01, length=8)),
    ("Short 0x55: Status", build_simple_cmd(0x55, 0x00, length=8)),
    ("Short 0xAA: Status", build_simple_cmd(0xAA, 0x00, length=8)),

    # Tuya-style (longer with different structure)
    ("Tuya: Status", bytes([0x55, 0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])),
    ("Tuya: Query", bytes([0x55, 0xAA, 0x00, 0x08, 0x00, 0x00, 0x00, 0x07])),

    # Raw intensity commands (maybe device uses simple values)
    ("Raw: 0x01 (Low?)", bytes([0x01])),
    ("Raw: 0x02 (Med?)", bytes([0x02])),
    ("Raw: 0x03 (High?)", bytes([0x03])),
    ("Raw: 0x10", bytes([0x10])),
    ("Raw: 0x20", bytes([0x20])),
    ("Raw: 0x30", bytes([0x30])),
]


class DualLogger:
    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []

    def print(self, msg=""):
        print(msg)
        self.lines.append(msg)

    def save(self, title="BLE PROTOCOL TEST"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"{title} - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for line in self.lines:
                f.write(line + "\n")
        print(f"\n[Output appended to {self.filepath}]")


log = DualLogger(SCRATCH_PAD)


async def test_protocols():
    """Test various protocol patterns."""

    log.print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        log.print(f"Could not find device {DEVICE_ADDRESS}")
        log.save()
        return

    log.print(f"Found device: {device.name}")
    log.print("Connecting (with retry)...")

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
            log.print(f"    << [all zeros - {len(data)} bytes]")
        elif all(b == 255 for b in data):
            log.print(f"    << [all 0xFF - {len(data)} bytes]")
        else:
            log.print(f"    << RESPONSE: {hex_data}")
            log.print(f"       bytes: {byte_list}")
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
        log.print("TESTING PROTOCOL PATTERNS")
        log.print("=" * 60)

        for name, cmd in TEST_PROTOCOLS:
            log.print(f"\n{name}")
            log.print(f"  >> Sending: {cmd.hex()}")
            log.print(f"     bytes: {list(cmd)}")

            try:
                await client.write_gatt_char(CHAR_TX_UUID, cmd, response=False)
                await asyncio.sleep(0.8)
            except Exception as e:
                log.print(f"  Error: {e}")

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
            log.print("Disconnected")

    log.save()


if __name__ == "__main__":
    print("Homedics SereneScent Protocol Pattern Tester")
    print("-" * 45)
    print("Testing common Chinese BLE device protocols")
    print("-" * 45)
    print()
    asyncio.run(test_protocols())
