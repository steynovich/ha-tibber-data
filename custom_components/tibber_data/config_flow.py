"""OAuth2 configuration flow for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.components.application_credentials import (
    AuthImplementation,
    AuthorizationServer,
    async_import_client_credential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import TibberDataClient
from .const import DOMAIN, OAUTH2_AUTHORIZE_URL, OAUTH2_TOKEN_URL

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Tibber Data OAuth2 authentication."""

    DOMAIN = DOMAIN
    VERSION = 1

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> Dict[str, Any]:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "scope": "USER HOME",
        }

    async def async_step_reauth(self, entry_data: Dict[str, Any]) -> ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Confirm reauth dialog."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")

        return await self.async_step_user()

    async def async_oauth_create_entry(self, data: Dict[str, Any]) -> ConfigFlowResult:
        """Create an entry for Tibber Data."""
        session = async_get_clientsession(self.hass)
        client = TibberDataClient(session=session)

        # Set up the client with the OAuth token
        client._access_token = data["access_token"]

        try:
            # Get user information to set unique_id and title
            user_info = await client.get_user_info()
            user_id = user_info.get("user_id", user_info.get("id", "unknown"))

            # Check for existing entry
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()

            # Create the entry
            return self.async_create_entry(
                title=user_info.get("name", f"Tibber User {user_id}"),
                data={
                    **data,
                    "user_id": user_id,
                    "user_email": user_info.get("email"),
                },
            )

        except Exception as err:
            _LOGGER.error("Error creating entry: %s", err)
            return self.async_abort(reason="cannot_connect")

        finally:
            await client.close()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Tibber Data."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        import voluptuous as vol

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


async def async_get_config_flow_impl(
    hass: HomeAssistant,
    auth_implementation: AuthImplementation,
) -> config_entry_oauth2_flow.AbstractOAuth2FlowHandler:
    """Return a Tibber Data OAuth2 flow handler."""
    return OAuth2FlowHandler()


# For backwards compatibility and manual setup
class TibberDataFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle manual configuration flow for Tibber Data."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Start OAuth2 flow - parent class will handle implementation selection
        return await super().async_step_user(user_input)

    async def async_step_pick_implementation(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> ConfigFlowResult:
        """Handle picking OAuth2 implementation."""
        # The parent OAuth2 flow handler will handle this automatically
        return self.async_create_entry(
            title="Tibber Data",
            data={"auth_implementation": DOMAIN},
        )