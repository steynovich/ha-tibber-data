"""Test configuration for Tibber Data integration."""
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    return MockConfigEntry(
        domain="tibber_data",
        data={
            "client_id": "test_client_id",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": 1234567890,
        },
        unique_id="test_user_id",
    )


@pytest.fixture
async def mock_tibber_data_setup(hass: HomeAssistant, mock_config_entry):
    """Set up the Tibber Data integration for testing."""
    mock_config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, "tibber_data", {})
    await hass.async_block_till_done()
    return mock_config_entry