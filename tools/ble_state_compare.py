#!/usr/bin/env python3
"""BLE State Comparison Script for Homedics SereneScent reverse engineering.

Captures device state, waits for changes via app, then compares.
Output is written to both terminal and appended to scratch_pad.
"""

import asyncio
import os
import sys
from datetime import datetime
from bleak import BleakClient, BleakScanner

# Target device - on macOS use UUID, on Linux/Windows use MAC address
DEVICE_ADDRESS = "389C3434-C52A-4D66-8DDD-0063FBDF755C"

# All discovered characteristics
CHARACTERISTICS = {
    # Main service
    "main_rx": "654b749c-e37f-ae1f-ebab-40ca133e3690",  # notify, read
    "main_tx": "ee684b1a-1e9b-ed3e-ee55-f894667e92ac",  # write
    # OAD service
    "oad_1": "f000ffc1-0451-4000-b000-000000000000",  # write, notify
    "oad_2": "f000ffc2-0451-4000-b000-000000000000",  # write, notify
}

# Path to scratch_pad
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRATCH_PAD = os.path.join(SCRIPT_DIR, "..", "scratch_pad")


class DualLogger:
    """Logger that writes to both terminal and file."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []

    def print(self, msg=""):
        print(msg)
        self.lines.append(msg)

    def save(self, title="BLE STATE COMPARE"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.filepath, "a") as f:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"{title} - {timestamp}\n")
            f.write(f"{'='*60}\n")
            for line in self.lines:
                f.write(line + "\n")
        print(f"\n[Output appended to {self.filepath}]")


log = DualLogger(SCRATCH_PAD)


async def read_all_characteristics(client):
    """Read all readable characteristics and return as dict."""
    state = {}

    for service in client.services:
        for char in service.characteristics:
            if "read" in char.properties:
                try:
                    value = await client.read_gatt_char(char.uuid)
                    state[char.uuid] = {
                        "hex": value.hex(),
                        "bytes": list(value),
                        "handle": char.handle,
                    }
                except Exception as e:
                    state[char.uuid] = {"error": str(e)}

    return state


async def capture_notifications(client, duration=3):
    """Subscribe to notifications and capture for duration seconds."""
    notifications = {}

    def handler(char_uuid):
        def inner(sender, data):
            key = str(char_uuid)
            if key not in notifications:
                notifications[key] = []
            notifications[key].append({
                "hex": data.hex(),
                "bytes": list(data),
            })
        return inner

    # Subscribe to all notify characteristics
    subscribed = []
    for service in client.services:
        for char in service.characteristics:
            if "notify" in char.properties:
                try:
                    await client.start_notify(char.uuid, handler(char.uuid))
                    subscribed.append(char.uuid)
                except Exception:
                    pass

    await asyncio.sleep(duration)

    # Unsubscribe
    for char_uuid in subscribed:
        try:
            await client.stop_notify(char_uuid)
        except Exception:
            pass

    return notifications


def compare_states(state1, state2, label1="State 1", label2="State 2"):
    """Compare two states and show differences."""
    differences = []

    all_keys = set(state1.keys()) | set(state2.keys())

    for key in sorted(all_keys):
        val1 = state1.get(key, {})
        val2 = state2.get(key, {})

        if val1.get("hex") != val2.get("hex"):
            differences.append({
                "uuid": key,
                label1: val1.get("hex", "N/A"),
                label2: val2.get("hex", "N/A"),
                f"{label1}_bytes": val1.get("bytes", []),
                f"{label2}_bytes": val2.get("bytes", []),
            })

    return differences


def format_byte_diff(bytes1, bytes2):
    """Show which bytes differ between two byte lists."""
    if not bytes1 or not bytes2:
        return "N/A"

    max_len = max(len(bytes1), len(bytes2))
    diffs = []

    for i in range(max_len):
        b1 = bytes1[i] if i < len(bytes1) else None
        b2 = bytes2[i] if i < len(bytes2) else None

        if b1 != b2:
            diffs.append(f"[{i}]: {b1} -> {b2}")

    return ", ".join(diffs[:20])  # Limit output


async def run_comparison(state_label=""):
    """Run the state comparison workflow."""

    log.print(f"Scanning for device {DEVICE_ADDRESS}...")
    device = await BleakScanner.find_device_by_address(DEVICE_ADDRESS, timeout=10.0)

    if not device:
        log.print(f"Could not find device {DEVICE_ADDRESS}")
        log.save()
        return

    log.print(f"Found device: {device.name}")

    # CAPTURE STATE 1
    log.print()
    log.print("=" * 60)
    log.print(f"CAPTURING STATE 1 {state_label}")
    log.print("=" * 60)

    async with BleakClient(device) as client:
        log.print("Connected, reading characteristics...")

        state1 = await read_all_characteristics(client)
        log.print("Capturing notifications for 3 seconds...")
        notif1 = await capture_notifications(client, 3)

        log.print(f"Read {len(state1)} characteristics")
        log.print(f"Received notifications from {len(notif1)} characteristics")

        # Show current state
        log.print()
        log.print("Current readable values:")
        for uuid, data in state1.items():
            if "error" not in data:
                # Skip showing all-zero or all-FF values in detail
                if all(b == 0 for b in data.get("bytes", [])):
                    log.print(f"  {uuid[:8]}...: [all zeros - {len(data.get('bytes', []))} bytes]")
                elif all(b == 255 for b in data.get("bytes", [])):
                    log.print(f"  {uuid[:8]}...: [all 0xFF - {len(data.get('bytes', []))} bytes]")
                else:
                    log.print(f"  {uuid[:8]}...: {data.get('hex', 'N/A')}")

        # Show notifications
        if notif1:
            log.print()
            log.print("Notifications received:")
            for uuid, notifs in notif1.items():
                for n in notifs:
                    if all(b == 0 for b in n.get("bytes", [])):
                        log.print(f"  {uuid[:8]}...: [all zeros]")
                    elif all(b == 255 for b in n.get("bytes", [])):
                        log.print(f"  {uuid[:8]}...: [all 0xFF]")
                    else:
                        log.print(f"  {uuid[:8]}...: {n.get('hex', 'N/A')}")

        # Explicit disconnect
        log.print()
        log.print("Disconnecting from device...")
        await client.disconnect()

    log.print("Explicitly disconnected.")

    # Wait for BLE stack to fully release the connection
    log.print("Waiting for BLE stack to release connection...")
    await asyncio.sleep(5)

    log.print("-" * 60)
    log.print("Disconnected. Now use the Homedics app to change a setting.")
    log.print("(Change intensity: Low -> Medium, or change color)")
    log.print("-" * 60)

    # Wait for user
    input("\nPress ENTER when you've changed a setting in the app...")

    # CAPTURE STATE 2
    log.print()
    log.print("=" * 60)
    log.print("CAPTURING STATE 2 (after change)")
    log.print("=" * 60)

    log.print(f"Reconnecting to {device.name}...")

    async with BleakClient(device) as client:
        log.print("Connected, reading characteristics...")

        state2 = await read_all_characteristics(client)
        log.print("Capturing notifications for 3 seconds...")
        notif2 = await capture_notifications(client, 3)

        log.print(f"Read {len(state2)} characteristics")

        # Show new state
        log.print()
        log.print("New readable values:")
        for uuid, data in state2.items():
            if "error" not in data:
                if all(b == 0 for b in data.get("bytes", [])):
                    log.print(f"  {uuid[:8]}...: [all zeros - {len(data.get('bytes', []))} bytes]")
                elif all(b == 255 for b in data.get("bytes", [])):
                    log.print(f"  {uuid[:8]}...: [all 0xFF - {len(data.get('bytes', []))} bytes]")
                else:
                    log.print(f"  {uuid[:8]}...: {data.get('hex', 'N/A')}")

    # COMPARE
    log.print()
    log.print("=" * 60)
    log.print("COMPARISON")
    log.print("=" * 60)

    differences = compare_states(state1, state2, "Before", "After")

    if differences:
        log.print(f"Found {len(differences)} characteristic(s) with changes:")
        for diff in differences:
            log.print()
            log.print(f"  UUID: {diff['uuid']}")
            log.print(f"    Before: {diff['Before']}")
            log.print(f"    After:  {diff['After']}")

            # Show byte-level differences
            byte_diff = format_byte_diff(
                diff.get('Before_bytes', []),
                diff.get('After_bytes', [])
            )
            if byte_diff and byte_diff != "N/A":
                log.print(f"    Changed bytes: {byte_diff}")
    else:
        log.print("No differences found in readable characteristics.")
        log.print("The device state may be stored differently or requires")
        log.print("a query command to retrieve.")

    # Compare notifications
    if notif1 or notif2:
        log.print()
        log.print("Notification comparison:")
        log.print(f"  Before: {sum(len(v) for v in notif1.values())} notifications")
        log.print(f"  After:  {sum(len(v) for v in notif2.values())} notifications")

    log.print()
    log.print("Done!")
    log.save()


if __name__ == "__main__":
    label = ""
    if len(sys.argv) > 1:
        label = f"({' '.join(sys.argv[1:])})"

    print("Homedics SereneScent BLE State Comparison Tool")
    print("-" * 40)
    print("This tool captures device state before and after you make")
    print("a change in the Homedics app, then shows the differences.")
    print("-" * 40)
    print()

    asyncio.run(run_comparison(label))
