"""Tibber Data integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_device_registry, DeviceEntryType

from .api.client import TibberDataClient
from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_COORDINATOR,
    DATA_CLIENT,
    DATA_OAUTH_SESSION,
    STARTUP_MESSAGE,
)
from .coordinator import TibberDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tibber Data from a config entry."""
    _LOGGER.info(STARTUP_MESSAGE)

    # Initialize aiohttp session
    session = async_get_clientsession(hass)

    # Create OAuth2 session for automatic token refresh
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # Create API client
    client = TibberDataClient(session=session)

    # Create update coordinator with OAuth2 session
    coordinator = TibberDataUpdateCoordinator(
        hass=hass,
        client=client,
        config_entry=entry,
        oauth_session=oauth_session
    )

    # Store coordinator, client, and OAuth session in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_CLIENT: client,
        DATA_OAUTH_SESSION: oauth_session
    }

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Register devices in device registry first (before platforms)
    # This ensures hub devices exist before entities try to reference them
    await _async_register_devices(hass, coordinator, entry)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register cleanup listener
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_stop_handler)
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Clean up stored data
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, {})

        # Close client connection
        client = entry_data.get(DATA_CLIENT)
        if client:
            await client.close()

        # Close coordinator
        coordinator = entry_data.get(DATA_COORDINATOR)
        if coordinator:
            await coordinator.async_close()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _async_register_devices(
    hass: HomeAssistant,
    coordinator: TibberDataUpdateCoordinator,
    entry: ConfigEntry
) -> None:
    """Register devices in Home Assistant device registry."""
    device_registry = async_get_device_registry(hass)

    if not coordinator.data:
        return

    # First, register hub devices for each home
    registered_homes = set()
    if "homes" in coordinator.data:
        for home_id, home_data in coordinator.data["homes"].items():
            base_name = home_data.get("displayName") or f"Home {home_id[:8]}"
            home_name = f"Tibber Data {base_name}"

            # Register hub device for the home
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, f"home_{home_id}")},
                name=home_name,
                manufacturer="Tibber",
                model="Tibber Home",
                configuration_url="https://data-api.tibber.com/clients/manage",
                entry_type=DeviceEntryType.SERVICE  # Mark as hub/service device
            )
            registered_homes.add(home_id)
            _LOGGER.debug("Registered hub device for home: %s", home_name)

    # Then register individual devices with their hub as parent
    if "devices" in coordinator.data:
        for device_id, device_data in coordinator.data["devices"].items():
            # Get home data for hub relationship
            home_id = device_data.get("home_id")
            home_data = coordinator.data.get("homes", {}).get(home_id, {})
            suggested_area = home_data.get("displayName")

            # Prepare device name using our helper logic
            device_name = device_data.get("name")
            if not device_name or not device_name.strip():
                manufacturer = device_data.get("manufacturer", "Unknown")
                model = device_data.get("model", "Device")
                device_name = f"{manufacturer} {model}"

            # Register device with hub as parent
            via_device = (DOMAIN, f"home_{home_id}") if home_id in registered_homes else None

            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, device_id)},
                name=device_name,
                manufacturer=device_data.get("manufacturer", "Tibber"),
                model=device_data.get("model", "Unknown"),
                suggested_area=suggested_area,
                configuration_url="https://data-api.tibber.com/clients/manage",
                via_device=via_device
            )

        _LOGGER.debug("Registered %d devices under %d hubs",
                     len(coordinator.data["devices"]), len(registered_homes))


async def _async_stop_handler(event: Any) -> None:  # noqa: ARG001
    """Handle Home Assistant stop event."""
    # Cleanup is handled by async_unload_entry
    pass