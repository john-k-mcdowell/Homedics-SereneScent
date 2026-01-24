"""Constants for the Homedics SereneScent integration."""

from homeassistant.const import Platform

DOMAIN = "homedics_serenescent"
NAME = "Homedics SereneScent"

# Platforms
PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

# Configuration
CONF_MAC_ADDRESS = "mac_address"

# Device names that we look for
# TODO: Update with actual Homedics SereneScent device name patterns
DEVICE_NAME_PREFIX = "SereneScent"

# Update interval
DEFAULT_SCAN_INTERVAL = 30  # seconds

# Connection management
CONNECTION_IDLE_TIMEOUT = 120  # seconds - disconnect after this much idle time
CONNECTION_MAX_ATTEMPTS = 3  # Maximum connection retry attempts
CONNECTION_MAX_DELAY = 6.0  # Maximum retry delay in seconds
CONNECTION_DELAY_REDUCTION = 0.75  # Multiply delay by this on success
DATA_COLLECTION_TIMEOUT = 3  # seconds - wait for device to send data chunks

# BLE Service and Characteristic UUIDs
# TODO: Update with actual Homedics SereneScent BLE service UUIDs
SERVICE_UUID = "00000000-0000-0000-0000-000000000000"
CHARACTERISTIC_UUID_TX = "00000000-0000-0000-0000-000000000000"  # Device transmits data
CHARACTERISTIC_UUID_RX = "00000000-0000-0000-0000-000000000000"  # Device receives commands

# Sensor keys
# TODO: Update with actual sensor types for SereneScent
SENSOR_STATUS = "status"

# Switch keys
SWITCH_MONITORING = "monitoring"
