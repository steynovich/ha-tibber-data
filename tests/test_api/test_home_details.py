"""Test GET /v1/homes/{homeId} endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestHomeDetailsContract:
    """Test GET /v1/homes/{homeId} endpoint contract."""

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
    async def test_successful_home_details(self, client, mock_session):
        """Test successful home details retrieval."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {
                "id": home_id,
                "displayName": "My Home",
                "address": {
                    "street": "123 Main St",
                    "city": "Oslo",
                    "postalCode": "0150",
                    "country": "NO"
                },
                "timeZone": "Europe/Oslo",
                "deviceCount": 3
            }
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Get home details
        home = await client.get_home_details(home_id)

        # Verify contract compliance
        assert home["id"] == home_id
        assert home["displayName"] == "My Home"
        assert home["timeZone"] == "Europe/Oslo"
        assert home["deviceCount"] == 3
        assert "address" in home
        assert home["address"]["city"] == "Oslo"

        # Verify correct request was made
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert f"/v1/homes/{home_id}" in call_args[0][0]

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
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Home not found"):
            await client.get_home_details(home_id)

    @pytest.mark.asyncio
    async def test_invalid_home_id_format(self, client):
        """Test validation of home ID format."""
        invalid_home_id = "invalid-uuid-format"

        with pytest.raises(ValueError, match="Invalid home ID format"):
            await client.get_home_details(invalid_home_id)

    @pytest.mark.asyncio
    async def test_unauthorized_home_access(self, client, mock_session):
        """Test handling of unauthorized home access."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock 403 response (user doesn't have access to this home)
        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.json = AsyncMock(return_value={
            "error": "forbidden",
            "message": "Access denied to home"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Access denied to home"):
            await client.get_home_details(home_id)

    @pytest.mark.asyncio
    async def test_required_fields_present(self, client, mock_session):
        """Test that all required fields are present in response."""
        home_id = "12345678-1234-1234-1234-123456789012"

        # Mock response with minimal required fields
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {
                "id": home_id,
                "displayName": "Minimal Home",
                "timeZone": "Europe/Oslo"
                # address and deviceCount are optional
            }
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        home = await client.get_home_details(home_id)

        # Required fields must be present
        assert "id" in home
        assert "displayName" in home
        assert "timeZone" in home

        # Optional fields may be missing
        assert home.get("address") is None
        assert home.get("deviceCount") is None