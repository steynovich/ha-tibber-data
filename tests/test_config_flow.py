"""Test OAuth2 configuration flow integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from custom_components.tibber_data import config_flow
from custom_components.tibber_data.const import DOMAIN


class TestTibberDataConfigFlow:
    """Test OAuth2 configuration flow integration."""

    @pytest.fixture
    def mock_oauth_session(self):
        """Mock OAuth session for testing."""
        return {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "Bearer",
            "expires_at": 1234567890,
            "scopes": ["USER", "HOME"]
        }

    @pytest.fixture
    def mock_user_info(self):
        """Mock user info response."""
        return {
            "user_id": "test_user_123",
            "email": "test@example.com",
            "name": "Test User"
        }

    @pytest.mark.asyncio
    async def test_config_flow_init(self, hass: HomeAssistant):
        """Test configuration flow initialization."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP
        assert result["step_id"] == "pick_implementation"

    @pytest.mark.asyncio
    async def test_oauth_flow_start(self, hass: HomeAssistant):
        """Test OAuth flow start."""
        with patch(
            "custom_components.tibber_data.config_flow.TibberDataFlowHandler._async_create_oauth_url"
        ) as mock_create_url:
            mock_create_url.return_value = "https://data-api.tibber.com/oauth2/authorize?client_id=test"

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Select OAuth implementation
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"implementation": "tibber_data"}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP
            assert result["step_id"] == "auth"
            assert "https://data-api.tibber.com/oauth2/authorize" in result["url"]

    @pytest.mark.asyncio
    async def test_oauth_callback_success(self, hass: HomeAssistant, mock_oauth_session, mock_user_info):
        """Test successful OAuth callback handling."""
        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient.exchange_code_for_token"
        ) as mock_exchange, patch(
            "custom_components.tibber_data.api.client.TibberDataClient.get_user_info"
        ) as mock_get_user:

            mock_exchange.return_value = mock_oauth_session
            mock_get_user.return_value = mock_user_info

            # Start flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            # Select implementation
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"implementation": "tibber_data"}
            )

            # Simulate OAuth callback
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"code": "test_auth_code", "state": "test_state"}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
            assert result["title"] == "Test User"
            assert result["data"]["access_token"] == "test_access_token"
            assert result["data"]["refresh_token"] == "test_refresh_token"

    @pytest.mark.asyncio
    async def test_oauth_callback_invalid_code(self, hass: HomeAssistant):
        """Test OAuth callback with invalid authorization code."""
        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient.exchange_code_for_token"
        ) as mock_exchange:

            mock_exchange.side_effect = ValueError("Invalid authorization code")

            # Start flow and get to callback
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"implementation": "tibber_data"}
            )

            # Simulate OAuth callback with invalid code
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"code": "invalid_code", "state": "test_state"}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["errors"]["base"] == "invalid_auth"

    @pytest.mark.asyncio
    async def test_oauth_state_mismatch(self, hass: HomeAssistant):
        """Test OAuth callback with state mismatch (CSRF protection)."""
        # Start flow
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"implementation": "tibber_data"}
        )

        # Simulate OAuth callback with wrong state
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"code": "test_code", "state": "wrong_state"}
        )

        assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result["errors"]["base"] == "csrf"

    @pytest.mark.asyncio
    async def test_reauth_flow(self, hass: HomeAssistant, mock_config_entry, mock_oauth_session):
        """Test reauthentication flow for expired tokens."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient.refresh_access_token"
        ) as mock_refresh:

            mock_refresh.return_value = mock_oauth_session

            # Start reauth flow
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": config_entries.SOURCE_REAUTH,
                    "entry_id": mock_config_entry.entry_id,
                },
                data=mock_config_entry.data,
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_EXTERNAL_STEP
            assert result["step_id"] == "reauth_confirm"

            # Confirm reauth
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
            assert result["reason"] == "reauth_successful"

    @pytest.mark.asyncio
    async def test_duplicate_entry_prevention(self, hass: HomeAssistant, mock_config_entry, mock_oauth_session, mock_user_info):
        """Test prevention of duplicate entries for same user."""
        mock_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient.exchange_code_for_token"
        ) as mock_exchange, patch(
            "custom_components.tibber_data.api.client.TibberDataClient.get_user_info"
        ) as mock_get_user:

            mock_exchange.return_value = mock_oauth_session
            mock_get_user.return_value = mock_user_info

            # Try to create another entry for same user
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"implementation": "tibber_data"}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"code": "test_auth_code", "state": "test_state"}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
            assert result["reason"] == "already_configured"

    @pytest.mark.asyncio
    async def test_network_error_handling(self, hass: HomeAssistant):
        """Test handling of network errors during OAuth flow."""
        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient.exchange_code_for_token"
        ) as mock_exchange:

            mock_exchange.side_effect = Exception("Network error")

            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": config_entries.SOURCE_USER}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"implementation": "tibber_data"}
            )

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"code": "test_code", "state": "test_state"}
            )

            assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
            assert result["errors"]["base"] == "cannot_connect"