"""Sensor platform for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_COORDINATOR, CAPABILITY_MAPPINGS
from .coordinator import TibberDataUpdateCoordinator
from .entity import TibberDataCapabilityEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tibber Data sensor entities."""
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]

    entities: List[TibberDataCapabilitySensor] = []

    if coordinator.data and "devices" in coordinator.data:
        for device_id, device_data in coordinator.data["devices"].items():
            # Create sensor entities for device capabilities
            for capability in device_data.get("capabilities", []):
                capability_name = capability["name"]
                entities.append(
                    TibberDataCapabilitySensor(
                        coordinator=coordinator,
                        device_id=device_id,
                        capability_name=capability_name
                    )
                )

    if entities:
        async_add_entities(entities, True)
        _LOGGER.debug("Added %d sensor entities", len(entities))


class TibberDataCapabilitySensor(TibberDataCapabilityEntity, SensorEntity):
    """Sensor entity for device capabilities."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        capability_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, capability_name)

        # Set entity description based on capability type
        self.entity_description = self._get_entity_description(capability_name)

    def _get_entity_description(self, capability_name: str) -> SensorEntityDescription:
        """Get entity description for capability."""
        # Get mapping configuration
        mapping = CAPABILITY_MAPPINGS.get(capability_name, {})

        capability_data = self.capability_data
        unit = capability_data.get("unit", "") if capability_data else ""
        display_name = capability_data.get("displayName", capability_name.replace("_", " ").title()) if capability_data else capability_name.replace("_", " ").title()

        # Determine device class based on mapping or unit
        device_class = mapping.get("device_class")
        if not device_class:
            device_class = self._infer_device_class_from_unit(unit)

        # Determine state class
        state_class = mapping.get("state_class")
        if not state_class:
            state_class = self._infer_state_class(capability_name, unit)

        return SensorEntityDescription(
            key=capability_name,
            name=display_name,
            device_class=device_class,
            state_class=state_class,
            native_unit_of_measurement=unit or None,
            icon=mapping.get("icon"),
        )

    def _infer_device_class_from_unit(self, unit: str) -> Optional[SensorDeviceClass]:
        """Infer device class from unit."""
        unit_mappings = {
            "%": SensorDeviceClass.BATTERY,
            "kW": SensorDeviceClass.POWER,
            "W": SensorDeviceClass.POWER,
            "kWh": SensorDeviceClass.ENERGY,
            "Wh": SensorDeviceClass.ENERGY,
            "°C": SensorDeviceClass.TEMPERATURE,
            "°F": SensorDeviceClass.TEMPERATURE,
            "A": SensorDeviceClass.CURRENT,
            "V": SensorDeviceClass.VOLTAGE,
            "dBm": SensorDeviceClass.SIGNAL_STRENGTH,
        }
        return unit_mappings.get(unit)

    def _infer_state_class(self, capability_name: str, unit: str) -> Optional[SensorStateClass]:
        """Infer state class from capability name and unit."""
        # Energy consumption is usually total increasing
        if "energy" in capability_name.lower() or "consumption" in capability_name.lower():
            return SensorStateClass.TOTAL_INCREASING

        # Power, temperature, battery level are measurements
        if any(keyword in capability_name.lower() for keyword in ["power", "temperature", "battery", "level", "current", "voltage"]):
            return SensorStateClass.MEASUREMENT

        # Default to measurement for numeric values
        return SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> Optional[float | int | str]:
        """Return the state of the sensor."""
        capability_data = self.capability_data
        if not capability_data:
            return None

        return capability_data.get("value")

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        capability_data = self.capability_data
        if not capability_data:
            return None

        return capability_data.get("unit")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = super().extra_state_attributes

        capability_data = self.capability_data
        if capability_data:
            # Add precision for display formatting
            if "precision" in capability_data:
                attributes["precision"] = capability_data["precision"]

            # Add formatted value if precision is specified
            if isinstance(capability_data.get("value"), (int, float)) and capability_data.get("precision") is not None:
                precision = capability_data["precision"]
                value = capability_data["value"]
                attributes["formatted_value"] = f"{value:.{precision}f}"

        return attributes

    @property
    def suggested_display_precision(self) -> Optional[int]:
        """Return the suggested number of decimal places for display."""
        capability_data = self.capability_data
        if capability_data and "precision" in capability_data:
            return capability_data["precision"]
        return None

    @property
    def icon(self) -> Optional[str]:
        """Return the icon for the entity."""
        # Check if entity description has an icon
        if hasattr(self.entity_description, 'icon') and self.entity_description.icon:
            return self.entity_description.icon

        # Fallback icons based on capability name
        capability_name = self._capability_name.lower()

        if "battery" in capability_name:
            # Dynamic battery icon based on level
            value = self.native_value
            if isinstance(value, (int, float)):
                if value <= 10:
                    return "mdi:battery-10"
                elif value <= 20:
                    return "mdi:battery-20"
                elif value <= 30:
                    return "mdi:battery-30"
                elif value <= 40:
                    return "mdi:battery-40"
                elif value <= 50:
                    return "mdi:battery-50"
                elif value <= 60:
                    return "mdi:battery-60"
                elif value <= 70:
                    return "mdi:battery-70"
                elif value <= 80:
                    return "mdi:battery-80"
                elif value <= 90:
                    return "mdi:battery-90"
                else:
                    return "mdi:battery"
            return "mdi:battery"
        elif "charging" in capability_name and "power" in capability_name:
            return "mdi:lightning-bolt"
        elif "temperature" in capability_name:
            return "mdi:thermometer"
        elif "current" in capability_name:
            return "mdi:current-ac"
        elif "voltage" in capability_name:
            return "mdi:sine-wave"
        elif "energy" in capability_name:
            return "mdi:flash"
        elif "power" in capability_name:
            return "mdi:flash-outline"
        elif "signal" in capability_name:
            return "mdi:wifi"

        return None