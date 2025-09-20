"""Data update coordinator for Tibber Data integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api.client import TibberDataClient
from .api.models import TibberOAuthSession, TibberDevice
from .const import (
    DOMAIN,
    DATA_HOMES,
    DATA_DEVICES,
    TOKEN_REFRESH_THRESHOLD,
    DEFAULT_UPDATE_INTERVAL,
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_EXPIRES_AT
)

_LOGGER = logging.getLogger(__name__)


class TibberDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching data from Tibber Data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TibberDataClient,
        config_entry: ConfigEntry,
        update_interval: Optional[timedelta] = None
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.config_entry: ConfigEntry = config_entry
        self._oauth_session: Optional[TibberOAuthSession] = None

        # Set up OAuth session from config entry data
        self._setup_oauth_session()

        # Use provided update interval or default
        interval = update_interval or DEFAULT_UPDATE_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=interval,
        )

    def _setup_oauth_session(self) -> None:
        """Set up OAuth session from config entry data."""
        try:
            # Home Assistant OAuth2 stores token data in nested structure under "token"
            token_data = self.config_entry.data.get("token", {})

            # Extract token information from Home Assistant OAuth2 structure
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
            expires_at = token_data.get("expires_at", 0)

            # Fallback to direct access for compatibility
            if not access_token:
                access_token = self.config_entry.data.get("access_token") or self.config_entry.data.get(CONF_ACCESS_TOKEN)
                refresh_token = self.config_entry.data.get("refresh_token") or self.config_entry.data.get(CONF_REFRESH_TOKEN)
                expires_at = self.config_entry.data.get("expires_at", 0) or self.config_entry.data.get(CONF_EXPIRES_AT, 0)

            if not access_token:
                raise ValueError("Missing OAuth2 access token in config entry")

            # Handle scopes from token data or use default with all device category scopes
            scopes = token_data.get("scope", "openid profile email offline_access data-api-user-read data-api-homes-read data-api-vehicles-read data-api-chargers-read data-api-thermostats-read data-api-energy-systems-read data-api-inverters-read")
            if isinstance(scopes, str):
                scopes = scopes.split()
            elif not scopes:
                scopes = ["openid", "profile", "email", "offline_access", "data-api-user-read", "data-api-homes-read", "data-api-vehicles-read", "data-api-chargers-read", "data-api-thermostats-read", "data-api-energy-systems-read", "data-api-inverters-read"]

            self._oauth_session = TibberOAuthSession(
                session_id=self.config_entry.entry_id,
                user_id=self.config_entry.unique_id or "unknown",
                access_token=access_token,
                refresh_token=refresh_token or "",  # Allow empty refresh token
                expires_at=expires_at,
                scopes=scopes
            )

            # Set the OAuth session in the client
            self.client.set_oauth_session(self._oauth_session)

        except Exception as err:
            _LOGGER.error("Failed to setup OAuth session: %s", err)
            raise UpdateFailed(f"Authentication setup failed: {err}") from err

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            # Ensure we have a valid access token before making API calls
            await self._ensure_valid_token()

            # Fetch homes and devices
            homes_data, devices_data = await self.client.get_homes_with_devices()

            # Convert to the format expected by entities
            homes = {}
            for home in homes_data:
                homes[home.home_id] = {
                    "id": home.home_id,
                    "displayName": home.display_name,
                    "timeZone": home.time_zone,
                    "address": home.address,
                    "deviceCount": home.device_count
                }

            devices = {}
            for device in devices_data:
                # Skip devices with name "Dummy" (case-insensitive)
                device_name = device.name or ""
                if device_name.strip().lower() == "dummy":
                    _LOGGER.debug("Skipping dummy device: %s", device.device_id)
                    continue

                # Convert capabilities to the expected format
                capabilities = []
                for capability in device.capabilities:
                    cap_data: Dict[str, Any] = {
                        "name": capability.name,
                        "displayName": capability.display_name,
                        "value": capability.value,
                        "unit": capability.unit,
                        "lastUpdated": capability.last_updated.isoformat()
                    }
                    if capability.available_values is not None:
                        cap_data["availableValues"] = capability.available_values
                    capabilities.append(cap_data)

                # Convert attributes to the expected format
                attributes = []
                for attribute in device.attributes:
                    attr_dict = {
                        "name": attribute.name,
                        "displayName": attribute.display_name,
                        "value": attribute.value,
                        "dataType": attribute.data_type,
                        "lastUpdated": attribute.last_updated.isoformat(),
                        "isDiagnostic": attribute.is_diagnostic
                    }

                    # Add any additional fields stored in the attribute
                    if hasattr(attribute, 'additional_fields') and attribute.additional_fields:
                        attr_dict.update(attribute.additional_fields)

                    attributes.append(attr_dict)

                devices[device.device_id] = {
                    "id": device.device_id,
                    "external_id": device.external_id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "home_id": device.home_id,
                    "online": device.online_status,
                    "lastSeen": device.last_seen.isoformat() if device.last_seen else None,
                    "capabilities": capabilities,
                    "attributes": attributes
                }

            _LOGGER.debug(
                "Fetched %d homes and %d devices from Tibber Data API",
                len(homes),
                len(devices)
            )

            # Update device areas if home names have changed
            await self._update_device_areas_if_needed(homes)

            return {
                DATA_HOMES: homes,
                DATA_DEVICES: devices
            }

        except Exception as err:
            # Log specific error types for better debugging
            if "401" in str(err) or "Invalid or expired token" in str(err) or "Unauthorized" in str(err):
                _LOGGER.error("Authentication failed - token may be expired: %s", err)
                # Try to refresh token one more time
                try:
                    await self._refresh_token()
                    # Retry the request once
                    return await self._async_update_data()
                except Exception as refresh_err:
                    _LOGGER.error("Token refresh failed: %s", refresh_err)
                    raise UpdateFailed("Authentication failed - please reconfigure") from refresh_err
            elif "Rate limit exceeded" in str(err):
                _LOGGER.warning("API rate limit exceeded, will retry later")
                raise UpdateFailed("Rate limit exceeded") from err
            elif "cannot connect" in str(err).lower() or "timeout" in str(err).lower():
                _LOGGER.warning("API connection failed: %s", err)
                raise UpdateFailed(f"API unavailable: {err}") from err
            else:
                _LOGGER.error("Unexpected error fetching data: %s", err)
                raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token."""
        if not self._oauth_session:
            raise UpdateFailed("No OAuth session available")

        # Check if token needs refresh
        current_time = int(dt_util.utcnow().timestamp())
        if self._oauth_session.expires_at > 0:
            time_until_expiry = self._oauth_session.expires_at - current_time
            if time_until_expiry <= TOKEN_REFRESH_THRESHOLD:
                _LOGGER.debug("Token expires in %d seconds, refreshing", time_until_expiry)
                await self._refresh_token()

    async def _refresh_token(self) -> None:
        """Refresh the OAuth access token."""
        if not self._oauth_session:
            raise UpdateFailed("No OAuth session available")

        try:
            # Get client_id from Home Assistant OAuth2 implementation
            client_id = None
            try:
                from homeassistant.helpers import config_entry_oauth2_flow

                # Get OAuth2 implementation from the config entry
                implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
                    self.hass, self.config_entry
                )
                if implementation and hasattr(implementation, 'client_id'):
                    client_id = getattr(implementation, 'client_id', None)
            except Exception as impl_err:
                _LOGGER.debug("Could not get client_id from OAuth2 implementation: %s", impl_err)

            if not client_id:
                # As a last resort, trigger a reauth flow
                _LOGGER.warning("Cannot refresh token - client ID not available, triggering reauth")
                self.hass.async_create_task(
                    self.hass.config_entries.flow.async_init(
                        DOMAIN,
                        context={"source": "reauth", "entry_id": self.config_entry.entry_id},
                        data=self.config_entry.data,
                    )
                )
                raise UpdateFailed("Authentication expired - please reauthorize in integrations")

            refresh_response = await self.client.refresh_access_token(
                client_id=client_id,
                refresh_token=self._oauth_session.refresh_token
            )

            # Update OAuth session with new tokens
            self._oauth_session.update_tokens(
                access_token=refresh_response["access_token"],
                refresh_token=refresh_response.get("refresh_token", self._oauth_session.refresh_token),
                expires_in=refresh_response["expires_in"],
                scopes=refresh_response.get("scope", "").split() if refresh_response.get("scope") else None
            )

            # Update config entry data (handle both formats)
            new_data = dict(self.config_entry.data)

            # Use the same keys that were in the original data
            if "access_token" in new_data:
                new_data["access_token"] = self._oauth_session.access_token
                new_data["refresh_token"] = self._oauth_session.refresh_token
                new_data["expires_at"] = self._oauth_session.expires_at
            else:
                new_data[CONF_ACCESS_TOKEN] = self._oauth_session.access_token
                new_data[CONF_REFRESH_TOKEN] = self._oauth_session.refresh_token
                new_data[CONF_EXPIRES_AT] = self._oauth_session.expires_at

            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=new_data
            )

            # Update client with new token
            self.client.set_oauth_session(self._oauth_session)

            _LOGGER.debug("Successfully refreshed OAuth token")

        except Exception as err:
            _LOGGER.error("Failed to refresh token: %s", err)
            raise UpdateFailed(f"Token refresh failed: {err}") from err

    async def async_get_device_data(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific device."""
        if not self.data or DATA_DEVICES not in self.data:
            return None
        device_data: Optional[Dict[str, Any]] = self.data[DATA_DEVICES].get(device_id)
        return device_data

    async def async_get_home_data(self, home_id: str) -> Optional[Dict[str, Any]]:
        """Get data for a specific home."""
        if not self.data or DATA_HOMES not in self.data:
            return None
        home_data: Optional[Dict[str, Any]] = self.data[DATA_HOMES].get(home_id)
        return home_data

    async def async_update_device(self, device_id: str) -> bool:
        """Update a specific device and return True if successful."""
        try:
            device_data = await self.async_get_device_data(device_id)
            if not device_data:
                _LOGGER.warning("Device %s not found in coordinator data", device_id)
                return False

            home_id = device_data["home_id"]

            # Fetch updated device details
            updated_device_data = await self.client.get_device_details(home_id, device_id)
            updated_device = TibberDevice.from_api_data(updated_device_data, home_id)

            # Skip devices with name "Dummy" (case-insensitive)
            device_name = updated_device.name or ""
            if device_name.strip().lower() == "dummy":
                _LOGGER.debug("Skipping update for dummy device: %s", device_id)
                return False

            # Update the device data in coordinator
            if self.data and DATA_DEVICES in self.data:
                # Convert device back to the expected format (same as _async_update_data)
                capabilities = []
                for capability in updated_device.capabilities:
                    cap_data: Dict[str, Any] = {
                        "name": capability.name,
                        "displayName": capability.display_name,
                        "value": capability.value,
                        "unit": capability.unit,
                        "lastUpdated": capability.last_updated.isoformat()
                    }
                    if capability.available_values is not None:
                        cap_data["availableValues"] = capability.available_values
                    capabilities.append(cap_data)

                attributes = []
                for attribute in updated_device.attributes:
                    attributes.append({
                        "name": attribute.name,
                        "displayName": attribute.display_name,
                        "value": attribute.value,
                        "dataType": attribute.data_type,
                        "lastUpdated": attribute.last_updated.isoformat(),
                        "isDiagnostic": attribute.is_diagnostic
                    })

                self.data[DATA_DEVICES][device_id] = {
                    "id": updated_device.device_id,
                    "external_id": updated_device.external_id,
                    "name": updated_device.name,
                    "manufacturer": updated_device.manufacturer,
                    "model": updated_device.model,
                    "home_id": updated_device.home_id,
                    "online": updated_device.online_status,
                    "lastSeen": updated_device.last_seen.isoformat() if updated_device.last_seen else None,
                    "capabilities": capabilities,
                    "attributes": attributes
                }

                # Notify listeners of the update
                self.async_update_listeners()

            return True

        except Exception as err:
            _LOGGER.error("Failed to update device %s: %s", device_id, err)
            return False

    def get_devices_by_type(self, device_type: str) -> List[Dict[str, Any]]:
        """Get all devices of a specific type."""
        if not self.data or DATA_DEVICES not in self.data:
            return []

        return [
            device for device in self.data[DATA_DEVICES].values()
            if device.get("type") == device_type
        ]

    def get_online_devices(self) -> List[Dict[str, Any]]:
        """Get all online devices."""
        if not self.data or DATA_DEVICES not in self.data:
            return []

        return [
            device for device in self.data[DATA_DEVICES].values()
            if device.get("online", False)
        ]

    def get_devices_for_home(self, home_id: str) -> List[Dict[str, Any]]:
        """Get all devices for a specific home."""
        if not self.data or DATA_DEVICES not in self.data:
            return []

        return [
            device for device in self.data[DATA_DEVICES].values()
            if device.get("home_id") == home_id
        ]

    @property
    def oauth_session(self) -> Optional[TibberOAuthSession]:
        """Get the current OAuth session."""
        return self._oauth_session

    async def async_close(self) -> None:
        """Close the coordinator and cleanup resources."""
        if self.client:
            await self.client.close()

    async def async_refresh_token_if_needed(self) -> bool:
        """Refresh token if needed and return True if refreshed."""
        try:
            await self._ensure_valid_token()
            return True
        except UpdateFailed:
            return False

    async def _update_device_areas_if_needed(self, new_homes: Dict[str, Dict[str, Any]]) -> None:
        """Update device areas if home names have changed."""
        from homeassistant.helpers.device_registry import async_get as async_get_device_registry

        # Check if we have previous data to compare
        if not self.data or DATA_HOMES not in self.data:
            return

        old_homes = self.data[DATA_HOMES]
        device_registry = async_get_device_registry(self.hass)

        # Check each home for name changes
        for home_id, new_home_data in new_homes.items():
            new_name = new_home_data.get("displayName")
            old_home_data = old_homes.get(home_id, {})
            old_name = old_home_data.get("displayName")

            # If home name has changed, update device areas
            if new_name and old_name and new_name != old_name:
                _LOGGER.info("Home name changed: %s -> %s", old_name, new_name)

                # Update the hub device itself
                hub_device = device_registry.async_get_device({(DOMAIN, f"home_{home_id}")})
                if hub_device:
                    device_registry.async_update_device(hub_device.id, name=new_name)

                # Update all devices for this home with new suggested area
                if DATA_DEVICES in self.data:
                    for device_id, device_data in self.data[DATA_DEVICES].items():
                        if device_data.get("home_id") == home_id:
                            device = device_registry.async_get_device({(DOMAIN, device_id)})
                            if device:
                                device_registry.async_update_device(
                                    device.id, suggested_area=new_name
                                )