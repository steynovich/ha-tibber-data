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

## EV Support Features

### Sensor Types
The integration supports both numeric and string-valued sensors for EVs and other devices:

**Numeric Sensors:**
- `storage.stateOfCharge` - Battery state of charge (%)
- `storage.targetStateOfCharge` - Target charge level (%)
- `range.remaining` - Estimated range (automatically converted from meters to km)

**ENUM Sensors (string-valued):**
- `connector.status` - Vehicle plug status ("Connected", "Disconnected", "Unknown")
- `charging.status` - Charging status ("Idle", "Charging", "Complete", "Error", "Unknown")
- String values are automatically formatted with title case for better display

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

## Performance Optimizations

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
<!-- MANUAL ADDITIONS END -->