# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.27] - 2025-10-08

### Fixed
- **Entity Availability During Temporary Failures**: Entities no longer become unavailable during brief network issues or API timeouts
  - Entities now remain available with cached data when coordinator updates fail temporarily
  - Entities only become unavailable when device is actually offline according to API
  - Improved availability logic to check for cached coordinator data instead of update success flag
  - Prevents sensor flickering during transient network problems

### Technical
- Enhanced `available` property in `TibberDataEntity` to use cached coordinator data
- Checks `coordinator.data` (which persists across failed updates) instead of `last_update_success`
- Entities use device's last known online state from cached data
- Added comprehensive test coverage for coordinator data caching behavior on update failures
- All tests pass (117 passed, 7 skipped)

## [1.0.26] - 2025-10-08

### Fixed
- **Battery Device Class Detection**: Fixed incorrect battery percentage display in Home Assistant device cards
  - Only percentage sensors with battery/storage-related keywords now get battery device class
  - Prevents power flow percentages (e.g., `powerFlow.fromSolar` at 0.9%) from being identified as battery sensors
  - Device cards now correctly show actual battery level (e.g., `storage.stateOfCharge` at 95.5%)
  - Power flow percentage sensors (`powerFlow.toGrid`, `powerFlow.fromSolar`, etc.) no longer have device class
  - Battery/storage sensors (`storage.stateOfCharge`, `battery.level`, etc.) correctly get battery device class

### Technical
- Enhanced `_infer_device_class_from_value_and_unit()` with keyword-based filtering for percentage sensors
- Keywords checked: `battery`, `storage`, `stateofcharge`, `charge`
- Percentage sensors without these keywords get no device class instead of battery
- Added comprehensive test coverage for both power flow percentages and battery percentages
- All existing power/energy/temperature sensors retain their correct device classes
- All tests pass (116 passed, 7 skipped)

## [1.0.25] - 2025-10-08

### Fixed
- **Energy Flow Duplicate Names**: Fixed remaining duplicate sensor names for energy flow capabilities
  - API uses `source.grid` format (with dot) instead of `sourceGrid` (camelCase)
  - Updated parser to handle both `energyFlow.day.battery.source.grid` and legacy `sourceGrid` formats
  - All 70 energy flow capabilities now have unique, descriptive names
  - Added support for "generated" action (e.g., "Load Generated")
  - Tested against actual API response data to ensure 100% unique names

### Technical
- Enhanced source parsing with state tracking for multi-part source notation
- Handles `source.grid`, `source.solar`, `source.battery`, `source.load` patterns
- Backward compatible with `sourceGrid` camelCase format
- Validated against `samples/response.json` with 70 energy flow capabilities
- All tests pass (114 passed)

## [1.0.24] - 2025-10-08

### Changed
- **Code Refactoring**: Simplified entity naming logic for better maintainability
  - Split `name` property into focused helper methods (`_get_capability_display_name()`, `_has_duplicate_display_name()`)
  - Refactored `_format_energy_flow_name()` with data-driven approach using naming rules dictionary
  - Reduced energy flow naming method from ~120 lines to ~80 lines (33% reduction)
  - Replaced nested if/elif chains with cleaner, more maintainable structure
  - No functional changes - all existing behavior preserved

### Technical
- Main `name` property reduced from 54 lines to 15 lines
- Energy flow naming now uses declarative `naming_rules` dict instead of procedural conditionals
- Easier to extend with new destinations or modify naming patterns
- Improved separation of concerns and testability
- All 114 tests pass with full mypy and ruff compliance

## [1.0.23] - 2025-10-08

### Fixed
- **Duplicate Entity Display Names**: Automatically detects and resolves duplicate sensor names
  - When multiple capabilities have the same `displayName` from API, adds capability prefix to make unique
  - Example: `battery.level` and `storage.level` both with displayName "Level" now become "Battery Level" and "Storage Level"
  - Applies to all capability types: battery.power + grid.power → "Battery Power" and "Grid Power"
  - Prevents confusion in Home Assistant UI where multiple sensors had identical display names
  - Entity IDs remain unique (as before), but now display names are also unique

- **Energy Flow Format Support**: Added support for alternative energy flow capability naming format
  - Now handles both `{destination}.energyFlow.{period}.{source}` and `energyFlow.{period}.{destination}.{source}` formats
  - Fixed issue where `energyFlow.month.battery.sourceGrid`, `energyFlow.month.battery.sourceSolar`, etc. all had name "Battery Energy (Month)"
  - Now properly generates unique names: "Battery from Grid (Month)", "Battery from Solar (Month)", "Battery Self-Charge (Week)"
  - Supports all energy flow combinations across battery, grid, load, and solar with proper naming

### Technical
- Enhanced `TibberDataCapabilityEntity.name` property to detect displayName conflicts
- Automatically adds capability prefix (first part before dot) when duplicates detected
- Updated `_format_energy_flow_name()` to parse both capability name formats from Tibber API
- Added special case handling for "Battery from Battery" → "Battery Self-Charge"
- Only applies prefix when necessary - capabilities with unique displayNames remain unchanged
- No breaking changes - existing entity IDs and unique_ids remain the same

## [1.0.22] - 2025-10-08

### Fixed
- **Energy Flow Sensor Names**: Comprehensive improvements to energy flow sensor display names
  - Battery sensors now properly differentiated: "Battery Charged", "Battery Discharged", "Battery from Grid", "Battery from Load", "Battery from Solar"
  - Solar sensors now properly differentiated: "Solar Produced", "Solar Consumed", "Solar Production"
  - Grid sensors now properly named: "Grid Import", "Grid from Battery", "Grid from Solar"
  - Load sensors now properly named: "Load from Battery", "Load from Grid", "Load from Solar"
  - All time periods supported: Hour, Day, Week, Month, Year with period suffix (e.g., "Battery Charged (Day)")
  - Added support for actions: charged, discharged, produced, consumed, imported, exported
- **Device Name Handling**: Fixed "no_name" prefix appearing in entity IDs
  - Now handles case-insensitive variations of "no name" from API (e.g., "No name", "no name", "<no name>")
  - Falls back to manufacturer + model when device name is invalid
  - Prevents entity IDs like "sensor.no_name_energyflow_..." from being created

### Technical
- Enhanced `_format_energy_flow_name()` to parse additional action keywords
- Added destination-specific logic for Battery, Grid, Load, and Solar energy flows
- Case-insensitive device name validation in `_get_device_display_name()`
- All energy flow sensors now have unique, meaningful display names across all time periods

## [1.0.21] - 2025-10-07

### Performance
- **Entity Data Caching**: Implemented property-level caching for entity data lookups
  - Added caching for `device_data`, `capability_data`, and `attribute_data` properties
  - Reduces sensor state update time from ~1.5 seconds to <0.5 seconds (67% improvement)
  - 85% reduction in list iterations during state updates (from ~350-400 to ~50 per sensor)
  - Cache automatically invalidates when coordinator fetches new data
  - Eliminates repeated linear searches through device capabilities/attributes during each state update
  - Critical fix for "Updating state took X.XXX seconds" warnings with many sensors

### Technical
- Cache key strategy uses `id(coordinator.data)` for automatic invalidation on coordinator updates
- Stores references (not copies), so in-place modifications remain visible
- Each entity instance maintains its own cache per coordinator data object
- During state updates, Home Assistant calls 7-8 properties that previously triggered redundant data lookups
- Added comprehensive test coverage in `tests/test_entity_caching.py` with 8 tests
- All tests pass (121 total: 114 passed, 7 skipped)
- Full mypy and ruff compliance maintained
- Backward compatible - no breaking changes

## [1.0.20] - 2025-10-06

### Fixed
- **Reauth Flow Error Handling**: Fixed test failure where reauth flow creation errors could obscure authentication failures
  - Added defensive error handling around reauth flow creation in coordinator
  - Reauth flow creation failures are now logged but don't prevent proper authentication error reporting
  - Ensures `UpdateFailed("Authentication failed")` is always raised correctly for auth errors
  - Prevents test environment mocking issues from causing incorrect error messages
  - Critical fix for proper error propagation during token refresh failures

### Technical
- Added try-except wrapper around `async_create_task()` for reauth flow creation
- Added null check for `config_entry` before attempting reauth flow
- Reauth flow creation errors are logged but don't interfere with main authentication error
- All tests pass (106 passed, 7 skipped)
- Full mypy and ruff compliance maintained

## [1.0.19] - 2025-10-06

### Fixed
- **Network Error Handling**: DNS timeouts and transient network errors no longer trigger unnecessary reauthentication
  - Token refresh now distinguishes between network errors (DNS, timeouts, connection issues) and authentication failures
  - Network errors raise `UpdateFailed` and allow automatic retry on next update cycle
  - Authentication errors (401, invalid tokens, expired refresh tokens) still properly trigger reauth flow
  - Prevents frustrating scenario where temporary DNS issues force users to re-authenticate with valid tokens

### Technical
- Enhanced error categorization in `coordinator._get_access_token()` to identify error types
- Network errors: timeout, DNS, connection failures → retry without reauth
- Auth errors: 401, unauthorized, invalid_grant, expired tokens → trigger reauth
- Added comprehensive test coverage for both error scenarios
- Follows defensive error handling pattern with conservative defaults

## [1.0.18] - 2025-10-06

### Fixed
- **Unhandled Task Exception**: Fixed "Task exception was never retrieved" error during token refresh failures
  - Reauth flow now properly triggered using `async_create_task()` instead of unawaited coroutine
  - Prevents integration failure when DNS or network issues occur during token refresh
  - Proper async task handling ensures stable operation when Tibber OAuth endpoints are unreachable
  - Critical fix for integration stability during network timeouts

### Technical
- Changed reauth flow initialization from `config_entry.async_start_reauth()` to `hass.async_create_task()` pattern
- Properly handles async task creation in exception handlers that need to re-raise
- Follows Home Assistant best practices for triggering reauth from coordinators
- Ensures reauth flow runs without blocking or creating unhandled coroutines

## [1.0.17] - 2025-10-02

### Fixed
- **Integration Entry Loop Prevention**: Fixed issue where failed initial data fetch could cause integration setup to proceed anyway
  - Setup now properly fails if `async_config_entry_first_refresh()` raises an exception
  - Prevents multiple duplicate integration entries from being created
  - Ensures clean error handling during OAuth or API failures

### Technical
- Removed try-catch wrapper around `async_config_entry_first_refresh()` in `async_setup_entry()`
- Home Assistant will now properly handle setup failures and trigger reauth when needed
- Prevents entry creation loops when API or authentication issues occur

## [1.0.16] - 2025-10-02

### Fixed
- **Dynamic Sensor Properties**: Fixed Home Assistant error where ENUM sensors were incorrectly assigned numeric state classes
  - `device_class`, `state_class`, and `native_unit_of_measurement` are now determined dynamically at runtime
  - Prevents errors like "could not convert string to float: 'connected'" for string-valued sensors
  - Critical fix for EV connector status and charging status sensors
  - All sensor properties now wait for coordinator data before determining types

### Technical
- Made `device_class` a dynamic property instead of static entity description value
- Made `state_class` a dynamic property that evaluates when data is available
- ENUM sensors (string values) correctly get `device_class=ENUM` and `state_class=None`
- Numeric sensors get appropriate state classes (MEASUREMENT, TOTAL, TOTAL_INCREASING)
- Properties gracefully handle initialization when coordinator data is not yet available
- All tests pass with dynamic property implementation
- Full mypy and ruff compliance maintained

## [1.0.15] - 2025-10-01

### Fixed
- **ENUM Sensor Value Formatting**: Fixed title case formatting for all string sensor values
  - Now applies `.title()` to all string values, not just when device_class is explicitly ENUM
  - Ensures connectivity sensors (wifi, cellular) show "Connected" instead of "connected"
  - More robust handling when entity description device_class is not set during initialization

### Technical
- Improved `native_value` property to handle string formatting even when device_class is None
- Fallback logic ensures all string sensor values get proper title case formatting

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