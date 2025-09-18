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

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->