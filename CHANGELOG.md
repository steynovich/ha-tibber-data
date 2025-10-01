# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.14] - 2025-10-01

### Fixed
- **Energy Flow Sensor Names**: Dynamic formatting for energy flow capability display names
  - `grid.energyFlow.sourceGrid.hour` now displays as "Grid Import Energy (Hour)"
  - `load.energyFlow.sourceBattery.hour` now displays as "Load Energy from Battery (Hour)"
  - `grid.energyFlow.sourceBattery.hour` now displays as "Grid Export Energy from Battery (Hour)"
  - Automatically parses energy flow capability paths to generate meaningful names
  - Eliminates confusing API display names like "Energyflow.Hour.Grid.Source.Grid"
- **Connectivity Sensor States**: Fixed ENUM sensors for connectivity capabilities
  - `connectivity.cellular` and `connectivity.wifi` now show proper states instead of "unknown"
  - Dynamic option detection from API's `availableValues` field
  - Fallback to predefined options (Connected, Disconnected, Poor, Fair, Good, Excellent, Unknown)
- **Display Name Improvements**:
  - "firmwareversion" now displays as "Firmware Version"
  - Firmware version attributes marked as diagnostic entities

### Technical
- Added `_format_energy_flow_name()` method to dynamically parse and format energy flow capabilities
- Energy flow formatting takes precedence over API displayName values
- Supports all time periods (hour, day, week, month, year, minute)
- Handles multiple source/destination combinations (load, grid, solar, battery)
- ENUM sensors now check API's `availableValues` for dynamic option lists
- Added capability mappings for connectivity.cellular and connectivity.wifi
- Added attribute mapping for firmwareVersion

## [1.0.13] - 2025-10-01

### Fixed
- **Attribute Sensor Display Names**: Fixed display names for attribute sensors to use custom mappings
  - Serial number now displays as "Serial Number" instead of "Serialnumber"
  - VIN number displays as "VIN Number"
  - Custom mappings in ATTRIBUTE_MAPPINGS now take precedence over API displayName

## [1.0.12] - 2025-10-01

### Added
- **Attribute Sensors**: Non-boolean device attributes now create sensor entities
  - String attributes (e.g., VIN number, serial number) now exposed as sensors
  - Numeric attributes exposed as measurement sensors
  - VIN numbers and serial numbers marked as diagnostic entities
  - Proper ENUM device class for string-valued attribute sensors
  - Entity category support for diagnostic attributes

### Technical
- Added `TibberDataAttributeSensor` class for non-boolean attribute handling
- Extended sensor platform to process all attribute types (not just capabilities)
- Added attribute mappings for common identifiers (vinNumber, serialNumber)
- Proper type annotations with EntityCategory support
- All mypy and ruff checks pass

## [1.0.11] - 2025-10-01

### Fixed
- **OAuth2 Token Refresh**: Fixed automatic token refresh and reauthentication flow
  - Improved token expiration handling with proper error detection
  - Fixed reauth flow to properly trigger when tokens expire
  - Enhanced error handling for API authentication failures

## [1.0.10] - 2025-09-30

### Added
- **Full EV Support**: Complete support for Electric Vehicles with specialized sensors
  - State of charge sensors (battery level)
  - Target charge level sensors
  - Estimated remaining range (automatically converted from meters to kilometers)
  - Vehicle plug status (ENUM sensor: Connected/Disconnected/Unknown)
  - Vehicle charging status (ENUM sensor: Idle/Charging/Complete/Error/Unknown)
- **ENUM Sensors**: String-valued sensors with title case formatting for better readability
- **Automatic Unit Conversion**: Range sensors automatically convert from meters to kilometers
- **Binary Sensor Display Names**: Added "Is online" display name override for isOnline attribute

### Fixed
- **Case-Insensitive Online Detection**: Fixed bug where devices with camelCase attributes (e.g., `isOnline`) were incorrectly detected as offline
  - Now properly detects online status regardless of attribute name casing
  - Critical fix for EVs and other devices using camelCase attribute names
- **Entity Default State**: All entities now enabled by default instead of being disabled when device is temporarily unavailable during setup
- **String Sensor Validation**: ENUM sensors now properly declare device_class and options to prevent Home Assistant validation errors

### Performance
- **66% Reduction in Property Lookups**: Optimized sensor entity initialization
  - Capability data fetched once and cached during initialization
  - Reduced from 3 separate property calls to 1 cached lookup
- **Optimized Online Status Detection**:
  - Fast path when attributes is not a list
  - Single lowercase conversion per attribute ID
  - Direct equality checks instead of `in` operator
  - Early continue for non-dict attributes
  - Extracted helper method to reduce code duplication

### Technical
- Added `SensorDeviceClass.ENUM` for string-valued capabilities
- String sensor values formatted with `.title()` for consistent display
- Range conversion: values in meters with "range" in capability name automatically converted to km
- Optimized `_determine_online_status()` with fast paths and helper methods
- Refactored sensor methods to accept pre-fetched values (value, unit)
- Added comprehensive tests for EV sensors, unit conversion, and online status detection
- All code passes ruff linting with zero issues

## [1.0.9] - 2025-09-30

### Added
- Added entity_category support for diagnostic sensors and attributes
- Entity IDs now include tibber_data_ prefix for better identification
- Compound word detection for proper snake_case formatting (e.g., isonline → is_online)

### Fixed
- Fixed diagnostic sensors not being grouped properly in device view
- Fixed "isonline" and similar connectivity attributes not being marked as diagnostic
- Fixed device names showing as "<no name>" by improving fallback logic to use manufacturer and model information
- Fixed entity_id generation to use human-readable device names instead of UUID hashes
- Signal strength and other technical sensors now correctly marked as diagnostic
- Entity display names are clean (without "Tibber" prefix) while entity_ids maintain tibber_data_ prefix

### Migration Notes
- **Entity IDs now use `tibber_data_` prefix with proper snake_case**: Format is `sensor.tibber_data_<device_slug>_<capability_snake_case>`
  - **To migrate existing entities**: Go to Settings → Devices & Services → Tibber Data → Click on the integration → ⋮ (three dots menu) → "Recreate entities"
  - This will recreate all entities with clean, readable entity_ids
  - Examples:
    - `sensor.tibber_homevolt_teg06_available_energy_stored` → `sensor.tibber_data_homevolt_teg06_storage_available_energy`
    - `sensor.homevolt_teg06_state_of_charge` → `sensor.tibber_data_homevolt_teg06_storage_state_of_charge`
    - `sensor.tibber_homevolt_teg06_wi_fi_signal_strength` → `sensor.tibber_data_homevolt_teg06_wifi_rssi`
    - `binary_sensor.tibber_homevolt_teg06_isonline` → `binary_sensor.tibber_data_homevolt_teg06_is_online`
  - ⚠️ **Important**: Automations and dashboards using old entity_ids will need to be updated after recreation

### Technical
- Implemented entity_category property for TibberDataCapabilityEntity (sensors)
- Implemented entity_category property for TibberDataAttributeEntity (binary sensors)
- Enhanced diagnostic detection to include: online, connected, status, update, version keywords
- Removed name parameter from SensorEntityDescription and BinarySensorEntityDescription to avoid override
- Added suggested_object_id property to all entities using human-readable device slugs
- Added _get_device_slug() helper to generate clean entity_id slugs from device names
- Added _slugify_capability_name() to convert camelCase to snake_case and handle compound words
- Compound word patterns: isonline→is_online, isconnected→is_connected, haserror→has_error, etc.
- Diagnostic keywords include: signal, rssi, wifi, voltage, current, firmware, version, error, etc.
- Entity display names use device name + capability/attribute name (no platform prefix)
- Entity IDs use tibber_data_{device_slug}_{capability} format with proper snake_case

## [1.0.8] - 2025-09-30

### Fixed
- Fixed device names showing as "<no name>" by improving fallback logic to use manufacturer and model information
- Fixed mypy type error in DeviceInfo `via_device` parameter by conditionally adding it only when home_id is present
- Fixed home display name extraction to correctly read from `info.name` field according to Tibber Data API specification
- Updated fallback home display name format from "Tibber Home {id}" to "Tibber Home Name" for better consistency

### Technical
- Enhanced device display name logic with better fallback chain: name → manufacturer + model → model → manufacturer → device ID
- Improved TypedDict compliance for Home Assistant DeviceInfo objects
- Enhanced API response parsing to match official Tibber Data API specification
- All mypy type checks now pass without errors

## [1.0.0] - 2025-01-XX

### Added
- Initial release of Tibber Data integration for Home Assistant
- OAuth2 authentication with PKCE support
- Automatic device discovery for Tibber connected IoT devices
- Support for Electric Vehicles, EV Chargers, Thermostats, Solar Inverters, Battery Storage, and Heat Pumps
- Real-time monitoring with 60-second update intervals
- HACS compatibility
- Comprehensive test coverage with pytest
- Full type annotations with mypy compliance
- Device organization by Tibber homes
- Sensor and binary sensor entities for various device capabilities
- Proper error handling and API rate limiting
- Home Assistant integration with automations and dashboards