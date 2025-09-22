"""Sensor platform for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union, cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass
)
from homeassistant.helpers.entity import EntityCategory  # type: ignore[attr-defined]
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_COORDINATOR, CAPABILITY_MAPPINGS, SENSOR_NAME_MAPPINGS, ATTRIBUTE_MAPPINGS
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

    entities: List[SensorEntity] = []

    if coordinator.data and "devices" in coordinator.data:
        for device_id, device_data in coordinator.data["devices"].items():
            # Skip devices with name "Dummy" (case-insensitive)
            device_name = device_data.get("name", "").strip()
            if device_name.lower() == "dummy":
                _LOGGER.debug("Skipping sensors for dummy device: %s", device_id)
                continue

            # Create sensor entities for device capabilities
            for capability in device_data.get("capabilities", []):
                capability_name = capability["name"]

                # Create diagnostic sensors for capabilities that should be diagnostic
                if _should_be_diagnostic(capability_name):
                    _LOGGER.debug("Creating diagnostic sensor for capability %s", capability_name)
                    entities.append(
                        TibberDataCapabilitySensor(
                            coordinator=coordinator,
                            device_id=device_id,
                            capability_name=capability_name,
                            is_diagnostic=True
                        )
                    )
                    continue

                # Check if this is a string sensor (has availableValues)
                is_string_sensor = "availableValues" in capability

                if is_string_sensor:
                    _LOGGER.debug("Creating string sensor for capability: %s", capability_name)
                    sensor_class: Union[type[TibberDataStringSensor], type[TibberDataCapabilitySensor]] = TibberDataStringSensor
                else:
                    sensor_class = TibberDataCapabilitySensor

                entities.append(
                    sensor_class(
                        coordinator=coordinator,
                        device_id=device_id,
                        capability_name=capability_name
                    )
                )

            # Create diagnostic sensor entities for device attributes
            for attribute in device_data.get("attributes", []):
                attribute_name = attribute["name"]
                entities.append(
                    TibberDataAttributeSensor(
                        coordinator=coordinator,
                        device_id=device_id,
                        attribute_name=attribute_name
                    )
                )

    if entities:
        async_add_entities(entities, True)
        _LOGGER.debug("Added %d sensor entities", len(entities))


def _should_be_diagnostic(capability_name: str) -> bool:
    """Determine if a capability should be a diagnostic sensor instead of a regular sensor."""
    diagnostic_capability_names = {
        "isOnline",
        "connectivity.wifi",
        "connectivity.cellular",
        "firmwareVersion",
        "Firmwareversion",
        "firmwareversion",
        "serialNumber",
        "wifi.rssi",
        "cellular.rssi"
    }
    return capability_name in diagnostic_capability_names


class TibberDataStringSensor(TibberDataCapabilityEntity, SensorEntity):
    """String sensor entity for device capabilities with availableValues.

    Uses SensorEntity but completely overrides all methods to prevent numeric conversion.
    """

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        capability_name: str
    ) -> None:
        """Initialize the string sensor."""
        super().__init__(coordinator, device_id, capability_name)

        # Get display name
        capability_data = self.capability_data
        display_name = capability_data.get("displayName", capability_name.replace("_", " ").title()) if capability_data else capability_name.replace("_", " ").title()

        # Get icon from mapping
        mapping: Dict[str, Any] = cast(Dict[str, Any], CAPABILITY_MAPPINGS.get(capability_name, {}))
        icon = mapping.get("icon")

        # Create a minimal entity description with NO numeric properties
        self.entity_description = SensorEntityDescription(
            key=capability_name,
            name=display_name,
            icon=icon,
            # Explicitly avoid all numeric properties
            has_entity_name=True,
        )

        # Set all numeric attributes to None using _attr approach
        self._attr_device_class = None
        self._attr_state_class = None
        self._attr_native_unit_of_measurement = None
        self._attr_unit_of_measurement = None
        self._attr_suggested_display_precision = None

    @property
    def native_value(self) -> str:
        """Return string value, never None to avoid numeric conversion."""
        capability_data = self.capability_data
        if not capability_data:
            return "Unknown"

        value = capability_data.get("value")
        if value is None:
            return "Unknown"
        return str(value).capitalize()

    # Don't override state - let SensorEntity handle it but ensure native_value is always string
    # and all numeric indicators are None

    @property
    def device_class(self) -> None:
        """Always return None for device class."""
        return None

    @property
    def state_class(self) -> None:
        """Always return None for state class."""
        return None

    @property
    def native_unit_of_measurement(self) -> None:
        """Always return None for unit."""
        return None


    @property
    def suggested_display_precision(self) -> None:
        """Always return None for precision."""
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = super().extra_state_attributes

        capability_data = self.capability_data
        if capability_data:
            # Add available values for reference
            if "availableValues" in capability_data:
                attributes["available_values"] = capability_data["availableValues"]

        return attributes


class TibberDataCapabilitySensor(TibberDataCapabilityEntity, SensorEntity):
    """Sensor entity for device capabilities."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        capability_name: str,
        is_diagnostic: bool = False
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, capability_name)
        self._is_diagnostic = is_diagnostic

        # Set entity description based on capability type
        self.entity_description = self._get_entity_description(capability_name)

    def _get_entity_description(self, capability_name: str) -> SensorEntityDescription:
        """Get entity description for capability."""
        # Get mapping configuration
        mapping: Dict[str, Any] = cast(Dict[str, Any], CAPABILITY_MAPPINGS.get(capability_name, {}))

        capability_data = self.capability_data
        unit = capability_data.get("unit", "") if capability_data else ""
        display_name = capability_data.get("displayName", capability_name.replace("_", " ").title()) if capability_data else capability_name.replace("_", " ").title()

        # Determine device class based on mapping or unit
        device_class: Optional[SensorDeviceClass] = None
        device_class_str = mapping.get("device_class")
        if device_class_str:
            # Convert string device class to enum
            try:
                device_class = SensorDeviceClass(device_class_str)
            except ValueError:
                device_class = self._infer_device_class_from_unit(unit)
        else:
            device_class = self._infer_device_class_from_unit(unit)

        # Determine state class
        state_class = mapping.get("state_class")
        if state_class is None and "state_class" not in mapping:
            # Only infer if state_class is not explicitly set in mapping
            state_class = self._infer_state_class(capability_name, unit)

        # Determine if this should be a diagnostic sensor
        entity_category = EntityCategory.DIAGNOSTIC if self._is_diagnostic else None
        enabled_default = True

        # Get icon from mapping
        icon = mapping.get("icon")

        # Check if this is a string sensor by looking at the capability data
        capability_data = self.capability_data
        is_string_sensor = (
            capability_data and
            "availableValues" in capability_data and
            not unit and
            device_class is None and
            state_class is None
        )

        if is_string_sensor:
            # For string sensors, explicitly avoid any numeric properties
            return SensorEntityDescription(
                key=capability_name,
                name=display_name,
                icon=icon,
                entity_category=entity_category,
                entity_registry_enabled_default=enabled_default,
            )
        else:
            # For numeric sensors, include all the properties
            return SensorEntityDescription(
                key=capability_name,
                name=display_name,
                device_class=device_class,
                state_class=state_class,
                native_unit_of_measurement=unit or None,
                icon=icon,
                entity_category=entity_category,
                entity_registry_enabled_default=enabled_default,
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
        # If there's no unit, default to None (string sensor) unless we're very sure it's numeric
        if not unit:
            return None

        # Energy units (kWh, Wh) should use appropriate state class based on capability name
        if unit in ["kWh", "Wh"]:
            # Energy consumption/usage is typically total_increasing
            if any(keyword in capability_name.lower() for keyword in ["consumption", "usage", "used", "imported"]):
                return SensorStateClass.TOTAL_INCREASING
            # Energy storage/capacity is usually total (can go up and down)
            elif any(keyword in capability_name.lower() for keyword in ["storage", "capacity", "stored", "available"]):
                return SensorStateClass.TOTAL
            # Energy production is typically total_increasing
            elif any(keyword in capability_name.lower() for keyword in ["production", "generated", "exported"]):
                return SensorStateClass.TOTAL_INCREASING
            # Default for energy units is total (safest choice)
            else:
                return SensorStateClass.TOTAL

        # Only assign state classes when we have clear numeric units
        numeric_units = ["%", "°C", "°F", "A", "V", "Hz", "rpm", "kW", "W", "dBm"]
        if unit in numeric_units:
            # Power, temperature, battery level are measurements
            if any(keyword in capability_name.lower() for keyword in ["power", "temperature", "battery", "level", "current", "voltage", "signal"]):
                return SensorStateClass.MEASUREMENT
            # Default to measurement for numeric units
            return SensorStateClass.MEASUREMENT

        # For any unit we don't recognize or status/state sensors, default to None
        return None


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
    def suggested_display_precision(self) -> Optional[int]:
        """Return the suggested number of decimal places for display."""
        capability_data = self.capability_data
        if capability_data and "precision" in capability_data:
            precision: Optional[int] = capability_data["precision"]
            return precision
        return None

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

    @property
    def name(self) -> str:
        """Return entity name with human-readable capability name."""
        device_data = self.device_data
        if not device_data:
            return f"Unknown Device {self._get_human_readable_capability_name(self._capability_name)}"

        # Get device name using fallback logic
        device_name = self._get_device_display_name(device_data)

        # Get human-readable capability name
        capability_display_name = self._get_human_readable_capability_name(self._capability_name)

        return f"{device_name} {capability_display_name}"

    def _get_human_readable_capability_name(self, capability_name: str) -> str:
        """Get human-readable name for capability."""
        # Return mapped name if available, otherwise create readable name from capability name
        if capability_name in SENSOR_NAME_MAPPINGS:
            return SENSOR_NAME_MAPPINGS[capability_name]

        # Fallback: convert capability name to readable format
        return capability_name.replace("_", " ").replace(".", " ").title()


class TibberDataAttributeSensor(TibberDataCapabilityEntity, SensorEntity):
    """Diagnostic sensor entity for device attributes."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        attribute_name: str
    ) -> None:
        """Initialize the attribute sensor."""
        super().__init__(coordinator, device_id, attribute_name)

        # Set entity description for diagnostic attributes
        self.entity_description = self._get_attribute_entity_description(attribute_name)

    def _get_attribute_entity_description(self, attribute_name: str) -> SensorEntityDescription:
        """Get entity description for attribute."""
        # Get human-readable name for the attribute
        display_name = self._get_human_readable_name(attribute_name)

        # All attributes are diagnostic sensors
        entity_category = EntityCategory.DIAGNOSTIC
        enabled_default = True

        # Determine appropriate icon based on attribute name
        icon = self._get_attribute_icon(attribute_name)

        return SensorEntityDescription(
            key=attribute_name,
            name=display_name,
            icon=icon,
            entity_category=entity_category,
            entity_registry_enabled_default=enabled_default,
        )

    def _get_human_readable_name(self, sensor_name: str) -> str:
        """Get human-readable name for sensor."""
        # Return mapped name if available, otherwise create readable name from sensor name
        if sensor_name in SENSOR_NAME_MAPPINGS:
            return SENSOR_NAME_MAPPINGS[sensor_name]

        # Fallback: convert sensor name to readable format
        return sensor_name.replace("_", " ").replace(".", " ").title()

    def _get_attribute_icon(self, attribute_name: str) -> Optional[str]:
        """Get appropriate icon for attribute."""
        # Check if we have a mapping for this attribute
        if attribute_name in ATTRIBUTE_MAPPINGS:
            mapping = ATTRIBUTE_MAPPINGS[attribute_name]
            if "icon" in mapping:
                return mapping["icon"]

        # Fallback to pattern matching
        name_lower = attribute_name.lower()

        if "wifi" in name_lower or "connectivity.wifi" in name_lower:
            return "mdi:wifi"
        elif "cellular" in name_lower or "connectivity.cellular" in name_lower:
            return "mdi:signal"
        elif "firmware" in name_lower:
            return "mdi:chip"
        elif "serial" in name_lower:
            return "mdi:barcode"
        elif "isonline" in name_lower or "online" in name_lower:
            return "mdi:lan-connect"

        return "mdi:information"

    @property
    def capability_data(self) -> Optional[Dict[str, Any]]:
        """Override to get attribute data instead of capability data."""
        return self._get_attribute_data(self._capability_name)

    @property
    def name(self) -> str:
        """Return entity name with human-readable attribute name."""
        device_data = self.device_data
        if not device_data:
            return f"Unknown Device {self._get_human_readable_name(self._capability_name)}"

        # Get device name using fallback logic
        device_name = self._get_device_display_name(device_data)

        # Get human-readable attribute name
        attribute_display_name = self._get_human_readable_name(self._capability_name)

        return f"{device_name} {attribute_display_name}"

    @property
    def native_value(self) -> Optional[float | int | str]:
        """Return the state of the sensor."""
        attribute_data = self.capability_data
        if not attribute_data:
            return None

        # Handle different attribute value formats
        if "value" in attribute_data:
            value = attribute_data["value"]
            return cast(Union[float, int, str, None], value)
        elif "status" in attribute_data:
            status = attribute_data["status"]
            # Map API status values to more user-friendly values
            status_mappings = {
                "unknown": "Not Available",
                "connected": "Connected",
                "disconnected": "Disconnected",
                "offline": "Offline",
                "online": "Online"
            }
            mapped_status = status_mappings.get(status, status)
            return cast(Union[float, int, str, None], mapped_status)

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = super().extra_state_attributes

        attribute_data = self.capability_data
        if attribute_data:
            # Add all additional fields from the attribute data as extra state attributes
            # Exclude standard fields that are already handled elsewhere
            excluded_fields = {"name", "displayName", "value", "status", "dataType", "lastUpdated", "isDiagnostic", "id"}

            for key, value in attribute_data.items():
                if key not in excluded_fields and value is not None:
                    # Convert camelCase field names to snake_case for consistency with HA conventions
                    attr_key = self._camel_to_snake(key)
                    attributes[attr_key] = value

        return attributes

    def _camel_to_snake(self, camel_str: str) -> str:
        """Convert camelCase to snake_case."""
        import re
        # Insert underscore before uppercase letters that follow lowercase letters
        snake_str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', camel_str)
        return snake_str.lower()