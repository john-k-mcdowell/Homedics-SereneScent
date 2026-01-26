#!/usr/bin/env python3
"""BLE Discovery Script for Homedics SereneScent reverse engineering.

Output is written to both terminal and appended to scratch_pad.
"""

import asyncio
import os
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Target device - on macOS use UUID, on Linux/Windows use MAC address
# macOS UUID for ARMH-973 E5FC0007F9C7:
DEVICE_ADDRESS = "389C3434-C52A-4D66-8DDD-0063FBDF755C"

# Path to scratch_pad (relative to script location)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_PAD = os.path.join(SCRIPT_DIR, "..", "scratch_pad")


class DualLogger:
    """Logger that writes to both terminal and file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []

    def print(self, msg=""):
        """Print to terminal and store for file."""
        print(msg)
        self.lines.append(msg)

    def save(self, title="BLE DISCOVERY"):
        """Append all output to scratch_pad with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"{title} - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for line in self.lines:
                f.write(line + "\n")
        print(f"\n[Output appended to {self.filepath}]")


# Global logger instance
log = DualLogger(SCRATCH_PAD)


async def discover_device():
    """Connect to device and enumerate all services/characteristics."""

    log.print(f"Scanning for device {DEVICE_ADDRESS}...")

    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        log.print(f"Could not find device {DEVICE_ADDRESS}")
        log.print("\nScanning for all nearby BLE devices...")
        devices = await BleakScanner.discover(timeout=5.0)
        log.print("\nFound devices:")
        for d in devices:
            log.print(f"  {d.address} - {d.name}")
        log.save()
        return

    log.print(f"Found device: {device.name}")
    log.print(f"Connecting...")

    async with BleakClient(device) as client:
        log.print(f"Connected: {client.is_connected}")
        log.print()
        log.print("=" * 60)
        log.print("SERVICES AND CHARACTERISTICS")
        log.print("=" * 60)

        for service in client.services:
            log.print(f"\nService: {service.uuid}")
            log.print(f"  Description: {service.description}")

            for char in service.characteristics:
                props = ", ".join(char.properties)
                log.print(f"\n  Characteristic: {char.uuid}")
                log.print(f"    Properties: {props}")
                log.print(f"    Handle: {char.handle}")

                # Try to read if readable
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        log.print(f"    Value (hex): {value.hex()}")
                        log.print(f"    Value (bytes): {list(value)}")
                        # Try to decode as string
                        try:
                            decoded = value.decode('utf-8')
                            log.print(f"    Value (str): {decoded}")
                        except Exception:
                            pass
                    except Exception as e:
                        log.print(f"    Read error: {e}")

                # List descriptors
                for desc in char.descriptors:
                    log.print(f"    Descriptor: {desc.uuid}")

        log.print()
        log.print("=" * 60)
        log.print("NOTIFICATION TEST")
        log.print("=" * 60)
        log.print("Subscribing to notify characteristics for 10 seconds...")
        log.print("(Change settings on the device to see notifications)")
        log.print()

        notifications_received = []

        def notification_handler(char_handle, data):
            """Handle incoming notifications."""
            hex_data = data.hex()
            byte_list = list(data)
            # Get characteristic info from handle
            char_info = f"{char_handle}"
            for svc in client.services:
                for c in svc.characteristics:
                    if c.handle == char_handle or str(char_handle) in str(c.uuid):
                        char_info = f"{c.uuid} (Handle: {c.handle})"
                        break

            # Filter display but still log
            if all(b == 0 for b in data):
                log.print(f"  NOTIFY from {char_info}: [all zeros - {len(data)} bytes]")
            elif all(b == 255 for b in data):
                log.print(f"  NOTIFY from {char_info}: [all 0xFF - {len(data)} bytes]")
            else:
                log.print(f"  NOTIFY from {char_info}:")
                log.print(f"    hex={hex_data}")
                log.print(f"    bytes={byte_list}")
            notifications_received.append((char_handle, data))

        # Subscribe to all notify characteristics
        notify_chars = []
        for service in client.services:
            for char in service.characteristics:
                if "notify" in char.properties:
                    try:
                        await client.start_notify(char.uuid, notification_handler)
                        notify_chars.append(char.uuid)
                        log.print(f"  Subscribed to {char.uuid}")
                    except Exception as e:
                        log.print(f"  Failed to subscribe to {char.uuid}: {e}")

        # Wait and collect notifications
        await asyncio.sleep(10)

        # Unsubscribe
        for char_uuid in notify_chars:
            try:
                await client.stop_notify(char_uuid)
            except Exception:
                pass

        log.print(f"\nReceived {len(notifications_received)} notifications")
        log.print("\nDone!")

    log.save()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        DEVICE_ADDRESS = sys.argv[1]

    print("Homedics SereneScent BLE Discovery Tool")
    print("-" * 40)
    asyncio.run(discover_device())
