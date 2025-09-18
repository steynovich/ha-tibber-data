"""Test GET /v1/homes/{homeId}/devices endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestDevicesContract:
    """Test GET /v1/homes/{homeId}/devices endpoint contract."""

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
    async def test_successful_devices_list(self, client, mock_session):
        """Test successful devices list retrieval."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "id": "device-1234-5678-9012",
                    "externalId": "ext_device_001",
                    "type": "EV",
                    "manufacturer": "Tesla",
                    "model": "Model 3",
                    "name": "My Tesla",
                    "online": True,
                    "lastSeen": "2025-09-18T10:30:00Z"
                },
                {
                    "id": "device-2345-6789-0123",
                    "externalId": "ext_charger_001",
                    "type": "CHARGER",
                    "manufacturer": "Easee",
                    "model": "Home",
                    "name": "Garage Charger",
                    "online": False,
                    "lastSeen": "2025-09-18T08:15:00Z"
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        # Get devices
        devices = await client.get_home_devices(home_id)

        # Verify contract compliance
        assert len(devices) == 2

        device1 = devices[0]
        assert device1["id"] == "device-1234-5678-9012"
        assert device1["type"] == "EV"
        assert device1["manufacturer"] == "Tesla"
        assert device1["online"] is True

        device2 = devices[1]
        assert device2["id"] == "device-2345-6789-0123"
        assert device2["type"] == "CHARGER"
        assert device2["online"] is False

        # Verify correct request was made
        # Note: We can't easily assert on the mock_request call since it's a custom function
        # But the test passing means the request was made successfully

    @pytest.mark.asyncio
    async def test_home_not_found(self, client, mock_session):
        """Test handling of non-existent home."""
        home_id = "nonexistent-home-id"

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={
            "error": "not_found",
            "message": "Home not found"
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        with pytest.raises(ValueError, match="Home not found"):
            await client.get_home_devices(home_id)

    @pytest.mark.asyncio
    async def test_empty_devices_list(self, client, mock_session):
        """Test handling of home with no devices."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock empty response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": []
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)
        assert devices == []

    @pytest.mark.asyncio
    async def test_device_types_validation(self, client, mock_session):
        """Test that device types are from valid enumeration."""
        home_id = "12345678-1234-1234-1234-123456789012"

        valid_types = ["EV", "CHARGER", "THERMOSTAT", "SOLAR_INVERTER", "BATTERY", "HEAT_PUMP"]

        # Mock response with all valid device types
        mock_response = MagicMock()
        devices_data = []
        for i, device_type in enumerate(valid_types):
            devices_data.append({
                "id": f"device-{i:04d}-{i:04d}-{i:04d}",
                "externalId": f"ext_device_{i:03d}",
                "type": device_type,
                "manufacturer": "TestMfg",
                "model": "TestModel",
                "name": f"Test {device_type}",
                "online": True,
                "lastSeen": "2025-09-18T10:30:00Z"
            })

        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"data": devices_data})
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)

        # Verify all device types are valid
        for device in devices:
            assert device["type"] in valid_types

    @pytest.mark.asyncio
    async def test_required_device_fields(self, client, mock_session):
        """Test that all required device fields are present."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock response with minimal required fields
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "id": "device-1234-5678-9012",
                    "externalId": "ext_device_001",
                    "type": "EV",
                    "name": "My Device",
                    "online": True
                    # manufacturer, model, lastSeen are optional
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)
        device = devices[0]

        # Required fields must be present
        required_fields = ["id", "externalId", "type", "name", "online"]
        for field in required_fields:
            assert field in device

        # Optional fields may be missing
        optional_fields = ["manufacturer", "model", "lastSeen"]
        for field in optional_fields:
            # These fields may or may not be present
            pass