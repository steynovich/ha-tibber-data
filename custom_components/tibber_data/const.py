"""Constants for Tibber Data integration."""
from datetime import timedelta
from typing import Final

# Integration details
DOMAIN: Final = "tibber_data"
INTEGRATION_NAME: Final = "Tibber Data"
INTEGRATION_VERSION: Final = "1.0.0"

# Manufacturer information
MANUFACTURER: Final = "Tibber"

# OAuth2 configuration
OAUTH2_AUTHORIZE_URL: Final = "https://data-api.tibber.com/oauth2/authorize"
OAUTH2_TOKEN_URL: Final = "https://data-api.tibber.com/oauth2/token"
OAUTH2_SCOPES: Final = ["USER", "HOME"]

# API configuration
API_BASE_URL: Final = "https://data-api.tibber.com"
API_TIMEOUT: Final = 30  # seconds
API_RATE_LIMIT: Final = 100  # requests per 5 minutes
API_RATE_LIMIT_WINDOW: Final = 300  # 5 minutes in seconds

# Update intervals
DEFAULT_UPDATE_INTERVAL: Final = timedelta(seconds=60)
MIN_UPDATE_INTERVAL: Final = timedelta(seconds=30)
MAX_UPDATE_INTERVAL: Final = timedelta(minutes=15)

# Token management
TOKEN_REFRESH_THRESHOLD: Final = 600  # Refresh token 10 minutes before expiry
TOKEN_RETRY_DELAY: Final = 30  # seconds between token refresh retries

# Device types supported by the integration
DEVICE_TYPES: Final = {
    "EV": "Electric Vehicle",
    "CHARGER": "EV Charger",
    "THERMOSTAT": "Thermostat",
    "SOLAR_INVERTER": "Solar Inverter",
    "BATTERY": "Battery Storage",
    "HEAT_PUMP": "Heat Pump"
}

# Platforms supported by this integration
PLATFORMS: Final = ["sensor", "binary_sensor"]

# Configuration flow constants
CONF_CLIENT_ID: Final = "client_id"
CONF_ACCESS_TOKEN: Final = "access_token"
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_EXPIRES_AT: Final = "expires_at"
CONF_TOKEN_TYPE: Final = "token_type"
CONF_SCOPES: Final = "scopes"

# Entity configuration
ENTITY_ID_FORMAT: Final = "{domain}.{device_name}_{capability_name}"
UNIQUE_ID_FORMAT: Final = "tibber_data_{device_id}_{capability_name}"

# Device capability types and their Home Assistant sensor mappings
CAPABILITY_MAPPINGS: Final = {
    # Energy and power capabilities
    "battery_level": {
        "device_class": "battery",
        "state_class": "measurement",
        "unit": "%",
        "icon": "mdi:battery"
    },
    "charging_power": {
        "device_class": "power",
        "state_class": "measurement",
        "unit": "kW",
        "icon": "mdi:lightning-bolt"
    },
    "energy_consumed": {
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit": "kWh",
        "icon": "mdi:flash"
    },
    "solar_production": {
        "device_class": "energy",
        "state_class": "total_increasing",
        "unit": "kWh",
        "icon": "mdi:solar-power"
    },

    # Temperature capabilities
    "temperature": {
        "device_class": "temperature",
        "state_class": "measurement",
        "unit": "°C",
        "icon": "mdi:thermometer"
    },
    "target_temperature": {
        "device_class": "temperature",
        "state_class": "measurement",
        "unit": "°C",
        "icon": "mdi:thermometer-plus"
    },

    # Current and voltage
    "charging_current": {
        "device_class": "current",
        "state_class": "measurement",
        "unit": "A",
        "icon": "mdi:current-ac"
    },
    "voltage": {
        "device_class": "voltage",
        "state_class": "measurement",
        "unit": "V",
        "icon": "mdi:sine-wave"
    },

    # Generic numeric capabilities
    "signal_strength": {
        "device_class": "signal_strength",
        "state_class": "measurement",
        "unit": "%",
        "icon": "mdi:wifi"
    }
}

# Device attribute types and their binary sensor mappings
ATTRIBUTE_MAPPINGS: Final = {
    # Connectivity attributes
    "connectivity.online": {
        "device_class": "connectivity",
        "name_suffix": "Online",
        "icon": "mdi:wifi"
    },

    # Firmware and update attributes
    "firmware.updateAvailable": {
        "device_class": "update",
        "name_suffix": "Update Available",
        "icon": "mdi:update"
    },

    # Charging status
    "charging_status.is_charging": {
        "device_class": "battery_charging",
        "name_suffix": "Charging",
        "icon": "mdi:battery-charging"
    },

    # Generic problem/issue attributes
    "status.has_error": {
        "device_class": "problem",
        "name_suffix": "Error",
        "icon": "mdi:alert-circle"
    }
}

# Home Assistant device classes for sensors
SENSOR_DEVICE_CLASSES: Final = [
    "battery", "current", "energy", "humidity", "illuminance",
    "power", "power_factor", "pressure", "signal_strength",
    "temperature", "timestamp", "voltage"
]

# Home Assistant device classes for binary sensors
BINARY_SENSOR_DEVICE_CLASSES: Final = [
    "battery", "battery_charging", "cold", "connectivity", "door",
    "garage_door", "gas", "heat", "light", "lock", "moisture",
    "motion", "moving", "occupancy", "opening", "plug", "power",
    "presence", "problem", "running", "safety", "smoke", "sound",
    "update", "vibration", "window"
]

# Error messages for configuration flow
ERROR_MESSAGES: Final = {
    "invalid_auth": "Invalid authentication credentials",
    "invalid_client": "Invalid OAuth client configuration",
    "csrf": "Security validation failed. Please try again.",
    "cannot_connect": "Unable to connect to Tibber Data API",
    "timeout": "Request timed out. Please try again.",
    "rate_limited": "API rate limit exceeded. Please wait and try again.",
    "unknown": "An unknown error occurred"
}

# Home Assistant service names
SERVICE_REFRESH_DEVICES: Final = "refresh_devices"
SERVICE_UPDATE_DEVICE: Final = "update_device"

# Events fired by the integration
EVENT_DEVICE_STATE_CHANGED: Final = f"{DOMAIN}_device_state_changed"
EVENT_DEVICE_ONLINE_STATUS_CHANGED: Final = f"{DOMAIN}_device_online_status_changed"

# Startup banner
STARTUP_MESSAGE: Final = f"""
-------------------------------------------------------------------
{INTEGRATION_NAME} v{INTEGRATION_VERSION}
This integration provides access to Tibber Data API for monitoring
IoT devices connected through the Tibber platform.

Supported devices: {', '.join(DEVICE_TYPES.keys())}
Update interval: {DEFAULT_UPDATE_INTERVAL.total_seconds()}s
API endpoint: {API_BASE_URL}
-------------------------------------------------------------------
"""

# Debug logging configuration
LOGGER_NAME: Final = f"custom_components.{DOMAIN}"

# Data storage keys for coordinator data
DATA_HOMES: Final = "homes"
DATA_DEVICES: Final = "devices"
DATA_COORDINATOR: Final = "coordinator"
DATA_CLIENT: Final = "client"
DATA_OAUTH_SESSION: Final = "oauth_session"

# Device registry configuration
DEVICE_IDENTIFIERS: Final = (DOMAIN,)
DEVICE_DEFAULT_NAME: Final = "Tibber Device"
DEVICE_DEFAULT_MODEL: Final = "Unknown"

# Entity registry configuration
ENTITY_DEFAULT_NAME: Final = "Tibber Sensor"
ENTITY_DISABLED_BY_DEFAULT: Final = False

# Configuration validation
MIN_CLIENT_ID_LENGTH: Final = 10
MAX_CLIENT_ID_LENGTH: Final = 100

# Connection configuration
CONNECTION_TIMEOUT: Final = 10  # seconds
READ_TIMEOUT: Final = 30  # seconds
TOTAL_TIMEOUT: Final = 60  # seconds

# Retry configuration
MAX_RETRIES: Final = 3
RETRY_BACKOFF_FACTOR: Final = 2  # Exponential backoff multiplier
INITIAL_RETRY_DELAY: Final = 1  # seconds

# Cache configuration
CACHE_HOMES_TTL: Final = timedelta(hours=24)  # Cache home info for 24 hours
CACHE_DEVICE_ATTRIBUTES_TTL: Final = timedelta(hours=1)  # Cache device attributes for 1 hour

# Signal strength thresholds (for connectivity binary sensors)
SIGNAL_STRENGTH_THRESHOLD_POOR: Final = 25  # Below this is considered poor
SIGNAL_STRENGTH_THRESHOLD_GOOD: Final = 75  # Above this is considered good