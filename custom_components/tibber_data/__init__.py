"""Tibber Data integration for Home Assistant."""
from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import async_get as async_get_device_registry

from .api.client import TibberDataClient
from .const import (
    DOMAIN,
    PLATFORMS,
    DATA_COORDINATOR,
    DATA_CLIENT,
    STARTUP_MESSAGE,
    CONF_CLIENT_ID
)
from .coordinator import TibberDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tibber Data from a config entry."""
    _LOGGER.info(STARTUP_MESSAGE)

    # Validate config entry data
    if not entry.data.get(CONF_CLIENT_ID):
        _LOGGER.error("Config entry missing client_id")
        return False

    # Initialize aiohttp session
    session = async_get_clientsession(hass)

    # Create API client
    client = TibberDataClient(
        client_id=entry.data[CONF_CLIENT_ID],
        session=session
    )

    # Create update coordinator
    coordinator = TibberDataUpdateCoordinator(
        hass=hass,
        client=client,
        config_entry=entry
    )

    # Store coordinator and client in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_CLIENT: client
    }

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to fetch initial data: %s", err)
        # Still proceed with setup - coordinator will retry
        pass

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register devices in device registry
    await _async_register_devices(hass, coordinator, entry)

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

    if not coordinator.data or "devices" not in coordinator.data:
        return

    for device_id, device_data in coordinator.data["devices"].items():
        # Get home data for suggested area
        home_id = device_data.get("home_id")
        home_data = coordinator.data.get("homes", {}).get(home_id, {})
        suggested_area = home_data.get("displayName")

        # Register device
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, device_id)},
            name=device_data.get("name", f"Tibber Device {device_id}"),
            manufacturer=device_data.get("manufacturer", "Tibber"),
            model=device_data.get("model", device_data.get("type", "Unknown")),
            suggested_area=suggested_area,
            configuration_url="https://data-api.tibber.com/clients/manage",
        )

    _LOGGER.debug("Registered %d devices", len(coordinator.data["devices"]))


async def _async_stop_handler(event) -> None:
    """Handle Home Assistant stop event."""
    # Cleanup is handled by async_unload_entry
    pass