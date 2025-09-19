"""Test GET /v1/homes/{homeId}/devices/{deviceId} endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestDeviceDetailsContract:
    """Test GET /v1/homes/{homeId}/devices/{deviceId} endpoint contract."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp client session."""
        from unittest.mock import AsyncMock

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

        # Mock successful response - according to OpenAPI spec, device details are returned directly
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": device_id,
            "externalId": "ext_device_001",
            "info": {
                "name": "My Tesla",
                "brand": "Tesla",
                "model": "Model 3"
            },
            "status": {
                "lastSeen": "2025-09-18T10:30:00Z"
            },
            "identity": {
                "id": device_id,
                "externalId": "ext_device_001",
                "name": "My Tesla",
                "manufacturer": "Tesla",
                "model": "Model 3"
            },
            "attributes": [
                {
                    "id": "connectivity.online",
                    "value": True,
                    "$type": "BooleanAttribute"
                },
                {
                    "id": "connectivity.signalStrength",
                    "value": 85,
                    "$type": "IntegerAttribute"
                },
                {
                    "id": "firmware.version",
                    "value": "2025.4.1",
                    "$type": "StringAttribute"
                },
                {
                    "id": "firmware.updateAvailable",
                    "value": False,
                    "$type": "BooleanAttribute"
                }
            ],
            "capabilities": [
                {
                    "id": "battery_level",
                    "description": "Battery Level",
                    "value": 87.5,
                    "unit": "%",
                    "$type": "FloatingPointCapability"
                },
                {
                    "id": "charging_power",
                    "description": "Charging Power",
                    "value": 11.2,
                    "unit": "kW",
                    "$type": "FloatingPointCapability"
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        # Get device details
        device = await client.get_device_details(home_id, device_id)

        # Verify contract compliance
        assert device["id"] == device_id
        assert device["info"]["brand"] == "Tesla"
        assert device["info"]["name"] == "My Tesla"
        assert "identity" in device
        assert "attributes" in device
        assert "capabilities" in device
        assert len(device["capabilities"]) == 2

        # Verify capabilities structure
        battery_capability = device["capabilities"][0]
        assert battery_capability["id"] == "battery_level"
        assert battery_capability["value"] == 87.5
        assert battery_capability["unit"] == "%"

    @pytest.mark.asyncio
    async def test_device_not_found(self, client, mock_session):
        """Test handling of non-existent device."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "nonexistent-device"

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

        # Mock response with capability validation
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": device_id,
            "externalId": "ext_device_001",
            "info": {
                "name": "Living Room Thermostat",
                "brand": "Nest",
                "model": "Learning Thermostat"
            },
            "status": {
                "lastSeen": "2025-09-18T10:30:00Z"
            },
            "capabilities": [
                {
                    "id": "temperature",
                    "description": "Temperature",
                    "value": 22.5,
                    "unit": "°C",
                    "$type": "FloatingPointCapability"
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        device = await client.get_device_details(home_id, device_id)

        # Verify capabilities have required fields according to actual API structure
        capability = device["capabilities"][0]
        assert "id" in capability
        assert "description" in capability
        assert "value" in capability
        assert "unit" in capability

    @pytest.mark.asyncio
    async def test_different_capability_value_types(self, client, mock_session):
        """Test that capabilities can have different value types."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock response with different value types
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "id": device_id,
            "externalId": "ext_device_001",
            "info": {
                "name": "Garage Charger",
                "brand": "Easee",
                "model": "Home"
            },
            "status": {
                "lastSeen": "2025-09-18T10:30:00Z"
            },
            "capabilities": [
                {
                    "id": "power",
                    "description": "Charging Power",
                    "value": 1250.5,  # number
                    "unit": "W",
                    "$type": "FloatingPointCapability"
                },
                {
                    "id": "online",
                    "description": "Online Status",
                    "value": True,  # boolean
                    "unit": "",
                    "$type": "IntegerCapability"
                },
                {
                    "id": "status",
                    "description": "Charging Status",
                    "value": "charging",  # string
                    "availableValues": ["idle", "charging", "error"],
                    "$type": "EnumCapability"
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        device = await client.get_device_details(home_id, device_id)

        capabilities = {cap["id"]: cap["value"] for cap in device["capabilities"]}
        assert isinstance(capabilities["power"], float)  # number
        assert isinstance(capabilities["online"], bool)  # boolean
        assert isinstance(capabilities["status"], str)   # string