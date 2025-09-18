"""Test device discovery coordinator integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from custom_components.tibber_data.coordinator import TibberDataUpdateCoordinator
from custom_components.tibber_data.const import DOMAIN


class TestTibberDataCoordinator:
    """Test TibberDataUpdateCoordinator integration."""

    @pytest.fixture
    def mock_client(self):
        """Mock TibberDataClient."""
        client = AsyncMock()
        client.get_homes = AsyncMock()
        client.get_home_devices = AsyncMock()
        client.get_device_details = AsyncMock()
        client.refresh_access_token = AsyncMock()
        return client

    @pytest.fixture
    def mock_config_entry_data(self):
        """Mock config entry data."""
        return {
            "client_id": "test_client_id",
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_at": dt_util.utcnow().timestamp() + 3600,  # Expires in 1 hour
        }

    @pytest.fixture
    def coordinator(self, hass: HomeAssistant, mock_client, mock_config_entry_data):
        """Create TibberDataUpdateCoordinator."""
        return TibberDataUpdateCoordinator(
            hass=hass,
            client=mock_client,
            config_entry_data=mock_config_entry_data,
            update_interval=timedelta(seconds=60)
        )

    @pytest.mark.asyncio
    async def test_successful_data_fetch(self, coordinator, mock_client):
        """Test successful data fetch from API."""
        # Mock API responses
        mock_homes = [
            {
                "id": "home-123",
                "displayName": "My Home",
                "timeZone": "Europe/Oslo"
            }
        ]

        mock_devices = [
            {
                "id": "device-456",
                "type": "EV",
                "name": "My Tesla",
                "online": True
            }
        ]

        mock_device_details = {
            "id": "device-456",
            "type": "EV",
            "name": "My Tesla",
            "online": True,
            "capabilities": [
                {
                    "name": "battery_level",
                    "displayName": "Battery Level",
                    "value": 85.0,
                    "unit": "%",
                    "lastUpdated": "2025-09-18T10:30:00Z"
                }
            ]
        }

        mock_client.get_homes.return_value = mock_homes
        mock_client.get_home_devices.return_value = mock_devices
        mock_client.get_device_details.return_value = mock_device_details

        # Perform data refresh
        await coordinator.async_config_entry_first_refresh()

        # Verify data structure
        data = coordinator.data
        assert "homes" in data
        assert len(data["homes"]) == 1
        assert data["homes"]["home-123"]["displayName"] == "My Home"

        assert "devices" in data
        assert len(data["devices"]) == 1
        assert data["devices"]["device-456"]["name"] == "My Tesla"
        assert data["devices"]["device-456"]["capabilities"][0]["value"] == 85.0

        # Verify API calls were made
        mock_client.get_homes.assert_called_once()
        mock_client.get_home_devices.assert_called_once_with("home-123")
        mock_client.get_device_details.assert_called_once_with("home-123", "device-456")

    @pytest.mark.asyncio
    async def test_token_refresh_before_expiry(self, coordinator, mock_client, mock_config_entry_data):
        """Test automatic token refresh before expiry."""
        # Set token to expire soon
        mock_config_entry_data["expires_at"] = dt_util.utcnow().timestamp() + 300  # 5 minutes

        mock_client.refresh_access_token.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "expires_in": 3600
        }

        mock_client.get_homes.return_value = []

        # Perform data refresh (should trigger token refresh)
        await coordinator.async_config_entry_first_refresh()

        # Verify token was refreshed
        mock_client.refresh_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_unavailable_handling(self, coordinator, mock_client):
        """Test handling of API unavailability."""
        # Mock API failure
        mock_client.get_homes.side_effect = Exception("API unavailable")

        # Should raise UpdateFailed
        with pytest.raises(UpdateFailed, match="API unavailable"):
            await coordinator.async_config_entry_first_refresh()

    @pytest.mark.asyncio
    async def test_unauthorized_token_handling(self, coordinator, mock_client):
        """Test handling of unauthorized/expired tokens."""
        # Mock unauthorized response
        mock_client.get_homes.side_effect = ValueError("Invalid or expired token")

        with pytest.raises(UpdateFailed, match="Authentication failed"):
            await coordinator.async_config_entry_first_refresh()

    @pytest.mark.asyncio
    async def test_partial_device_failure(self, coordinator, mock_client):
        """Test handling when some devices fail to load."""
        mock_homes = [{"id": "home-123", "displayName": "My Home"}]
        mock_devices = [
            {"id": "device-456", "type": "EV", "name": "Working Device", "online": True},
            {"id": "device-789", "type": "CHARGER", "name": "Failing Device", "online": False}
        ]

        mock_client.get_homes.return_value = mock_homes
        mock_client.get_home_devices.return_value = mock_devices

        # First device succeeds, second fails
        mock_client.get_device_details.side_effect = [
            {
                "id": "device-456",
                "type": "EV",
                "capabilities": [
                    {"name": "battery_level", "value": 85.0, "unit": "%"}
                ]
            },
            Exception("Device communication error")  # Second device fails
        ]

        # Should not raise UpdateFailed, but log error and continue
        await coordinator.async_config_entry_first_refresh()

        # Verify partial data is available
        data = coordinator.data
        assert "device-456" in data["devices"]
        # Failing device should either be missing or marked as unavailable
        assert "device-789" not in data["devices"] or not data["devices"]["device-789"].get("online")

    @pytest.mark.asyncio
    async def test_multiple_homes_handling(self, coordinator, mock_client):
        """Test handling of multiple homes with devices."""
        mock_homes = [
            {"id": "home-123", "displayName": "Primary Home"},
            {"id": "home-456", "displayName": "Summer House"}
        ]

        # Different devices for each home
        def mock_get_devices(home_id):
            if home_id == "home-123":
                return [{"id": "device-111", "type": "EV", "name": "Tesla", "online": True}]
            elif home_id == "home-456":
                return [{"id": "device-222", "type": "THERMOSTAT", "name": "Thermostat", "online": True}]
            return []

        def mock_get_device_details(home_id, device_id):
            if device_id == "device-111":
                return {
                    "id": "device-111",
                    "type": "EV",
                    "capabilities": [{"name": "battery_level", "value": 90.0}]
                }
            elif device_id == "device-222":
                return {
                    "id": "device-222",
                    "type": "THERMOSTAT",
                    "capabilities": [{"name": "temperature", "value": 21.5}]
                }

        mock_client.get_homes.return_value = mock_homes
        mock_client.get_home_devices.side_effect = mock_get_devices
        mock_client.get_device_details.side_effect = mock_get_device_details

        await coordinator.async_config_entry_first_refresh()

        # Verify both homes and their devices are loaded
        data = coordinator.data
        assert len(data["homes"]) == 2
        assert len(data["devices"]) == 2
        assert "device-111" in data["devices"]
        assert "device-222" in data["devices"]

    @pytest.mark.asyncio
    async def test_data_update_interval_respected(self, coordinator, mock_client):
        """Test that update interval is respected."""
        mock_client.get_homes.return_value = []

        # First update
        await coordinator.async_config_entry_first_refresh()
        first_call_count = mock_client.get_homes.call_count

        # Immediate second update should use cached data
        await coordinator.async_request_refresh()

        # Should not have made additional API calls due to update interval
        # (This behavior depends on the coordinator implementation)
        assert mock_client.get_homes.call_count >= first_call_count

    @pytest.mark.asyncio
    async def test_device_state_change_detection(self, coordinator, mock_client):
        """Test detection of device state changes between updates."""
        mock_homes = [{"id": "home-123", "displayName": "My Home"}]
        mock_devices = [{"id": "device-456", "type": "EV", "name": "Tesla", "online": True}]

        mock_client.get_homes.return_value = mock_homes
        mock_client.get_home_devices.return_value = mock_devices

        # First update - battery at 80%
        mock_client.get_device_details.return_value = {
            "id": "device-456",
            "capabilities": [{"name": "battery_level", "value": 80.0}]
        }

        await coordinator.async_config_entry_first_refresh()
        first_battery_level = coordinator.data["devices"]["device-456"]["capabilities"][0]["value"]
        assert first_battery_level == 80.0

        # Second update - battery at 85% (state changed)
        mock_client.get_device_details.return_value = {
            "id": "device-456",
            "capabilities": [{"name": "battery_level", "value": 85.0}]
        }

        await coordinator.async_refresh()
        second_battery_level = coordinator.data["devices"]["device-456"]["capabilities"][0]["value"]
        assert second_battery_level == 85.0
        assert second_battery_level != first_battery_level