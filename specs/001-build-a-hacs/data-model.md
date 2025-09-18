# Data Model: Tibber Data Integration

**Date**: 2025-09-18
**Phase**: 1 - Design and Contracts

## Core Entities

### TibberHome
Represents a user's physical location with associated devices.

**Attributes**:
- `home_id`: Unique identifier for the home (UUID format)
- `display_name`: User-friendly name for the home
- `address`: Physical address information
- `time_zone`: Home's timezone for data interpretation
- `devices`: Collection of associated TibberDevice entities

**Relationships**:
- One-to-many with TibberDevice
- Root entity for device hierarchy

**Validation Rules**:
- `home_id` must be valid UUID format
- `display_name` must not be empty
- `time_zone` must be valid IANA timezone identifier

### TibberDevice
IoT devices connected through Tibber platform (EVs, chargers, thermostats, etc.)

**Attributes**:
- `device_id`: Unique device identifier (UUID format)
- `external_id`: Third-party system identifier
- `device_type`: Type classification (EV, charger, thermostat, etc.)
- `manufacturer`: Device manufacturer name
- `model`: Device model identifier
- `name`: User-assigned device name
- `home_id`: Reference to parent TibberHome
- `capabilities`: Collection of DeviceCapability entities
- `attributes`: Collection of DeviceAttribute entities
- `last_seen`: Timestamp of last communication
- `online_status`: Current connectivity state

**Relationships**:
- Many-to-one with TibberHome
- One-to-many with DeviceCapability
- One-to-many with DeviceAttribute

**Validation Rules**:
- `device_id` must be valid UUID format
- `home_id` must reference existing TibberHome
- `device_type` must be from approved enumeration
- `last_seen` must be valid ISO 8601 timestamp

**State Transitions**:
- `online_status`: offline → connecting → online → offline
- Capabilities can be added/removed based on firmware updates
- Attributes update independently from capabilities

### DeviceCapability
Current state values with units for device functions.

**Attributes**:
- `capability_id`: Unique capability identifier
- `device_id`: Reference to parent TibberDevice
- `name`: Capability name (e.g., "charging_power", "temperature")
- `display_name`: User-friendly capability name
- `value`: Current capability value
- `unit`: Measurement unit (W, kWh, °C, etc.)
- `last_updated`: Timestamp of last value update
- `min_value`: Minimum possible value (if applicable)
- `max_value`: Maximum possible value (if applicable)
- `precision`: Decimal precision for display

**Relationships**:
- Many-to-one with TibberDevice

**Validation Rules**:
- `capability_id` must be unique per device
- `value` must be within min/max bounds when specified
- `unit` must be from standardized unit list
- `last_updated` must not be in the future

### DeviceAttribute
Metadata including connectivity status, firmware versions, and identifiers.

**Attributes**:
- `attribute_id`: Unique attribute identifier
- `device_id`: Reference to parent TibberDevice
- `name`: Attribute name (e.g., "firmware_version", "connectivity")
- `display_name`: User-friendly attribute name
- `value`: Current attribute value
- `data_type`: Value data type (string, number, boolean, datetime)
- `last_updated`: Timestamp of last value update
- `is_diagnostic`: Whether attribute is diagnostic information

**Relationships**:
- Many-to-one with TibberDevice

**Validation Rules**:
- `attribute_id` must be unique per device
- `value` must match specified `data_type`
- `data_type` must be from approved enumeration
- Diagnostic attributes should not trigger entity state changes

### OAuthSession
Authentication session for accessing Tibber Data API.

**Attributes**:
- `session_id`: Unique session identifier
- `user_id`: Associated user identifier
- `access_token`: OAuth2 access token
- `refresh_token`: OAuth2 refresh token
- `token_type`: Token type (typically "Bearer")
- `expires_at`: Access token expiry timestamp
- `scopes`: Granted permission scopes
- `created_at`: Session creation timestamp
- `last_refreshed`: Last token refresh timestamp

**Relationships**:
- Independent entity, referenced by API client

**Validation Rules**:
- Tokens must not be logged or exposed in diagnostics
- `expires_at` must be validated before API calls
- `scopes` must include required permissions for operations
- Refresh tokens must be used before access token expiry

**Security Considerations**:
- All token values must be encrypted at rest
- Token refresh must be atomic operation
- Failed refresh attempts should trigger reauthorization flow

## Entity Relationships Diagram

```
TibberHome (1) ──────── (*) TibberDevice (1) ──────── (*) DeviceCapability
    │                         │
    │                         └──────── (*) DeviceAttribute
    │
    └── home_id, display_name, address, time_zone

TibberDevice:
├── device_id, external_id, device_type
├── manufacturer, model, name
├── home_id (FK), last_seen, online_status
│
DeviceCapability:
├── capability_id, device_id (FK), name
├── display_name, value, unit
├── last_updated, min/max_value, precision
│
DeviceAttribute:
├── attribute_id, device_id (FK), name
├── display_name, value, data_type
├── last_updated, is_diagnostic

OAuthSession (Independent):
├── session_id, user_id, access_token
├── refresh_token, token_type, expires_at
├── scopes, created_at, last_refreshed
```

## Data Flow Patterns

### Device Discovery Flow
1. Authenticate with OAuthSession
2. Fetch all TibberHome entities for user
3. For each home, fetch associated TibberDevice entities
4. For each device, populate DeviceCapability and DeviceAttribute collections
5. Register devices in Home Assistant device registry

### State Update Flow
1. Periodic coordinator update (60-second interval)
2. Fetch updated capabilities for all devices
3. Compare with cached values
4. Update changed capabilities and trigger entity updates
5. Update device attributes if changed

### Error Handling Patterns
- **API Unavailable**: Use cached data, set entities to unavailable state
- **Authentication Failed**: Trigger reauth flow, notify user
- **Device Offline**: Update online_status, mark related entities unavailable
- **Invalid Data**: Log warning, use previous valid value, notify user if persistent

## Performance Considerations

### Caching Strategy
- Device metadata (attributes) cached for 1 hour
- Capability values cached until next coordinator update
- Home information cached for 24 hours
- OAuth tokens cached until expiry

### Optimization Patterns
- Batch API calls where possible (single request for all devices)
- Use conditional requests with ETags when supported
- Implement proper pagination for large device lists
- Lazy load device history data only when requested