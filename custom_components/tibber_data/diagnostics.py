"""Diagnostics support for Tibber Data."""
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN
from .coordinator import TibberDataUpdateCoordinator

# Keys to redact for privacy/security
TO_REDACT = {
    "access_token",
    "refresh_token",
    "token",
    "vinNumber",
    "vin",
    "serialNumber",
    "serial",
    "email",
    "phoneNumber",
    "phone",
    "address",
    "latitude",
    "longitude",
    "lat",
    "lon",
    "userId",
    "user_id",
    "homeId",
    "home_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": coordinator.update_interval.total_seconds(),
        },
        "api_data": async_redact_data(coordinator.data, TO_REDACT) if coordinator.data else None,
    }

    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Find the device in coordinator data
    device_data = None
    if coordinator.data and isinstance(coordinator.data, dict):
        homes = coordinator.data.get("homes", [])
        for home in homes:
            devices = home.get("devices", [])
            for dev in devices:
                # Match by device identifiers
                dev_id = dev.get("id")
                if dev_id and any(dev_id in identifier for identifier in device.identifiers):
                    device_data = dev
                    break
            if device_data:
                break

    diagnostics_data = {
        "device": {
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.sw_version,
            "identifiers": [list(identifier) for identifier in device.identifiers],
        },
        "device_data": async_redact_data(device_data, TO_REDACT) if device_data else None,
    }

    return diagnostics_data
