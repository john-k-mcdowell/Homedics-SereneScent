"""Constants for the Homedics SereneScent integration."""

from homeassistant.const import Platform

DOMAIN = "homedics_serenescent"
NAME = "Homedics SereneScent"

# Platforms
PLATFORMS = [Platform.FAN, Platform.LIGHT, Platform.SWITCH, Platform.SENSOR]

# Configuration
CONF_MAC_ADDRESS = "mac_address"

# Device names that we look for during discovery
DEVICE_NAME_PREFIX = "ARMH-"  # Actual device advertises as ARPRP-xxx

# Update interval
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Connection management
CONNECTION_IDLE_TIMEOUT = 120  # seconds - disconnect after this much idle time
CONNECTION_MAX_ATTEMPTS = 3  # Maximum connection retry attempts
CONNECTION_MAX_DELAY = 6.0  # Maximum retry delay in seconds
CONNECTION_DELAY_REDUCTION = 0.75  # Multiply delay by this on success
COMMAND_DELAY = 0.2  # seconds between commands

# BLE Service and Characteristic UUIDs (from protocol reverse engineering)
SERVICE_UUID = "53527aa4-29f7-ae11-4e74-997334782568"
CHAR_TX_UUID = "ee684b1a-1e9b-ed3e-ee55-f894667e92ac"  # Write commands TO device
CHAR_RX_UUID = "654b749c-e37f-ae1f-ebab-40ca133e3690"  # Receive FROM device (notify)

# Advertised service UUID (used for discovery)
ADVERTISED_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"

# Protocol command header
CMD_HEADER = bytes([0xFF, 0xFA])
RESP_HEADER = bytes([0xFF, 0xFB])

# Power commands
CMD_POWER_ON = bytes([0xFF, 0xFA, 0x10, 0x04])
CMD_POWER_OFF = bytes([0xFF, 0xFA, 0x11, 0x04])

# Intensity commands (with pre-calculated checksums)
CMD_INTENSITY_LOW = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x0A, 0x00, 0xF0])
CMD_INTENSITY_MEDIUM = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x14, 0x00, 0x82])
CMD_INTENSITY_HIGH = bytes([0xFF, 0xFA, 0x17, 0x08, 0x00, 0x1E, 0x00, 0x3C])

# Color commands
CMD_COLOR_OFF = bytes([0xFF, 0xFA, 0x16, 0x05, 0x00])
CMD_COLOR_ROTATING = bytes([0xFF, 0xFA, 0x16, 0x05, 0x01])
CMD_COLOR_WHITE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x02])
CMD_COLOR_RED = bytes([0xFF, 0xFA, 0x16, 0x05, 0x03])
CMD_COLOR_BLUE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x04])
CMD_COLOR_VIOLET = bytes([0xFF, 0xFA, 0x16, 0x05, 0x05])
CMD_COLOR_GREEN = bytes([0xFF, 0xFA, 0x16, 0x05, 0x06])
CMD_COLOR_ORANGE = bytes([0xFF, 0xFA, 0x16, 0x05, 0x07])

# Schedule commands
CMD_SCHEDULE_ON = bytes([0xFF, 0xFA, 0x14, 0x04])
CMD_SCHEDULE_OFF = bytes([0xFF, 0xFA, 0x13, 0x04])
CMD_SCHEDULE_SYNC = bytes([0xFF, 0xFA, 0x15, 0x04])

# Schedule sequence helper commands
CMD_SETTINGS_SYNC = bytes([0xFF, 0xFA, 0x20, 0x0E, 0x06, 0x00, 0x16, 0x00, 0x00, 0x1E, 0x00, 0x3C, 0x7F, 0x01])
CMD_SCHEDULE_UNKNOWN1 = bytes([0xFF, 0xFA, 0x12, 0x04])
CMD_SCHEDULE_UNKNOWN2 = bytes([0xFF, 0xFA, 0x46, 0x04])

# Mode commands
CMD_MODE_HOME = bytes([0xFF, 0xFA, 0x43, 0x05, 0x00])
CMD_MODE_SCHEDULE = bytes([0xFF, 0xFA, 0x43, 0x05, 0x01])

# Status query commands
CMD_STATUS_HOME = bytes([0xFF, 0xFA, 0x40, 0x05, 0x00])
CMD_STATUS_SCHEDULE = bytes([0xFF, 0xFA, 0x40, 0x05, 0x01])

# Status response byte positions (16-byte response)
STATUS_BYTE_INTENSITY = 8  # 10=LOW, 20=MEDIUM, 30=HIGH
STATUS_BYTE_COLOR = 12  # 0-7 color index
STATUS_BYTE_SCHEDULE = 13  # 0=OFF, 1=ON
STATUS_BYTE_POWER = 14  # 0=OFF, 1=ON
STATUS_BYTE_MODE = 15  # 0=HOME, 1=SCHEDULE

# Intensity values
INTENSITY_LOW = 10
INTENSITY_MEDIUM = 20
INTENSITY_HIGH = 30

INTENSITY_MAP = {
    INTENSITY_LOW: "low",
    INTENSITY_MEDIUM: "medium",
    INTENSITY_HIGH: "high",
}

INTENSITY_COMMANDS = {
    "low": CMD_INTENSITY_LOW,
    "medium": CMD_INTENSITY_MEDIUM,
    "high": CMD_INTENSITY_HIGH,
}

# Color values and names
COLOR_OFF = 0
COLOR_ROTATING = 1
COLOR_WHITE = 2
COLOR_RED = 3
COLOR_BLUE = 4
COLOR_VIOLET = 5
COLOR_GREEN = 6
COLOR_ORANGE = 7

COLOR_MAP = {
    COLOR_OFF: "off",
    COLOR_ROTATING: "rotating",
    COLOR_WHITE: "white",
    COLOR_RED: "red",
    COLOR_BLUE: "blue",
    COLOR_VIOLET: "violet",
    COLOR_GREEN: "green",
    COLOR_ORANGE: "orange",
}

COLOR_COMMANDS = {
    "off": CMD_COLOR_OFF,
    "rotating": CMD_COLOR_ROTATING,
    "white": CMD_COLOR_WHITE,
    "red": CMD_COLOR_RED,
    "blue": CMD_COLOR_BLUE,
    "violet": CMD_COLOR_VIOLET,
    "green": CMD_COLOR_GREEN,
    "orange": CMD_COLOR_ORANGE,
}

# Entity keys
SENSOR_INTENSITY = "intensity"
SENSOR_COLOR = "color"
SENSOR_SCHEDULE = "schedule"
SWITCH_SCHEDULE = "schedule"
SWITCH_MONITORING = "monitoring"
