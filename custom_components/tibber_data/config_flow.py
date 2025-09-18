"""OAuth2 configuration flow for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import voluptuous as vol

from .api.client import TibberDataClient
from .const import (
    DOMAIN,
    CONF_CLIENT_ID,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_EXPIRES_AT,
    CONF_TOKEN_TYPE,
    CONF_SCOPES,
    ERROR_MESSAGES
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_CLIENT_ID): str,
})


class TibberDataFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle OAuth2 configuration flow for Tibber Data."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.client_id: Optional[str] = None
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        self.state: Optional[str] = None
        self.redirect_uri: Optional[str] = None
        self._client: Optional[TibberDataClient] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate client ID format
                client_id = user_input[CONF_CLIENT_ID].strip()
                if len(client_id) < 10:
                    errors["base"] = "invalid_client"
                else:
                    self.client_id = client_id
                    return await self.async_step_pick_implementation()

            except Exception:
                _LOGGER.exception("Unexpected error validating user input")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "docs_url": "https://developer.tibber.com/",
                "client_setup_info": "Contact Tibber support to register your OAuth2 client application"
            }
        )

    async def async_step_pick_implementation(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle picking OAuth2 implementation."""
        if user_input is not None:
            # For now, we only have one implementation
            return await self.async_step_auth()

        implementations = {
            "tibber_data": "Tibber Data API"
        }

        return self.async_show_form(
            step_id="pick_implementation",
            data_schema=vol.Schema({
                vol.Required("implementation", default="tibber_data"): vol.In(implementations)
            }),
            description_placeholders={
                "implementation_name": "Tibber Data API"
            }
        )

    async def async_step_auth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the OAuth2 authorization step."""
        try:
            return await self._async_create_oauth_url()
        except Exception as err:
            _LOGGER.exception("Error creating OAuth URL: %s", err)
            return self.async_abort(reason="oauth_error")

    async def _async_create_oauth_url(self) -> FlowResult:
        """Create OAuth2 authorization URL."""
        if not self.client_id:
            return self.async_abort(reason="missing_client_id")

        # Initialize client
        session = async_get_clientsession(self.hass)
        self._client = TibberDataClient(client_id=self.client_id, session=session)

        # Generate PKCE challenge
        self.code_verifier, self.code_challenge = self._client.generate_pkce_challenge()

        # Generate state for CSRF protection
        import secrets
        self.state = secrets.token_urlsafe(32)

        # Set up redirect URI
        self.redirect_uri = f"{self.hass.config.external_url}/auth/tibber_data/callback"

        # Create authorization URL
        auth_url = await self._client.get_authorization_url(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            state=self.state,
            code_challenge=self.code_challenge,
            scopes=["USER", "HOME"]
        )

        return self.async_external_step(
            step_id="auth",
            url=auth_url
        )

    async def async_step_code(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the OAuth2 callback with authorization code."""
        if user_input is None:
            return self.async_abort(reason="missing_code")

        errors: Dict[str, str] = {}

        try:
            # Validate state parameter (CSRF protection)
            received_state = user_input.get("state")
            if received_state != self.state:
                return self.async_show_form(
                    step_id="code",
                    errors={"base": "csrf"}
                )

            # Extract authorization code
            code = user_input.get("code")
            if not code:
                return self.async_show_form(
                    step_id="code",
                    errors={"base": "invalid_auth"}
                )

            # Exchange code for tokens
            token_response = await self._client.exchange_code_for_token(
                client_id=self.client_id,
                code=code,
                redirect_uri=self.redirect_uri,
                code_verifier=self.code_verifier
            )

            # Get user information
            self._client._access_token = token_response["access_token"]
            user_info = await self._client.get_user_info()

            # Check for existing entry with same user
            user_id = user_info.get("user_id", user_info.get("id"))
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()

            # Create config entry
            entry_data = {
                CONF_CLIENT_ID: self.client_id,
                CONF_ACCESS_TOKEN: token_response["access_token"],
                CONF_REFRESH_TOKEN: token_response["refresh_token"],
                CONF_TOKEN_TYPE: token_response.get("token_type", "Bearer"),
                CONF_EXPIRES_AT: int(
                    self.hass.loop.time() + token_response.get("expires_in", 3600)
                ),
                CONF_SCOPES: token_response.get("scope", "USER HOME").split(),
                "user_id": user_id,
                "user_email": user_info.get("email"),
            }

            return self.async_create_entry(
                title=user_info.get("name", f"Tibber User {user_id}"),
                data=entry_data
            )

        except ValueError as err:
            error_str = str(err).lower()
            if "invalid authorization code" in error_str:
                errors["base"] = "invalid_auth"
            elif "client authentication failed" in error_str:
                errors["base"] = "invalid_client"
            else:
                _LOGGER.error("OAuth2 token exchange failed: %s", err)
                errors["base"] = "invalid_auth"

        except Exception as err:
            _LOGGER.exception("Unexpected error during OAuth2 flow: %s", err)
            if "timeout" in str(err).lower() or "cannot connect" in str(err).lower():
                errors["base"] = "cannot_connect"
            else:
                errors["base"] = "unknown"

        # Show form with errors
        return self.async_show_form(
            step_id="code",
            errors=errors
        )

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> FlowResult:
        """Handle reauthentication."""
        self.client_id = entry_data.get(CONF_CLIENT_ID)

        if not self.client_id:
            return self.async_abort(reason="missing_client_id")

        self.context["title_placeholders"] = {"name": self.hass.config_entries.async_get_entry(self.context["entry_id"]).title}
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Initialize client
                session = async_get_clientsession(self.hass)
                self._client = TibberDataClient(client_id=self.client_id, session=session)

                # Try to refresh token first
                entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
                if entry:
                    refresh_token = entry.data.get(CONF_REFRESH_TOKEN)
                    if refresh_token:
                        token_response = await self._client.refresh_access_token(
                            client_id=self.client_id,
                            refresh_token=refresh_token
                        )

                        # Update entry data
                        new_data = dict(entry.data)
                        new_data[CONF_ACCESS_TOKEN] = token_response["access_token"]
                        new_data[CONF_REFRESH_TOKEN] = token_response.get("refresh_token", refresh_token)
                        new_data[CONF_EXPIRES_AT] = int(
                            self.hass.loop.time() + token_response.get("expires_in", 3600)
                        )

                        self.hass.config_entries.async_update_entry(
                            entry,
                            data=new_data
                        )

                        return self.async_abort(reason="reauth_successful")

            except Exception as err:
                _LOGGER.error("Token refresh failed during reauth: %s", err)
                # If refresh fails, proceed with full OAuth flow
                return await self.async_step_auth()

        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            description_placeholders={
                "account": self.hass.config_entries.async_get_entry(self.context["entry_id"]).title
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tibber Data."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "update_interval",
                    default=self.config_entry.options.get("update_interval", 60)
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=900)),
                vol.Optional(
                    "include_offline_devices",
                    default=self.config_entry.options.get("include_offline_devices", True)
                ): bool,
            })
        )


class TibberDataAuthCallbackView(HomeAssistantView):
    """Handle OAuth2 callback."""

    url = "/auth/tibber_data/callback"
    name = "auth:tibber_data:callback"
    requires_auth = False

    async def get(self, request):
        """Handle GET request for OAuth2 callback."""
        hass = request.app["hass"]
        query_params = dict(request.query)

        # Find the config flow by matching state
        state = query_params.get("state")
        code = query_params.get("code")
        error = query_params.get("error")

        if error:
            _LOGGER.error("OAuth2 callback received error: %s", error)
            # Could redirect to an error page or close the window
            return self._redirect_with_error(error)

        if not state or not code:
            _LOGGER.error("OAuth2 callback missing required parameters")
            return self._redirect_with_error("missing_parameters")

        # Continue the flow with the authorization code
        # This would typically involve finding the right config flow instance
        # and calling the appropriate step

        return self._redirect_with_success(code, state)

    def _redirect_with_error(self, error: str) -> str:
        """Return HTML page with error."""
        return f"""
        <html>
        <head><title>Authorization Failed</title></head>
        <body>
            <h1>Authorization Failed</h1>
            <p>Error: {error}</p>
            <script>window.close();</script>
        </body>
        </html>
        """

    def _redirect_with_success(self, code: str, state: str) -> str:
        """Return HTML page with success."""
        return f"""
        <html>
        <head><title>Authorization Successful</title></head>
        <body>
            <h1>Authorization Successful</h1>
            <p>Please return to Home Assistant to complete setup.</p>
            <script>
                window.opener.postMessage({{
                    type: 'oauth_callback',
                    code: '{code}',
                    state: '{state}'
                }}, '*');
                window.close();
            </script>
        </body>
        </html>
        """