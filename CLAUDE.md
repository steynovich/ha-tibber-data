# ha-tibber-data Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-09-18

## Active Technologies
- Python 3.13+ (001-build-a-hacs)
- Home Assistant Core, aiohttp, HACS framework (001-build-a-hacs)

## Project Structure
```
custom_components/tibber_data/    # Home Assistant integration
├── __init__.py                   # Component setup and entry point
├── manifest.json                 # Integration metadata for HACS
├── config_flow.py               # OAuth2 configuration flow
├── const.py                     # Constants and configuration
├── coordinator.py               # Data update coordinator
├── entity.py                    # Base entity classes
├── sensor.py                    # Sensor entities
├── binary_sensor.py             # Binary sensor entities
├── switch.py                    # Switch entities (if applicable)
└── api/                         # API client
    ├── __init__.py
    ├── client.py                # Tibber Data API client
    └── models.py                # Data models

tests/                           # Comprehensive test suite
├── conftest.py                  # Test configuration
├── test_init.py                 # Component initialization tests
├── test_config_flow.py          # Configuration flow tests
├── test_coordinator.py          # Data coordinator tests
└── test_api/                    # API client tests
    ├── test_client.py
    └── test_models.py

.github/workflows/               # GitHub Actions
├── validate.yml                 # HACS validation
├── test.yml                     # Automated testing
└── release.yml                  # Release automation

specs/001-build-a-hacs/          # Design documentation
├── spec.md                      # Feature specification
├── plan.md                      # Implementation plan
├── research.md                  # Research findings
├── data-model.md                # Entity data models
├── quickstart.md                # Testing scenarios
└── contracts/                   # API contracts
    └── api-specification.yaml
```

## Commands
# Testing
pytest tests/                    # Run all tests
pytest tests/test_config_flow.py # Test configuration flow
pytest tests/test_coordinator.py # Test data coordinator

# HACS Validation
# Run HACS action validation in GitHub Actions

# Home Assistant Integration
# Install via HACS in Home Assistant UI

## Code Style
- Full async operations (no blocking calls)
- Complete type annotations with mypy strict compliance
- Follow Home Assistant integration patterns
- Use DataUpdateCoordinator for API polling
- Implement proper OAuth2 flows with PKCE
- HACS-compatible structure and metadata
- Optimized code with minimal property lookups and efficient algorithms

## Key Implementation Details

### Authentication
- OAuth2 Authorization Code Flow with PKCE
- Contact Tibber support for client registration
- Scopes: USER, HOME for device access
- Rate limit: 100 requests per 5 minutes

### Data Management
- 60-second coordinator refresh interval
- Async-only operations for HA compatibility
- Entity hierarchy: Homes → Devices → Capabilities/Attributes
- Proper error handling and recovery

### Quality Requirements (Platinum Tier)
- Comprehensive test coverage with pytest-homeassistant-custom-component
- Full type annotations and mypy compliance
- Efficient async operations with minimal resource usage
- Complete documentation and user guides
- HACS validation and automated GitHub Actions

## Recent Changes
- 001-build-a-hacs: Added HACS-compatible Tibber Data API integration with Platinum quality standards
- 2025-09-30: Added full EV support with string-valued ENUM sensors, range conversion, and improved online status detection
- 2025-09-30: Code optimizations - reduced property lookups by 66%, optimized online status detection with fast paths
- 2025-10-01: Fixed OAuth2 token refresh and reauthentication flow
- 2025-10-01: Added attribute sensors for non-boolean device attributes (VIN number, serial numbers, etc.)
- 2025-10-01: Dynamic energy flow sensor naming - automatically formats confusing energy flow capability names into readable display names
- 2025-10-01: Fixed ENUM sensor value formatting to ensure consistent title case for all string sensor values
- 2025-10-02: Fixed dynamic sensor properties - device_class and state_class now determined at runtime to prevent ENUM sensor errors
- 2025-10-07: Added entity data caching - device_data, capability_data, and attribute_data properties now cache lookups per coordinator update cycle, reducing sensor state update time from ~1.5s to <0.5s (85% reduction in iterations)
- 2025-10-08: Comprehensive energy flow sensor naming improvements - all battery, solar, grid, and load sensors now have unique meaningful names across all time periods (hour, day, week, month, year)
- 2025-10-08: Fixed "no_name" entity ID prefix issue - case-insensitive handling of invalid device names with proper fallback to manufacturer/model
- 2025-10-08: Fixed battery device class detection - only percentage sensors with battery/storage-related keywords get battery device class, preventing power flow percentages from being incorrectly identified as battery sensors
- 2025-10-08: Fixed entity availability during temporary failures - entities now remain available with cached data when coordinator updates fail temporarily (network issues, API timeouts), only becoming unavailable when device is actually offline
- 2025-10-09: Fixed periodic energy flow sensors becoming unavailable at period boundaries - hourly/daily/weekly/monthly/yearly sensors now have NO state_class (instead of TOTAL or TOTAL_INCREASING), preventing unavailability when values reset to 0 at period boundaries
- 2025-10-09: Fixed sensors flickering unavailable during coordinator refresh - changed availability check to use last_update_success instead of coordinator.data, and enhanced cache resilience to maintain previous data during transitions, eliminating brief unavailability every 60 seconds
- 2025-10-08: Removed device_online attribute from capability entities - cleaner entity attributes, online status reflected through availability only
- 2025-10-08: Updated test suite to match removal of device_online attribute
- 2025-10-10: Fixed entity availability after Home Assistant restart - simplified availability logic to trust cached/coordinator data and device online status, removing dependency on last_update_success flag that could cause false unavailability after restart

## EV Support Features

### Sensor Types
The integration supports numeric, string-valued, and attribute sensors for EVs and other devices:

**Numeric Capability Sensors:**
- `storage.stateOfCharge` - Battery state of charge (%)
- `storage.targetStateOfCharge` - Target charge level (%)
- `range.remaining` - Estimated range (automatically converted from meters to km)

**ENUM Capability Sensors (string-valued):**
- `connector.status` - Vehicle plug status ("Connected", "Disconnected", "Unknown")
- `charging.status` - Charging status ("Idle", "Charging", "Complete", "Error", "Unknown")
- String values are automatically formatted with title case for better display

**Attribute Sensors (from device attributes):**
- `vinNumber` - Vehicle identification number (diagnostic sensor)
- `serialNumber` - Device serial number (diagnostic sensor)
- All non-boolean string/numeric attributes exposed as sensors
- Boolean attributes remain as binary sensors

### Unit Conversions
- Range sensors automatically convert from meters (m) to kilometers (km)
- Example: API value of 67000m displays as 67.0 km
- Conversion applies to any capability with "range" in the name and unit "m"

### Device Online Status Detection
The integration uses case-insensitive attribute matching to detect device online status:
- Checks for `isOnline`, `isonline`, `connectivity.*` attributes
- Falls back to `lastSeen` timestamp (online if seen within 5 minutes)
- Defaults to online if no status information available
- Critical for EVs which may use camelCase attribute names

### Entity Configuration
- All entities are enabled by default (changed from availability-based)
- Entity availability is handled dynamically based on device online status
- ENUM sensors use `SensorDeviceClass.ENUM` with no `state_class`
- Range sensors maintain `state_class="measurement"` for statistics

### Device Class Mappings
The integration automatically assigns Home Assistant device classes based on sensor units:

| Unit | Device Class | State Class | Notes |
|------|--------------|-------------|-------|
| W, kW | `power` | `measurement` | Power sensors (charging, solar, load) |
| Wh, kWh | `energy` | `total` or none | Storage/lifetime totals use `total`, periodic sensors use none |
| % | `battery` | `measurement` | Only for battery/storage sensors (stateOfCharge, battery.level) |
| % | none | none | Power flow percentages (distribution ratios) |
| °C, °F | `temperature` | `measurement` | Temperature sensors |
| A | `current` | `measurement` | Current sensors |
| V | `voltage` | `measurement` | Voltage sensors |
| dBm | `signal_strength` | `measurement` | WiFi/Cellular signal strength |
| string | `enum` | none | Status sensors (charging, connector, connectivity) |

**Important Notes:**
- **Periodic energy sensors** (containing `.hour.`, `.day.`, `.week.`, `.month.`, `.year.`) have **NO state_class** to allow resets to 0 at period boundaries
- **Non-periodic energy sensors** (storage levels, lifetime totals) use `TOTAL` state class to allow fluctuations
- Battery device class only assigned to percentage sensors with battery/storage keywords in capability name
- ENUM sensors (string values) automatically get title case formatting ("Charging" not "charging")

## Performance Optimizations

### Entity Data Caching (2025-10-07)
- **Property-level caching**: `device_data`, `capability_data`, and `attribute_data` properties now cache lookups
- **Cache key strategy**: Uses `id(coordinator.data)` as cache key - automatically invalidates when coordinator updates
- **Impact**: During each state update, Home Assistant calls 7-8 properties that access capability_data
  - Before: ~350-400 list iterations per sensor per update (for 50 capabilities)
  - After: ~50 iterations per sensor per update (85% reduction)
  - Result: Sensor state update time reduced from ~1.5s to <0.5s
- **Cache behavior**:
  - Cache is per entity instance and per coordinator data object
  - Stores references (not copies), so in-place modifications are visible
  - Automatically invalidated when coordinator fetches new data
- **Test coverage**: Added comprehensive caching tests in `tests/test_entity_caching.py`

### Sensor Entity Initialization
- **Reduced property lookups**: Capability data is fetched once and cached during entity initialization
- Changed from 3 separate `self.capability_data` calls to 1 cached lookup
- Method signatures optimized to accept pre-fetched values (`value`, `unit`)
- ~66% reduction in property access overhead during sensor creation

### Online Status Detection
- **Fast path optimization**: Early return when `attributes` is not a list
- **Single string operations**: Lowercase conversion done once per attribute ID
- **Optimized comparisons**: Direct equality checks instead of `in` operator for status values
- **Helper method extraction**: `_check_last_seen_status()` reduces code duplication
- **Early continue**: Skip non-dict attributes immediately to reduce unnecessary processing

### Code Quality
- All code passes ruff linting checks
- No unused imports or dead code
- Maintains backward compatibility with existing functionality

<!-- MANUAL ADDITIONS START -->
API documentation link https://data-api.tibber.com/docs/
API specifications https://data-api.tibber.com/openapi/v1.json
When creating a new release: update changelog and documentation. Create a git commit and git tag, finally create GitHub release.
<!-- MANUAL ADDITIONS END -->