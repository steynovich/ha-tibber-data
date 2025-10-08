"""Test Tibber Data diagnostics."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tibber_data.const import (
    DATA_COORDINATOR,
    DATA_DEVICES,
    DATA_HOMES,
    DOMAIN,
)
from custom_components.tibber_data.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with test data."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.update_interval.total_seconds.return_value = 60.0
    coordinator.data = {
        DATA_HOMES: {
            "home123": {
                "id": "home123",
                "displayName": "Test Home",
                "timeZone": "Europe/Stockholm",
                "address": {
                    "street": "Test Street 123",
                    "city": "Stockholm",
                    "postalCode": "12345",
                },
                "deviceCount": 1,
            }
        },
        DATA_DEVICES: {
            "device456": {
                "id": "device456",
                "name": "Test Device",
                "homeId": "home123",
                "manufacturer": "Test Manufacturer",
                "model": "Test Model",
                "firmwareVersion": "1.0.0",
                "vinNumber": "SECRET_VIN_123",
                "serialNumber": "SECRET_SERIAL_456",
                "capabilities": [
                    {
                        "name": "storage.stateOfCharge",
                        "displayName": "State of Charge",
                        "value": 95.5,
                        "unit": "%",
                        "lastUpdated": "2025-10-08T12:00:00Z",
                    }
                ],
                "attributes": [
                    {
                        "name": "isOnline",
                        "displayName": "Is Online",
                        "value": True,
                        "dataType": "BOOLEAN",
                        "lastUpdated": "2025-10-08T12:00:00Z",
                        "isDiagnostic": False,
                    }
                ],
            }
        },
    }
    return coordinator


@pytest.fixture
def mock_config_entry_with_coordinator(hass: HomeAssistant, mock_coordinator):
    """Create a mock config entry with coordinator data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "auth_implementation": "tibber_data",
            "token": {
                "access_token": "SECRET_ACCESS_TOKEN",
                "refresh_token": "SECRET_REFRESH_TOKEN",
                "expires_at": 1234567890,
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        },
        unique_id="test_user_id",
    )
    entry.add_to_hass(hass)

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: mock_coordinator,
    }

    return entry


async def test_config_entry_diagnostics(
    hass: HomeAssistant, mock_config_entry_with_coordinator, mock_coordinator
):
    """Test config entry diagnostics."""
    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_config_entry_with_coordinator
    )

    # Check basic structure
    assert "config_entry" in diagnostics
    assert "coordinator" in diagnostics
    assert "api_data" in diagnostics

    # Check config entry data
    assert diagnostics["config_entry"]["entry_id"] == mock_config_entry_with_coordinator.entry_id
    assert diagnostics["config_entry"]["domain"] == DOMAIN
    assert diagnostics["config_entry"]["version"] == mock_config_entry_with_coordinator.version

    # Check coordinator data
    assert diagnostics["coordinator"]["last_update_success"] is True
    assert diagnostics["coordinator"]["update_interval"] == 60.0

    # Check API data is present
    assert diagnostics["api_data"] is not None
    assert DATA_HOMES in diagnostics["api_data"]
    assert DATA_DEVICES in diagnostics["api_data"]


async def test_config_entry_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant, mock_config_entry_with_coordinator
):
    """Test that sensitive data is redacted from config entry diagnostics."""
    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_config_entry_with_coordinator
    )

    # Check that token data is redacted (whole token object should be redacted)
    # async_redact_data may redact the entire token dict, so just check it's not the original
    token_data = diagnostics["config_entry"]["data"].get("token")
    # Token should be redacted - either the whole thing or individual fields
    assert token_data == "**REDACTED**" or (
        isinstance(token_data, dict) and
        token_data.get("access_token") == "**REDACTED**"
    )

    # Check that VIN and serial numbers are redacted from API data
    device_data = diagnostics["api_data"][DATA_DEVICES]["device456"]
    assert device_data["vinNumber"] == "**REDACTED**"
    assert device_data["serialNumber"] == "**REDACTED**"

    # Check that address data is redacted
    home_data = diagnostics["api_data"][DATA_HOMES]["home123"]
    assert home_data["address"] == "**REDACTED**"


async def test_config_entry_diagnostics_no_data(
    hass: HomeAssistant, mock_config_entry_with_coordinator, mock_coordinator
):
    """Test config entry diagnostics when coordinator has no data."""
    mock_coordinator.data = None

    diagnostics = await async_get_config_entry_diagnostics(
        hass, mock_config_entry_with_coordinator
    )

    assert diagnostics["api_data"] is None


async def test_device_diagnostics(
    hass: HomeAssistant, mock_config_entry_with_coordinator, mock_coordinator
):
    """Test device diagnostics."""
    # Create a mock device entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry_with_coordinator.entry_id,
        identifiers={(DOMAIN, "device456")},
        name="Test Device",
        manufacturer="Test Manufacturer",
        model="Test Model",
        sw_version="1.0.0",
    )

    diagnostics = await async_get_device_diagnostics(
        hass, mock_config_entry_with_coordinator, device_entry
    )

    # Check basic structure
    assert "device" in diagnostics
    assert "device_data" in diagnostics

    # Check device info
    assert diagnostics["device"]["name"] == "Test Device"
    assert diagnostics["device"]["manufacturer"] == "Test Manufacturer"
    assert diagnostics["device"]["model"] == "Test Model"
    assert diagnostics["device"]["sw_version"] == "1.0.0"

    # Check device data is present
    assert diagnostics["device_data"] is not None
    assert diagnostics["device_data"]["id"] == "device456"
    assert diagnostics["device_data"]["name"] == "Test Device"
    assert "capabilities" in diagnostics["device_data"]
    assert "attributes" in diagnostics["device_data"]


async def test_device_diagnostics_redacts_sensitive_data(
    hass: HomeAssistant, mock_config_entry_with_coordinator
):
    """Test that sensitive data is redacted from device diagnostics."""
    # Create a mock device entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry_with_coordinator.entry_id,
        identifiers={(DOMAIN, "device456")},
        name="Test Device",
        manufacturer="Test Manufacturer",
        model="Test Model",
        sw_version="1.0.0",
    )

    diagnostics = await async_get_device_diagnostics(
        hass, mock_config_entry_with_coordinator, device_entry
    )

    # Check that VIN and serial numbers are redacted
    assert diagnostics["device_data"]["vinNumber"] == "**REDACTED**"
    assert diagnostics["device_data"]["serialNumber"] == "**REDACTED**"


async def test_device_diagnostics_device_not_found(
    hass: HomeAssistant, mock_config_entry_with_coordinator
):
    """Test device diagnostics when device is not found in coordinator data."""
    # Create a mock device entry with a non-existent device ID
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry_with_coordinator.entry_id,
        identifiers={(DOMAIN, "nonexistent_device")},
        name="Nonexistent Device",
        manufacturer="Test Manufacturer",
        model="Test Model",
    )

    diagnostics = await async_get_device_diagnostics(
        hass, mock_config_entry_with_coordinator, device_entry
    )

    # Check that device_data is None
    assert diagnostics["device_data"] is None


async def test_device_diagnostics_no_coordinator_data(
    hass: HomeAssistant, mock_config_entry_with_coordinator, mock_coordinator
):
    """Test device diagnostics when coordinator has no data."""
    mock_coordinator.data = None

    # Create a mock device entry
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry_with_coordinator.entry_id,
        identifiers={(DOMAIN, "device456")},
        name="Test Device",
        manufacturer="Test Manufacturer",
        model="Test Model",
    )

    diagnostics = await async_get_device_diagnostics(
        hass, mock_config_entry_with_coordinator, device_entry
    )

    # Check that device_data is None
    assert diagnostics["device_data"] is None
