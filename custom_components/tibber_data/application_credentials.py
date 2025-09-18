"""Application credentials platform for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, OAUTH2_AUTHORIZE_URL, OAUTH2_TOKEN_URL

_LOGGER = logging.getLogger(__name__)


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server configuration for Tibber Data."""
    return AuthorizationServer(
        authorize_url=OAUTH2_AUTHORIZE_URL,
        token_url=OAUTH2_TOKEN_URL,
    )


async def async_get_description_placeholders(hass: HomeAssistant) -> Dict[str, str]:
    """Return description placeholders for OAuth2 setup."""
    return {
        "oauth_consent_url": "https://developer.tibber.com/",
        "more_info_url": "https://developer.tibber.com/docs/guides/calling-api",
        "developer_console_url": "https://developer.tibber.com/",
    }


def validate_client_credential(client_credential: ClientCredential) -> None:
    """Validate client credential."""
    if not client_credential.client_id:
        raise ValueError("Client ID is required")

    if len(client_credential.client_id) < 10:
        raise ValueError("Client ID appears to be invalid (too short)")

    # Note: Tibber uses public OAuth2 clients (no client secret required)
    # This is common for integrations that use PKCE for security
    _LOGGER.debug("Validated Tibber Data OAuth2 client credential")