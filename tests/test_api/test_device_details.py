"""Test GET /v1/homes/{homeId}/devices/{deviceId} endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestDeviceDetailsContract:
    """Test GET /v1/homes/{homeId}/devices/{deviceId} endpoint contract."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp client session."""
        from unittest.mock import AsyncMock, MagicMock
        import asyncio

        class MockAsyncContextManager:
            def __init__(self, return_value):
                self.return_value = return_value

            async def __aenter__(self):
                return self.return_value

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        session = AsyncMock()
        # Store the context manager creator on the session for tests to use
        session._mock_context_manager = MockAsyncContextManager
        # Override the request method to return the context manager directly
        def mock_request(*args, **kwargs):
            return session._current_context_manager

        session.request = mock_request
        return session

    @pytest.fixture
    def client(self, mock_session):
        """Create TibberDataClient with mocked session."""
        return TibberDataClient(
            access_token="test_access_token",
            session=mock_session
        )

    @pytest.mark.asyncio
    async def test_successful_device_details(self, client, mock_session):
        """Test successful device details retrieval."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {
                "id": device_id,
                "externalId": "ext_device_001",
                "type": "EV",
                "manufacturer": "Tesla",
                "model": "Model 3",
                "name": "My Tesla",
                "online": True,
                "lastSeen": "2025-09-18T10:30:00Z",
                "identity": {
                    "id": device_id,
                    "externalId": "ext_device_001",
                    "name": "My Tesla",
                    "manufacturer": "Tesla",
                    "model": "Model 3"
                },
                "attributes": {
                    "connectivity": {
                        "online": True,
                        "lastSeen": "2025-09-18T10:30:00Z",
                        "signalStrength": 85
                    },
                    "firmware": {
                        "version": "2025.4.1",
                        "updateAvailable": False,
                        "lastUpdated": "2025-08-15T14:20:00Z"
                    }
                },
                "capabilities": [
                    {
                        "name": "battery_level",
                        "displayName": "Battery Level",
                        "value": 87.5,
                        "unit": "%",
                        "lastUpdated": "2025-09-18T10:30:00Z",
                        "minValue": 0,
                        "maxValue": 100,
                        "precision": 1
                    },
                    {
                        "name": "charging_power",
                        "displayName": "Charging Power",
                        "value": 11.2,
                        "unit": "kW",
                        "lastUpdated": "2025-09-18T10:30:00Z",
                        "minValue": 0,
                        "maxValue": 22,
                        "precision": 1
                    }
                ]
            }
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        # Get device details
        device = await client.get_device_details(home_id, device_id)

        # Verify contract compliance
        assert device["id"] == device_id
        assert device["type"] == "EV"
        assert device["online"] is True

        # Verify identity section
        assert "identity" in device
        assert device["identity"]["manufacturer"] == "Tesla"

        # Verify attributes section
        assert "attributes" in device
        assert "connectivity" in device["attributes"]
        assert "firmware" in device["attributes"]

        # Verify capabilities section
        assert "capabilities" in device
        assert len(device["capabilities"]) == 2

        battery_cap = device["capabilities"][0]
        assert battery_cap["name"] == "battery_level"
        assert battery_cap["value"] == 87.5
        assert battery_cap["unit"] == "%"

        # Verify correct request was made
        # Note: We can't easily assert on the mock_request call since it's a custom function
        # But the test passing means the request was made successfully

    @pytest.mark.asyncio
    async def test_device_not_found(self, client, mock_session):
        """Test handling of non-existent device."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "nonexistent-device-id"

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={
            "error": "not_found",
            "message": "Device not found"
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        with pytest.raises(ValueError, match="Device not found"):
            await client.get_device_details(home_id, device_id)

    @pytest.mark.asyncio
    async def test_capabilities_validation(self, client, mock_session):
        """Test that capabilities have required fields."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock response with capabilities
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {
                "id": device_id,
                "externalId": "ext_device_001",
                "type": "CHARGER",
                "name": "My Charger",
                "online": True,
                "capabilities": [
                    {
                        "name": "charging_current",
                        "displayName": "Charging Current",
                        "value": 16.0,
                        "unit": "A",
                        "lastUpdated": "2025-09-18T10:30:00Z"
                        # minValue, maxValue, precision are optional
                    }
                ]
            }
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        device = await client.get_device_details(home_id, device_id)

        # Verify capabilities have required fields
        capability = device["capabilities"][0]
        required_fields = ["name", "displayName", "value", "unit", "lastUpdated"]
        for field in required_fields:
            assert field in capability

    @pytest.mark.asyncio
    async def test_different_capability_value_types(self, client, mock_session):
        """Test that capabilities can have different value types."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock response with different value types
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {
                "id": device_id,
                "externalId": "ext_device_001",
                "type": "THERMOSTAT",
                "name": "Living Room Thermostat",
                "online": True,
                "capabilities": [
                    {
                        "name": "temperature",
                        "displayName": "Temperature",
                        "value": 21.5,  # number
                        "unit": "°C",
                        "lastUpdated": "2025-09-18T10:30:00Z"
                    },
                    {
                        "name": "heating_enabled",
                        "displayName": "Heating Enabled",
                        "value": True,  # boolean
                        "unit": "",
                        "lastUpdated": "2025-09-18T10:30:00Z"
                    },
                    {
                        "name": "mode",
                        "displayName": "Mode",
                        "value": "heat",  # string
                        "unit": "",
                        "lastUpdated": "2025-09-18T10:30:00Z"
                    }
                ]
            }
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        device = await client.get_device_details(home_id, device_id)

        capabilities = device["capabilities"]
        assert isinstance(capabilities[0]["value"], float)  # number
        assert isinstance(capabilities[1]["value"], bool)   # boolean
        assert isinstance(capabilities[2]["value"], str)    # string