"""OAuth2 configuration flow for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api.client import TibberDataClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)



class TibberDataFlowHandler(
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
            "scope": "openid profile email offline_access data-api-user-read data-api-homes-read data-api-vehicles-read data-api-chargers-read data-api-thermostats-read data-api-energy-systems-read data-api-inverters-read",
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
        _LOGGER.debug("Creating OAuth entry with data keys: %s", list(data.keys()))
        session = async_get_clientsession(self.hass)
        client = TibberDataClient(session=session)

        # Set up the client with the OAuth token
        # Home Assistant passes token data in nested structure
        token_data = data.get("token", {})
        access_token = token_data.get("access_token")

        if not access_token:
            _LOGGER.error("No access token found in OAuth data: %s", data.keys())
            raise Exception("No access token received from OAuth flow")

        client.set_access_token(access_token)
        _LOGGER.debug("Successfully extracted access token from OAuth data")

        try:
            # Get homes to validate token and create unique identifier
            # Since there's no /v1/user endpoint, we'll use homes to identify the user
            _LOGGER.debug("Attempting to fetch homes from Tibber Data API")
            homes_data = await client.get_homes()
            _LOGGER.debug("API response: found %d homes", len(homes_data) if homes_data else 0)

            if not homes_data:
                # Log more details for debugging
                _LOGGER.warning("No homes found in API response. This could mean:")
                _LOGGER.warning("1. Your Tibber account has no homes configured")
                _LOGGER.warning("2. The OAuth scopes don't include homes access")
                _LOGGER.warning("3. The API endpoint or permissions have changed")
                raise Exception(
                    "No homes found with Tibber Data API access. Please ensure:\n"
                    "1. You have homes configured in your Tibber account\n"
                    "2. You have devices connected through Tibber (EVs, chargers, etc.)\n"
                    "3. Your account has access to the Tibber Data API\n"
                    "4. The OAuth scopes include 'data-api-homes-read'"
                )

            # Create a unique identifier based on the homes (user-specific)
            home_ids = [home.get("id", "") for home in homes_data]
            user_id = "_".join(sorted(home_ids))[:50] if home_ids else "unknown"

            # Check for existing entry - but allow updates during reauth
            await self.async_set_unique_id(user_id)

            # If this is a reauth flow, update the existing entry instead of creating a new one
            if self.source == config_entries.SOURCE_REAUTH:
                # Find the existing entry to update
                existing_entry = None
                for entry in self._async_current_entries():
                    if entry.unique_id == user_id:
                        existing_entry = entry
                        break

                if existing_entry:
                    _LOGGER.info("Updating existing entry during reauth")
                    self.hass.config_entries.async_update_entry(existing_entry, data=data)
                    await self.hass.config_entries.async_reload(existing_entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

            # For normal flow, abort if already configured
            self._abort_if_unique_id_configured()

            # Create a descriptive title
            if len(homes_data) == 1:
                title = f"Tibber Data - {homes_data[0].get('displayName', 'Home')}"
            else:
                title = f"Tibber Data - {len(homes_data)} homes"

            # Create the entry
            return self.async_create_entry(
                title=title,
                data={
                    **data,
                    "user_id": user_id,
                    "homes_count": len(homes_data),
                },
            )

        except ValueError as err:
            # This catches API errors from our client
            _LOGGER.error("API error during entry creation: %s", err)
            if "Invalid or expired token" in str(err):
                return self.async_abort(reason="invalid_auth")
            elif "Insufficient permissions" in str(err):
                return self.async_abort(reason="insufficient_permissions")
            else:
                return self.async_abort(reason="cannot_connect")
        except Exception as err:
            _LOGGER.error("Unexpected error creating entry: %s", err)
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


