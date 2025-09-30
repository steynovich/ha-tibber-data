"""Data update coordinator for Tibber Data integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api.client import TibberDataClient
from .api.models import TibberDevice
from .const import (
    DOMAIN,
    DATA_HOMES,
    DATA_DEVICES,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class TibberDataUpdateCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    """Class to manage fetching data from Tibber Data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TibberDataClient,
        config_entry: ConfigEntry,
        oauth_session: Optional[Any] = None,
        update_interval: Optional[timedelta] = None
    ) -> None:
        """Initialize the coordinator."""
        self.client = client
        self.config_entry: ConfigEntry = config_entry
        self.oauth_session = oauth_session

        # Use provided update interval or default
        interval = update_interval or DEFAULT_UPDATE_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=interval,
        )

    async def _get_access_token(self) -> str:
        """Get current access token with automatic refresh via OAuth2Session."""
        if not self.oauth_session:
            _LOGGER.error("No OAuth2 session available")
            raise UpdateFailed("No OAuth2 session - please re-authenticate")

        try:
            # Ensure token is valid (will refresh if needed)
            await self.oauth_session.async_ensure_token_valid()
        except Exception as err:
            _LOGGER.warning("Cannot refresh token - client ID not available, triggering reauth")
            _LOGGER.error("Failed to refresh token: %s", err)
            # Trigger reauth flow
            self.config_entry.async_start_reauth(self.hass)
            raise UpdateFailed(f"Token refresh failed: {err}") from err

        # Get the token from OAuth2Session
        token = self.oauth_session.token
        if not token or "access_token" not in token:
            _LOGGER.error("OAuth2Session returned invalid token")
            raise UpdateFailed("Invalid OAuth2 token - please re-authenticate")

        return token["access_token"]

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            # Get current access token
            self.client._access_token = await self._get_access_token()

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
                    capabilities.append({
                        "name": capability.name,
                        "displayName": capability.display_name,
                        "value": capability.value,
                        "unit": capability.unit,
                        "lastUpdated": capability.last_updated.isoformat()
                    })

                # Convert attributes to the expected format
                attributes = []
                for attribute in device.attributes:
                    attributes.append({
                        "name": attribute.name,
                        "displayName": attribute.display_name,
                        "value": attribute.value,
                        "dataType": attribute.data_type,
                        "lastUpdated": attribute.last_updated.isoformat(),
                        "isDiagnostic": attribute.is_diagnostic
                    })

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

            return {
                DATA_HOMES: homes,
                DATA_DEVICES: devices
            }

        except Exception as err:
            # Log specific error types for better debugging
            if "401" in str(err) or "Invalid or expired token" in str(err) or "Unauthorized" in str(err):
                _LOGGER.error("Authentication failed: %s", err)
                raise UpdateFailed("Authentication failed - please reauthorize in integrations") from err
            elif "Rate limit exceeded" in str(err):
                _LOGGER.warning("API rate limit exceeded, will retry later")
                raise UpdateFailed("Rate limit exceeded") from err
            elif "cannot connect" in str(err).lower() or "timeout" in str(err).lower():
                _LOGGER.warning("API connection failed: %s", err)
                raise UpdateFailed(f"API unavailable: {err}") from err
            else:
                _LOGGER.error("Unexpected error fetching data: %s", err)
                raise UpdateFailed(f"Unexpected error: {err}") from err


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

            # Ensure we have a valid token before making API call
            try:
                self.client._access_token = await self._get_access_token()
            except UpdateFailed as err:
                _LOGGER.error("Failed to get valid token for device update: %s", err)
                return False

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
                    capabilities.append({
                        "name": capability.name,
                        "displayName": capability.display_name,
                        "value": capability.value,
                        "unit": capability.unit,
                        "lastUpdated": capability.last_updated.isoformat()
                    })

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

    async def async_close(self) -> None:
        """Close the coordinator and cleanup resources."""
        if self.client:
            await self.client.close()