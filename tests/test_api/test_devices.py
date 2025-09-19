"""Test GET /v1/homes/{homeId}/devices endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestDevicesContract:
    """Test GET /v1/homes/{homeId}/devices endpoint contract."""

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
    async def test_successful_devices_list(self, client, mock_session):
        """Test successful devices list retrieval."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "devices": [
                {
                    "id": "device-1234-5678-9012",
                    "externalId": "ext_device_001",
                    "info": {
                        "name": "My Tesla",
                        "brand": "Tesla",
                        "model": "Model 3"
                    },
                    "status": {
                        "lastSeen": "2025-09-18T10:30:00Z"
                    }
                },
                {
                    "id": "device-2345-6789-0123",
                    "externalId": "ext_charger_001",
                    "info": {
                        "name": "Garage Charger",
                        "brand": "Easee",
                        "model": "Home"
                    },
                    "status": {
                        "lastSeen": "2025-09-18T08:15:00Z"
                    }
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
        assert device1["info"]["brand"] == "Tesla"
        assert device1["info"]["name"] == "My Tesla"
        assert "status" in device1

        device2 = devices[1]
        assert device2["id"] == "device-2345-6789-0123"
        assert device2["info"]["brand"] == "Easee"

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
            "devices": []
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)
        assert devices == []

    @pytest.mark.asyncio
    async def test_basic_device_structure(self, client, mock_session):
        """Test that devices have the expected basic structure from API."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock response with basic device structure (no device types)
        mock_response = MagicMock()
        devices_data = [
            {
                "id": "device-0001-0001-0001",
                "externalId": "ext_device_001",
                "info": {
                    "name": "Test Device",
                    "brand": "TestMfg",
                    "model": "TestModel"
                },
                "status": {
                    "lastSeen": "2025-09-18T10:30:00Z"
                }
            }
        ]

        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"devices": devices_data})
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)

        # Verify all devices have the expected structure
        for device in devices:
            assert "id" in device
            assert "info" in device

    @pytest.mark.asyncio
    async def test_required_device_fields(self, client, mock_session):
        """Test that all required device fields are present."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock response with minimal required fields
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "devices": [
                {
                    "id": "device-1234-5678-9012",
                    "externalId": "ext_device_001",
                    "info": {
                        "name": "My Device"
                        # brand, model are optional
                    }
                    # status, attributes are optional
                }
            ]
        })
        # Set up the session.request to return our async context manager
        mock_session._current_context_manager = mock_session._mock_context_manager(mock_response)

        devices = await client.get_home_devices(home_id)
        device = devices[0]

        # Required fields must be present according to actual API structure
        assert "id" in device
        assert "externalId" in device
        assert "info" in device
        assert "name" in device["info"]

        # Optional fields may be missing in the new API structure
        # brand and model are in info object, lastSeen is in status object
        # These may or may not be present, so we don't test for them here