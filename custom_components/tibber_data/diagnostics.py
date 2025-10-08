"""Diagnostics support for Tibber Data."""
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DATA_COORDINATOR, DATA_DEVICES, DOMAIN
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
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

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
            "update_interval": coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
        },
        "api_data": async_redact_data(coordinator.data, TO_REDACT) if coordinator.data else None,
    }

    return diagnostics_data


async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    # Find the device in coordinator data
    device_data = None
    if coordinator.data and isinstance(coordinator.data, dict):
        devices = coordinator.data.get(DATA_DEVICES, {})
        # Find device by matching identifiers
        for device_id, dev_data in devices.items():
            # Match by device identifiers - check if device_id is in any identifier tuple
            if any(device_id in str(identifier) for identifier in device.identifiers):
                device_data = dev_data
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
