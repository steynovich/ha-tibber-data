"""Constants for Tibber Data integration."""
from datetime import timedelta
from typing import Final

# Integration details
DOMAIN: Final = "tibber_data"
INTEGRATION_NAME: Final = "Tibber Data"
INTEGRATION_VERSION: Final = "1.0.13"

# Manufacturer information
MANUFACTURER: Final = "Tibber"

# OAuth2 configuration (according to official Tibber docs)
OAUTH2_AUTHORIZE_URL: Final = "https://thewall.tibber.com/connect/authorize"
OAUTH2_TOKEN_URL: Final = "https://thewall.tibber.com/connect/token"
OAUTH2_SCOPES: Final = [
    "openid",
    "profile",
    "email",
    "offline_access",
    "data-api-user-read",
    "data-api-homes-read",
    "data-api-vehicles-read",
    "data-api-chargers-read",
    "data-api-thermostats-read",
    "data-api-energy-systems-read",
    "data-api-inverters-read"
]

# API configuration
API_BASE_URL: Final = "https://data-api.tibber.com"
API_TIMEOUT: Final = 30  # seconds
API_RATE_LIMIT: Final = 100  # requests per 5 minutes
API_RATE_LIMIT_WINDOW: Final = 300  # 5 minutes in seconds

# Retry configuration (according to Tibber API specs)
API_RETRY_MAX_ATTEMPTS: Final = 5
API_RETRY_INITIAL_DELAY: Final = 0.4  # 400 milliseconds
API_RETRY_BACKOFF_FACTOR: Final = 2
API_RETRY_MAX_DELAY: Final = 15.0  # 15 seconds
API_RETRY_JITTER_MAX: Final = 0.25  # 250 milliseconds for Retry-After jitter

# Update intervals
DEFAULT_UPDATE_INTERVAL: Final = timedelta(seconds=60)
MIN_UPDATE_INTERVAL: Final = timedelta(seconds=30)
MAX_UPDATE_INTERVAL: Final = timedelta(minutes=15)

# Token management (according to Tibber specs)
TOKEN_REFRESH_THRESHOLD: Final = 300  # Refresh token 5 minutes before expiry (~1 hour lifetime)
TOKEN_RETRY_DELAY: Final = 30  # seconds between token refresh retries

# Note: Device types removed - API doesn't provide explicit device classification

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
    "energy_storage": {
        "device_class": "energy",
        "state_class": "total",
        "unit": "kWh",
        "icon": "mdi:battery-charging"
    },
    "storage_capacity": {
        "device_class": "energy",
        "state_class": "total",
        "unit": "kWh",
        "icon": "mdi:battery"
    },
    "rated_storage_capacity": {
        "device_class": "energy",
        "state_class": "total",
        "unit": "kWh",
        "icon": "mdi:battery"
    },
    "available_energy": {
        "device_class": "energy",
        "state_class": "total",
        "unit": "kWh",
        "icon": "mdi:battery-charging-50"
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
    },

    # Connectivity capabilities (override API displayName)
    "isonline": {
        "display_name": "Is online",
        "icon": "mdi:wifi-check"
    }
}

# Device attribute types and their sensor/binary sensor mappings
ATTRIBUTE_MAPPINGS: Final = {
    # Connectivity attributes (binary sensors)
    "connectivity.online": {
        "device_class": "connectivity",
        "name_suffix": "Online",
        "icon": "mdi:wifi"
    },
    "isOnline": {
        "device_class": "connectivity",
        "name_suffix": "Is online",
        "icon": "mdi:wifi-check"
    },

    # Firmware and update attributes (binary sensors)
    "firmware.updateAvailable": {
        "device_class": "update",
        "name_suffix": "Update Available",
        "icon": "mdi:update"
    },

    # Charging status (binary sensors)
    "charging_status.is_charging": {
        "device_class": "battery_charging",
        "name_suffix": "Charging",
        "icon": "mdi:battery-charging"
    },

    # Generic problem/issue attributes (binary sensors)
    "status.has_error": {
        "device_class": "problem",
        "name_suffix": "Error",
        "icon": "mdi:alert-circle"
    },

    # Identifier attributes (sensors)
    "vinNumber": {
        "name_suffix": "VIN Number",
        "icon": "mdi:identifier",
        "entity_category": "diagnostic"
    },
    "serialNumber": {
        "name_suffix": "Serial Number",
        "icon": "mdi:identifier",
        "entity_category": "diagnostic"
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
Access Tibber-connected devices via the Tibber Data API with
automatic OAuth2 token refresh.

Platforms: {', '.join(PLATFORMS)}
Update interval: {DEFAULT_UPDATE_INTERVAL.total_seconds()}s
API: {API_BASE_URL}
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