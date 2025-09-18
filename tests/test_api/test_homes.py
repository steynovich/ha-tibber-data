"""Test GET /v1/homes endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestHomesContract:
    """Test GET /v1/homes endpoint contract."""

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
    async def test_successful_homes_list(self, client, mock_session):
        """Test successful homes list retrieval."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": [
                {
                    "id": "12345678-1234-1234-1234-123456789012",
                    "displayName": "My Home",
                    "address": {
                        "street": "123 Main St",
                        "city": "Oslo",
                        "postalCode": "0150",
                        "country": "NO"
                    },
                    "timeZone": "Europe/Oslo",
                    "deviceCount": 3
                },
                {
                    "id": "87654321-4321-4321-4321-210987654321",
                    "displayName": "Summer House",
                    "address": {
                        "street": "456 Lake Rd",
                        "city": "Bergen",
                        "postalCode": "5020",
                        "country": "NO"
                    },
                    "timeZone": "Europe/Oslo",
                    "deviceCount": 1
                }
            ]
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Get homes
        homes = await client.get_homes()

        # Verify contract compliance
        assert len(homes) == 2

        home1 = homes[0]
        assert home1["id"] == "12345678-1234-1234-1234-123456789012"
        assert home1["displayName"] == "My Home"
        assert home1["timeZone"] == "Europe/Oslo"
        assert home1["deviceCount"] == 3
        assert "address" in home1

        # Verify correct request was made
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "/v1/homes" in call_args[0][0]

        # Check authorization header
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test_access_token"

    @pytest.mark.asyncio
    async def test_unauthorized_request(self, client, mock_session):
        """Test handling of unauthorized request."""
        # Mock 401 response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            "error": "unauthorized",
            "message": "Invalid or expired token"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid or expired token"):
            await client.get_homes()

    @pytest.mark.asyncio
    async def test_insufficient_permissions(self, client, mock_session):
        """Test handling of insufficient permissions."""
        # Mock 403 response
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.json = AsyncMock(return_value={
            "error": "forbidden",
            "message": "Insufficient permissions"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Insufficient permissions"):
            await client.get_homes()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, client, mock_session):
        """Test handling of rate limit exceeded."""
        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={
            "error": "rate_limit_exceeded",
            "message": "Rate limit exceeded"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Rate limit exceeded"):
            await client.get_homes()

    @pytest.mark.asyncio
    async def test_empty_homes_list(self, client, mock_session):
        """Test handling of empty homes list."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": []
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        homes = await client.get_homes()
        assert homes == []