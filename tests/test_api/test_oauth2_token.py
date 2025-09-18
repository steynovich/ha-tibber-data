"""Test OAuth2 token exchange endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestOAuth2TokenContract:
    """Test OAuth2 token exchange endpoint contract."""

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
    async def test_successful_token_exchange(self, client, mock_session):
        """Test successful OAuth2 token exchange."""
        # Mock successful token response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "access_token": "test_access_token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": "test_refresh_token",
            "scope": "USER HOME"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        # Exchange authorization code for token
        token_response = await client.exchange_code_for_token(
            client_id="test_client_id",
            code="test_authorization_code",
            redirect_uri="https://example.com/callback",
            code_verifier="test_code_verifier"
        )

        # Verify contract compliance
        assert token_response["access_token"] == "test_access_token"
        assert token_response["token_type"] == "Bearer"
        assert token_response["expires_in"] == 3600
        assert token_response["refresh_token"] == "test_refresh_token"
        assert token_response["scope"] == "USER HOME"

        # Verify correct request was made
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert "/oauth2/token" in call_args[0][0]

        # Check request data
        request_data = call_args[1]["data"]
        assert request_data["grant_type"] == "authorization_code"
        assert request_data["code"] == "test_authorization_code"
        assert request_data["client_id"] == "test_client_id"
        assert request_data["code_verifier"] == "test_code_verifier"

    @pytest.mark.asyncio
    async def test_invalid_authorization_code(self, client, mock_session):
        """Test handling of invalid authorization code."""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={
            "error": "invalid_grant",
            "error_description": "Invalid authorization code"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Invalid authorization code"):
            await client.exchange_code_for_token(
                client_id="test_client_id",
                code="invalid_code",
                redirect_uri="https://example.com/callback",
                code_verifier="test_code_verifier"
            )

    @pytest.mark.asyncio
    async def test_invalid_client_credentials(self, client, mock_session):
        """Test handling of invalid client credentials."""
        # Mock authentication error
        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={
            "error": "invalid_client",
            "error_description": "Client authentication failed"
        })
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with pytest.raises(ValueError, match="Client authentication failed"):
            await client.exchange_code_for_token(
                client_id="invalid_client_id",
                code="test_code",
                redirect_uri="https://example.com/callback",
                code_verifier="test_code_verifier"
            )

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, client):
        """Test validation of required parameters."""
        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.exchange_code_for_token(
                client_id="",  # Missing client_id
                code="test_code",
                redirect_uri="https://example.com/callback",
                code_verifier="test_code_verifier"
            )

        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.exchange_code_for_token(
                client_id="test_client_id",
                code="",  # Missing code
                redirect_uri="https://example.com/callback",
                code_verifier="test_code_verifier"
            )

        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.exchange_code_for_token(
                client_id="test_client_id",
                code="test_code",
                redirect_uri="https://example.com/callback",
                code_verifier=""  # Missing code_verifier (PKCE required)
            )