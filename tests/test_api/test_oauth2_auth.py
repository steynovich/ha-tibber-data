"""Test OAuth2 authorization endpoint contract."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from custom_components.tibber_data.api.client import TibberDataClient


class TestOAuth2AuthContract:
    """Test OAuth2 authorization endpoint contract."""

    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp client session."""
        session = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.fixture
    def client(self, mock_session):
        """Create TibberDataClient with mocked session."""
        return TibberDataClient(session=mock_session)

    @pytest.mark.asyncio
    async def test_authorization_url_generation(self, client):
        """Test OAuth2 authorization URL generation follows contract."""
        client_id = "test_client_id"
        redirect_uri = "https://example.com/callback"
        state = "test_state"
        code_challenge = "test_challenge"

        auth_url = await client.get_authorization_url(
            client_id=client_id,
            redirect_uri=redirect_uri,
            state=state,
            code_challenge=code_challenge,
            scopes=["USER", "HOME"]
        )

        # Should generate proper authorization URL
        from urllib.parse import urlparse, parse_qs

        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)

        assert "data-api.tibber.com/oauth2/authorize" in auth_url
        assert query_params["client_id"][0] == client_id
        assert query_params["redirect_uri"][0] == redirect_uri
        assert query_params["state"][0] == state
        assert query_params["code_challenge"][0] == code_challenge
        assert query_params["response_type"][0] == "code"
        assert query_params["code_challenge_method"][0] == "S256"
        assert query_params["scope"][0] == "USER HOME"

    @pytest.mark.asyncio
    async def test_authorization_endpoint_validation(self, client, mock_session):
        """Test authorization endpoint validates required parameters."""
        # Mock response for authorization endpoint validation
        mock_response = MagicMock()
        mock_response.status = 400
        mock_response.json = AsyncMock(return_value={
            "error": "invalid_request",
            "error_description": "Missing required parameter: client_id"
        })
        mock_session.get.return_value.__aenter__.return_value = mock_response

        # Should handle missing required parameters
        with pytest.raises(ValueError, match="Missing required parameter"):
            await client.validate_authorization_request(
                client_id="",  # Empty client_id should fail
                redirect_uri="https://example.com/callback",
                code_challenge="test_challenge"
            )

    @pytest.mark.asyncio
    async def test_pkce_support_required(self, client):
        """Test that PKCE (code_challenge) is required."""
        with pytest.raises(ValueError, match="PKCE code challenge is required"):
            await client.get_authorization_url(
                client_id="test_client",
                redirect_uri="https://example.com/callback",
                state="test_state",
                code_challenge="",  # Empty challenge should fail
                scopes=["USER"]
            )

    @pytest.mark.asyncio
    async def test_valid_scopes_required(self, client):
        """Test that valid scopes are required."""
        with pytest.raises(ValueError, match="Invalid scope"):
            await client.get_authorization_url(
                client_id="test_client",
                redirect_uri="https://example.com/callback",
                state="test_state",
                code_challenge="test_challenge",
                scopes=["INVALID_SCOPE"]  # Invalid scope should fail
            )