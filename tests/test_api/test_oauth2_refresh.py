"""Test OAuth2 token refresh endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestOAuth2RefreshContract:
    """Test OAuth2 token refresh endpoint contract."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp client session."""
        session = AsyncMock()
        session.post = AsyncMock()
        return session

    @pytest.fixture
    def client(self, mock_session):
        """Create TibberDataClient with mocked session."""
        return TibberDataClient(session=mock_session)

    @pytest.mark.asyncio
    async def test_successful_token_refresh(self, client, mock_session):
        """Test successful OAuth2 token refresh."""
        # Mock successful refresh response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "new_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "new_refresh_token",
            "scope": "USER HOME"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        # Refresh token
        token_response = await client.refresh_access_token(
            client_id="test_client_id",
            refresh_token="test_refresh_token"
        )

        # Verify contract compliance
        assert token_response["access_token"] == "new_access_token"
        assert token_response["token_type"] == "Bearer"
        assert token_response["expires_in"] == 3600
        assert token_response["refresh_token"] == "new_refresh_token"
        assert token_response["scope"] == "USER HOME"

        # Verify correct request was made
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/oauth2/refresh" in call_args[0][0]

        # Check request data
        request_data = call_args[1]["data"]
        assert request_data["grant_type"] == "refresh_token"
        assert request_data["refresh_token"] == "test_refresh_token"
        assert request_data["client_id"] == "test_client_id"

    @pytest.mark.asyncio
    async def test_invalid_refresh_token(self, client, mock_session):
        """Test handling of invalid refresh token."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            "error": "invalid_grant",
            "error_description": "Invalid refresh token"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid refresh token"):
            await client.refresh_access_token(
                client_id="test_client_id",
                refresh_token="invalid_refresh_token"
            )

    @pytest.mark.asyncio
    async def test_expired_refresh_token(self, client, mock_session):
        """Test handling of expired refresh token."""
        # Mock error response for expired token
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            "error": "invalid_grant",
            "error_description": "Refresh token expired"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Refresh token expired"):
            await client.refresh_access_token(
                client_id="test_client_id",
                refresh_token="expired_refresh_token"
            )

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, client):
        """Test validation of required parameters."""
        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.refresh_access_token(
                client_id="",  # Missing client_id
                refresh_token="test_refresh_token"
            )

        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.refresh_access_token(
                client_id="test_client_id",
                refresh_token=""  # Missing refresh_token
            )

    @pytest.mark.asyncio
    async def test_automatic_token_refresh_trigger(self, client):
        """Test that token refresh is triggered before expiry."""
        # This test verifies the client handles token expiry automatically
        current_time = 1234567890
        token_expires_at = current_time + 300  # Expires in 5 minutes

        # Should trigger refresh when token expires within threshold (e.g., 10 minutes)
        should_refresh = client.should_refresh_token(
            expires_at=token_expires_at,
            current_time=current_time,
            threshold_seconds=600  # 10 minutes
        )

        assert should_refresh is True

        # Should not refresh when token has plenty of time left
        token_expires_at = current_time + 1800  # Expires in 30 minutes
        should_refresh = client.should_refresh_token(
            expires_at=token_expires_at,
            current_time=current_time,
            threshold_seconds=600  # 10 minutes
        )

        assert should_refresh is False