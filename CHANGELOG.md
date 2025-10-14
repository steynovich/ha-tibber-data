# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.40] - 2025-10-14

### Fixed
- **Entities Becoming Unavailable During Resets**: Fixed cache invalidation bug causing entities to become unavailable when capabilities are temporarily missing from API responses during resets (e.g., hourly sensors at hour boundaries)
  - Root cause: When a capability was temporarily missing from an API response, the cache was marked as "seen" for that coordinator data object, preventing the entity from attempting to fetch fresh data on subsequent property accesses within the same update cycle
  - Bug scenario: Hour boundary → API temporarily doesn't return hourly capability → cache marked as "seen" but returns old data → on next property access, cache "seen" check passes and returns stale data → if API continues to not return capability for multiple updates, entity eventually becomes unavailable
  - Impact: Sensors (especially time-based energy sensors) could become unavailable during normal operation at period boundaries
  - Fix: Modified caching logic to NOT mark cache as "seen" when capability/attribute is temporarily missing, allowing continuous retry of data fetching while still returning cached data to maintain availability
  - Result: Entities continuously attempt to fetch fresh data when capability is missing, immediately recovering when capability reappears in API responses
  - Affects all capability sensors and attribute sensors

### Technical
- Modified `TibberDataCapabilityEntity.capability_data` property - removed cache marking when capability data is not found
- Modified `TibberDataAttributeEntity.attribute_data` property - removed cache marking when attribute data is not found
- Cache now only marked as "seen" when fresh valid data is successfully retrieved
- Maintains backward compatibility - still returns cached data when capability/attribute is missing
- Slightly less efficient (re-fetches on each property access during update cycle when data missing), but prevents entities from becoming stuck unavailable
- All 127 tests pass with no breaking changes

### Impact
- Improved entity reliability during API response inconsistencies
- Entities recover faster when capabilities reappear after temporary absence
- No configuration changes required
- No breaking changes
- Complements fixes in 1.0.39 for better overall entity availability

## [1.0.39] - 2025-10-13

### Fixed
- **Critical: Entities Permanently Unavailable at Hour Boundaries**: Fixed entities becoming permanently unavailable when API temporarily doesn't return capabilities
  - Root cause: When capabilities were temporarily missing from API responses (e.g., hourly energy sensors at top of hour), entities would become unavailable and NEVER recover, even after restart
  - Bug scenario: Hour boundary hits → API doesn't return hourly capability → entity becomes unavailable → capability returns in next update but entity stays unavailable forever → only fix was to remove and re-add entire integration
  - Impact: Entities could become permanently unavailable during normal operation, especially hourly/daily energy flow sensors at period boundaries
  - Fix: Enhanced caching system that preserves capability data when temporarily missing from API, combined with improved availability check that trusts cached data
  - Result: Entities remain available with last known good data when capabilities are temporarily absent from API responses
  - Affects all capability sensors (numeric sensors, ENUM sensors, energy flow sensors)

### Technical
- Enhanced cache tracking in `TibberDataEntity.device_data` property - preserves device data when temporarily missing
- Enhanced cache tracking in `TibberDataCapabilityEntity.capability_data` property - preserves capability data when temporarily missing
- Enhanced cache tracking in `TibberDataAttributeEntity.attribute_data` property - preserves attribute data when temporarily missing
- Updated `TibberDataCapabilityEntity.available` property to trust cached capability data
- When data is missing but cache exists, mark coordinator data as "seen" but keep old cached data
- Only retry fetching when no cache exists at all (new entities)
- All 127 tests pass with no breaking changes

### Impact
- **Critical fix**: Resolves permanent unavailability issue that required removing and re-adding integration
- Entities remain available during API response timing inconsistencies (hour/day/week/month boundaries)
- Fixes issue where entities would never recover after becoming unavailable
- No configuration changes required
- No breaking changes
- Significantly improves entity stability for time-based energy sensors

## [1.0.38] - 2025-10-13

### Fixed
- **Critical: Entity Cache Recovery After Restart**: Fixed entities becoming permanently unavailable after restart
  - Root cause: Cache validation logic incorrectly marked cache as "valid" even when no data was available
  - Bug scenario: Entity starts fresh → capability temporarily missing → cache marked valid with None → entity stays unavailable forever
  - Impact: Entities could never recover if capability data was temporarily missing during Home Assistant restart or integration reload
  - Fix: Removed buggy cache validation that marked cache as valid without data
  - Result: Entities now automatically recover on next coordinator update when data becomes available
  - Affects all entity types: capability sensors, attribute sensors, and binary sensors

### Technical
- Fixed cache validation logic in `TibberDataEntity.device_data` property
- Fixed cache validation logic in `TibberDataCapabilityEntity.capability_data` property
- Fixed cache validation logic in `TibberDataAttributeEntity.attribute_data` property
- Removed lines that set `_cache_coordinator_update` when no data is available
- Added comprehensive test `test_entity_recovers_from_temporary_missing_data_after_restart`
- Cache is now only marked as valid when real data is successfully cached
- All 127 tests pass with new regression test

### Impact
- **Critical fix**: All users should upgrade to prevent permanent entity unavailability after restart
- Entities will now automatically recover from temporary API issues during initialization
- No configuration changes required
- No breaking changes
- Fixes issue where entities would show "unavailable" after restart and never recover

## [1.0.37] - 2025-10-13

### Fixed
- **PowerFlow Percentage Conversion**: Fixed powerFlow sensor values displaying as decimals instead of percentages
  - API returns decimal ratios (0.0-1.0) for power flow distribution sensors
  - Now automatically converts to percentages: 0.9 → 90.0%, 0.1 → 10.0%
  - Only applies to capabilities starting with `powerFlow.` prefix
  - Does NOT affect battery or other percentage sensors (they remain unchanged)
  - Examples: `powerFlow.fromSolar`, `powerFlow.fromGrid`, `powerFlow.toBattery`

### Technical
- Updated `TibberDataCapabilitySensor.native_value` property in sensor.py
- Added conversion logic: `round(value * 100, 1)` for `powerFlow.*` sensors with `%` unit
- Conversion only applies when value is in 0-1 range
- Updated test `test_powerflow_percentage_not_battery` with correct expected values
- All 126 tests pass

### Impact
- Users with powerFlow sensors will see correct percentage values (90% instead of 0.9%)
- No configuration changes required
- Existing automations referencing these sensors may need adjustment if they expect decimal values
- Battery percentage sensors and other percentage sensors are unaffected

## [1.0.36] - 2025-10-13

### Fixed
- **Critical: Entity Cache Invalidation**: Fixed entities becoming unavailable over time despite API returning data
  - Root cause: Coordinator was modifying `self.data` in-place when updating individual devices
  - Entity caching uses `id(coordinator.data)` as cache key - in-place modifications don't change object ID
  - Result: Entity caches retained stale data, causing entities to become unavailable as capabilities changed
  - Fix: Coordinator now creates new data objects instead of modifying in-place
  - This ensures entity caches are properly invalidated on every coordinator update
  - Added comprehensive test `test_cache_invalidation_with_new_coordinator_data_object` to prevent regression

### Technical
- Updated `TibberDataUpdateCoordinator.async_update_device()` to create new data dict
- Changed from `self.data[DATA_DEVICES][device_id] = ...` to creating new data object
- Maintains performance benefits of entity caching while ensuring correct cache invalidation
- All 126 tests pass with new cache invalidation test added

### Impact
- **All users should upgrade**: This fixes a critical bug causing entities to become unavailable over time
- No configuration changes required
- Existing entities will remain available after update
- Entity caching performance improvements from v1.0.32 are maintained

## [1.0.35] - 2025-10-10

### Fixed
- **Entity ID Naming Consistency**: Fixed entity_id mismatches when recreating entities
  - `suggested_object_id` now uses formatted display names instead of raw API capability names
  - Prevents Home Assistant from suggesting different entity_ids when recreating entities
  - Results in more readable entity_ids (e.g., `battery_from_grid_hour` instead of `energy_flow_hour_battery_source_grid`)
  - Applies to both capability entities (sensors) and attribute entities (binary_sensors)
  - Ensures consistency between entity `name` and `suggested_object_id` properties

### Changed
- **API Client Encapsulation**: Improved access token management
  - Added public `set_access_token()` method to TibberDataClient
  - Replaced all direct `_access_token` private attribute access with public method
  - Better encapsulation and maintainability
  - Affects coordinator and config_flow modules

### Breaking Changes
⚠️ **Important**: This release changes entity_ids to use more readable formats. When you update:

**What happens**:
- Existing entity_ids remain unchanged (Home Assistant preserves them)
- New entities or recreated entities will use the new, more readable format
- If you remove and re-add the integration, all entities will get the new readable entity_ids

**Impact**:
- Old: `sensor.tibber_data_homevolt_teg06_energy_flow_hour_battery_source_grid`
- New: `sensor.tibber_data_homevolt_teg06_battery_from_grid_hour`

**Migration**:
- No action required for existing installations (entity_ids are preserved)
- If you recreate entities, update any automations/dashboards that reference the old entity_ids
- The new format is significantly more readable and consistent

### Technical
- Updated `TibberDataCapabilityEntity.suggested_object_id` to use `_get_capability_display_name()`
- Updated `TibberDataAttributeEntity.suggested_object_id` to use `_entity_name_suffix`
- Added `TibberDataClient.set_access_token()` public method
- Updated 3 locations to use new public method instead of private attribute access
- All 125 tests pass
- All ruff and mypy checks pass
- Updated test assertions to reflect new entity_id format

## [1.0.34] - 2025-10-10

### Fixed
- **Entity Availability After Restart**: Fixed entities becoming unavailable after Home Assistant restart
  - Simplified availability logic to trust coordinator/cached data and device online status
  - Removed dependency on `last_update_success` flag that could cause false unavailability
  - Entities now available as soon as coordinator has data, regardless of update success state
  - Prevents false unavailability during startup timing issues or coordinator transitions
  - More predictable and robust availability behavior across all scenarios

### Changed
- **Availability Logic Simplification**: Streamlined entity availability determination
  - Entity is available if: device data exists (coordinator or cache) AND device is online
  - Removed complex checking of `last_update_success` which could be unreliable after restarts
  - Trusts cached data to maintain availability during transient issues
  - Cleaner, more maintainable code with fewer edge cases

### Technical
- Updated `TibberDataEntity.available` property to use simplified logic
- Entity availability now only checks device data existence and online status
- Removes race conditions between coordinator first refresh and entity initialization
- All 125 tests pass
- All ruff and mypy checks pass
- Backward compatible - no breaking changes

## [1.0.33] - 2025-10-09

### Fixed
- **Sensor Availability**: Fixed sensors flickering unavailable during normal coordinator refresh cycles
  - Sensors no longer briefly become unavailable every 60 seconds during data updates
  - Improved cache resilience to maintain previous data during coordinator transitions
  - Changed availability check from `coordinator.data` to `coordinator.last_update_success`
  - Leverages Home Assistant's `CoordinatorEntity` built-in state management
  - Sensors remain available with last known good data during transient network errors

### Changed
- **Entity Data Caching**: Enhanced caching logic for `device_data`, `capability_data`, and `attribute_data`
  - Cache now maintains previous valid data when coordinator.data is None or missing expected data
  - Only updates cache when new valid data is available
  - Prevents brief None returns during coordinator data object transitions
  - Improves stability and user experience during normal operation

### Technical
- Updated `TibberDataEntity.available` property to use `last_update_success`
- Updated `device_data` property with resilient caching that maintains previous data
- Updated `capability_data` property with resilient caching that maintains previous data
- Updated `attribute_data` property with resilient caching that maintains previous data
- Updated test suite to reflect new cache persistence behavior
- All 125 tests pass
- All ruff checks pass

## [1.0.32] - 2025-10-09

### Fixed
- **Periodic Energy Sensors**: Fixed sensors becoming unavailable when resetting to 0 at period boundaries
  - Periodic energy sensors (`.hour.`, `.day.`, `.week.`, `.month.`, `.year.`) now have **NO state_class**
  - Allows hourly/daily/weekly/monthly energy flow sensors to reset to 0 without becoming unavailable
  - Non-periodic energy sensors (storage levels, lifetime totals) continue using `TOTAL` state_class
  - Examples affected: `energyFlow.hour.battery.charged`, `energyFlow.day.grid.imported`, `energyFlow.week.solar.produced`
  - Examples unaffected: `storage.availableEnergy` (uses `TOTAL` state_class)
- **Charging Sensors**: Fixed charging current/voltage sensors incorrectly marked as diagnostic
  - Charging current (A) and voltage (V) sensors are now shown as normal operational sensors
  - Other voltage/current sensors (non-charging) remain diagnostic
  - Examples affected: `charging.current.max`, `charging.current.offlineFallback`
  - Improves visibility of key EV charger operational metrics

### Changed
- **State Class Assignment**: Improved logic for determining sensor state classes
  - Periodic energy sensors check for period indicators (`.hour.`, `.day.`, etc.) before assigning state_class
  - Non-periodic energy sensors (storage, lifetime totals) use `TOTAL` state_class for fluctuation support
- **Entity Categories**: Refined diagnostic classification logic
  - Charging-related sensors (containing "charging" or "charge") are never marked as diagnostic
  - Voltage/current sensors only marked as diagnostic when not charging-related

### Migration Notes
- **Existing installations must remove and re-add the integration** to update state_class for existing sensors
- Home Assistant caches state_class in entity registry - code changes don't update existing entities
- Migration steps:
  1. Update to v1.0.32 via HACS
  2. Remove integration: Settings → Devices & Services → Tibber Data → ⋮ → Delete
  3. Re-add integration: Settings → Devices & Services → Add Integration → Tibber Data
  4. Re-authenticate with Tibber account
- Statistics/history data will be preserved (stored separately from entity registry)

### Technical
- Updated `_infer_state_class_from_value()` to detect periodic energy sensors and return `None`
- Updated `entity_category` property to exclude charging-related sensors from diagnostic classification
- Updated documentation in CLAUDE.md and README.md with new state_class behavior
- All sample devices verified: zappi.json (EV charger), pv1.json (solar inverter)

## [1.0.31] - 2025-10-08

### Added
- **Force Refresh Service**: Added `tibber_data.refresh` service to force immediate data refresh
  - Can refresh all config entries or a specific config entry by ID
  - Bypasses normal update interval for on-demand data updates
  - Useful for automations that need current data before making decisions
  - Service is registered when first config entry is added
  - Service is removed when last config entry is unloaded

### Technical
- Added service registration in `async_setup_entry()` with schema validation
- Service handler supports optional `config_entry_id` parameter
- Uses `coordinator.async_request_refresh()` for immediate refresh
- Created `services.yaml` with service documentation for UI
- All ruff and mypy checks pass
- All 125 tests pass

## [1.0.30] - 2025-10-08

### Changed
- **Cleaner Entity Attributes**: Removed "device_online" attribute from all capability entities (sensors)
  - Entities now only show relevant attributes (e.g., "last_updated" for capabilities)
  - Device online status is still reflected through entity availability
  - Reduces clutter in entity attribute listings
  - No functional impact - availability behavior unchanged

### Fixed
- **Test Suite**: Updated test to reflect removal of device_online attribute
  - Fixed `test_sensor_attributes` test that was checking for removed attribute
  - All 17 sensor tests now pass

### Technical
- Removed `device_online` attribute addition in `TibberDataCapabilityEntity.extra_state_attributes`
- Entity availability continues to be controlled by device online status via the `available` property
- Cleaner separation of concerns - online status is an availability concern, not an attribute
- Updated test suite to match current implementation

## [1.0.29] - 2025-10-08

### Added
- **Diagnostics Support**: Added comprehensive diagnostics data for troubleshooting
  - Config entry diagnostics show all homes, devices, coordinator status, and complete API response
  - Device-specific diagnostics show detailed device data from the API
  - Automatic redaction of sensitive information (tokens, VINs, serial numbers, emails, phone numbers, addresses, coordinates, user/home IDs)
  - Accessible via Settings → Devices & Services → Tibber Data → Download diagnostics
  - Includes last successful API response for debugging integration issues
  - Helpful for troubleshooting device availability, sensor values, and API communication

### Technical
- Created `diagnostics.py` with `async_get_config_entry_diagnostics()` and `async_get_device_diagnostics()`
- Added `"diagnostics": ["config_entry", "device"]` to manifest.json
- Uses Home Assistant's `async_redact_data()` for secure data sanitization
- TO_REDACT list covers all common sensitive fields (tokens, identifiers, contact info, location data)

## [1.0.28] - 2025-10-08

### Fixed
- **All Energy Sensors State Class**: Fixed all energy sensors (kWh/Wh) becoming unavailable when values reset
  - ALL energy sensors now use `TOTAL` state class instead of `TOTAL_INCREASING`
  - Prevents Home Assistant from marking sensors unavailable when periodic values reset to 0
  - Affects all energy sensors: hourly/daily/weekly/monthly energy flow sensors AND storage sensors
  - All Tibber Data API energy sensors are either periodic (reset at boundaries) or storage (can fluctuate)
  - None are lifetime cumulative counters, so `TOTAL_INCREASING` was inappropriate for all of them
  - Examples: `energyFlow.hour.battery.charged`, `energyFlow.day.grid.imported`, `storage.availableEnergy`

### Migration Required
- **Existing users must remove and re-add the integration** to update entity state classes
- Home Assistant caches state class in entity registry - restart alone won't fix existing entities
- Steps: Remove integration → Re-add → Re-authenticate → Entities recreated with correct state class
- Statistics history is preserved during this process

### Technical
- Simplified `_infer_state_class_from_value()` - all energy units (kWh, Wh) now return `SensorStateClass.TOTAL`
- Removed complex keyword-based logic for consumption/production/storage
- This allows periodic values to reset and storage values to fluctuate without errors
- Added comprehensive test coverage including imported/exported sensors that previously used TOTAL_INCREASING
- All tests pass (118 passed, 7 skipped)

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