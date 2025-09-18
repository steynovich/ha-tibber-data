"""Test GET /v1/homes/{homeId}/devices/{deviceId}/history endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestDeviceHistoryContract:
    """Test GET /v1/homes/{homeId}/devices/{deviceId}/history endpoint contract."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp client session."""
        session = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.fixture
    def client(self, mock_session):
        """Create TibberDataClient with mocked session."""
        return TibberDataClient(
            access_token="test_access_token",
            session=mock_session
        )

    @pytest.mark.asyncio
    async def test_successful_device_history(self, client, mock_session):
        """Test successful device history retrieval."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "timestamp": "2025-09-18T08:00:00Z",
                    "capabilities": {
                        "battery_level": 75.0,
                        "charging_power": 0.0,
                        "temperature": 22.5
                    }
                },
                {
                    "timestamp": "2025-09-18T09:00:00Z",
                    "capabilities": {
                        "battery_level": 82.5,
                        "charging_power": 11.2,
                        "temperature": 23.1
                    }
                },
                {
                    "timestamp": "2025-09-18T10:00:00Z",
                    "capabilities": {
                        "battery_level": 87.5,
                        "charging_power": 11.0,
                        "temperature": 23.8
                    }
                }
            ]
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Get device history
        history = await client.get_device_history(
            home_id=home_id,
            device_id=device_id,
            from_time="2025-09-18T08:00:00Z",
            to_time="2025-09-18T10:00:00Z",
            resolution="HOURLY"
        )

        # Verify contract compliance
        assert len(history) == 3

        entry1 = history[0]
        assert entry1["timestamp"] == "2025-09-18T08:00:00Z"
        assert "capabilities" in entry1
        assert entry1["capabilities"]["battery_level"] == 75.0
        assert entry1["capabilities"]["charging_power"] == 0.0

        # Verify correct request was made
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert f"/v1/homes/{home_id}/devices/{device_id}/history" in call_args[0][0]

        # Check query parameters
        params = call_args[1]["params"]
        assert params["from"] == "2025-09-18T08:00:00Z"
        assert params["to"] == "2025-09-18T10:00:00Z"
        assert params["resolution"] == "HOURLY"

    @pytest.mark.asyncio
    async def test_daily_resolution_history(self, client, mock_session):
        """Test device history with daily resolution."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock daily resolution response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "timestamp": "2025-09-17T00:00:00Z",
                    "capabilities": {
                        "energy_consumed": 45.8,
                        "avg_temperature": 21.2
                    }
                },
                {
                    "timestamp": "2025-09-18T00:00:00Z",
                    "capabilities": {
                        "energy_consumed": 52.3,
                        "avg_temperature": 22.1
                    }
                }
            ]
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        history = await client.get_device_history(
            home_id=home_id,
            device_id=device_id,
            from_time="2025-09-17T00:00:00Z",
            to_time="2025-09-18T23:59:59Z",
            resolution="DAILY"
        )

        assert len(history) == 2

        # Verify query parameters
        call_args = mock_session.get.call_args
        params = call_args[1]["params"]
        assert params["resolution"] == "DAILY"

    @pytest.mark.asyncio
    async def test_empty_history(self, client, mock_session):
        """Test handling of empty history."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock empty response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": []
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        history = await client.get_device_history(
            home_id=home_id,
            device_id=device_id,
            from_time="2025-09-18T00:00:00Z",
            to_time="2025-09-18T01:00:00Z",
            resolution="HOURLY"
        )

        assert history == []

    @pytest.mark.asyncio
    async def test_device_not_found_for_history(self, client, mock_session):
        """Test handling of non-existent device for history."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "nonexistent-device"

        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status = 404
        mock_response.json = AsyncMock(return_value={
            "error": "not_found",
            "message": "Device not found"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Device not found"):
            await client.get_device_history(
                home_id=home_id,
                device_id=device_id,
                from_time="2025-09-18T00:00:00Z",
                to_time="2025-09-18T01:00:00Z",
                resolution="HOURLY"
            )

    @pytest.mark.asyncio
    async def test_history_parameter_validation(self, client):
        """Test validation of history request parameters."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Test invalid resolution
        with pytest.raises(ValueError, match="Invalid resolution"):
            await client.get_device_history(
                home_id=home_id,
                device_id=device_id,
                from_time="2025-09-18T00:00:00Z",
                to_time="2025-09-18T01:00:00Z",
                resolution="INVALID"
            )

        # Test from_time after to_time
        with pytest.raises(ValueError, match="from_time must be before to_time"):
            await client.get_device_history(
                home_id=home_id,
                device_id=device_id,
                from_time="2025-09-18T10:00:00Z",
                to_time="2025-09-18T08:00:00Z",
                resolution="HOURLY"
            )

    @pytest.mark.asyncio
    async def test_different_capability_value_types_in_history(self, client, mock_session):
        """Test that history capabilities can have different value types."""
        home_id = "12345678-1234-1234-1234-123456789012"
        device_id = "device-1234-5678-9012"

        # Mock response with different value types
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "timestamp": "2025-09-18T10:00:00Z",
                    "capabilities": {
                        "power": 1250.5,      # number
                        "online": True,       # boolean
                        "status": "charging"  # string
                    }
                }
            ]
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        history = await client.get_device_history(
            home_id=home_id,
            device_id=device_id,
            from_time="2025-09-18T10:00:00Z",
            to_time="2025-09-18T10:00:00Z",
            resolution="HOURLY"
        )

        capabilities = history[0]["capabilities"]
        assert isinstance(capabilities["power"], float)    # number
        assert isinstance(capabilities["online"], bool)    # boolean
        assert isinstance(capabilities["status"], str)     # string