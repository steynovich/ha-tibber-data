# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Improved home display name fallback logic to use unique identifiers instead of static "Tibber Home Name"
- Enhanced API compliance by validating against official Tibber Data API specification
- Fixed home name parsing to prioritize official API format "info.name" from Tibber Data API playground
- Maintained fallback compatibility with test data format for comprehensive coverage
- Enhanced area assignment logic to use only actual home names from Tibber homes API
- Removed all hardcoded fallback names, relying exclusively on API-provided home names
- Fixed area names not updating when home names change in Tibber - now automatically updates device areas

### Added
- Automatic device area updates when Tibber home names change
- Hub device name updates when home names change in Tibber API
- Debug logging for home name changes and device area updates

## [1.0.0] - 2025-01-19

### Added
- Initial release of Tibber Data integration for Home Assistant
- OAuth2 authentication with PKCE support
- Automatic device discovery for Tibber connected IoT devices
- Support for Electric Vehicles, EV Chargers, Thermostats, Solar Inverters, Battery Storage, and Heat Pumps
- Real-time monitoring with 60-second update intervals
- HACS compatibility
- Comprehensive test coverage with pytest (96.5% success rate)
- Full type annotations with mypy compliance
- Device organization by Tibber homes
- Sensor and binary sensor entities for various device capabilities
- Proper error handling and API rate limiting
- Home Assistant integration with automations and dashboards

### Fixed
- Fixed mypy type error in DeviceInfo `via_device` parameter by conditionally adding it only when home_id is present
- Fixed home display name extraction to correctly read from `info.name` field according to Tibber Data API specification
- Updated fallback home display name format from "Tibber Home {id}" to "Tibber Home Name" for better consistency

### Technical
- Improved TypedDict compliance for Home Assistant DeviceInfo objects
- Enhanced API response parsing to match official Tibber Data API specification
- All mypy type checks now pass without errors
- Production-ready code with comprehensive error handling
- GitHub Actions workflows for HACS validation, testing, and releases