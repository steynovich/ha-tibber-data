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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_COORDINATOR, CAPABILITY_MAPPINGS, ATTRIBUTE_MAPPINGS
from .coordinator import TibberDataUpdateCoordinator
from .entity import TibberDataCapabilityEntity, TibberDataAttributeEntity

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
                entities.append(
                    TibberDataCapabilitySensor(
                        coordinator=coordinator,
                        device_id=device_id,
                        capability_name=capability_name
                    )
                )

            # Create sensor entities for non-boolean device attributes
            for attribute in device_data.get("attributes", []):
                attribute_value = attribute.get("value")

                # Skip boolean attributes (handled by binary_sensor platform)
                if isinstance(attribute_value, bool):
                    continue

                # Create sensor for string/numeric attributes
                if isinstance(attribute_value, (str, int, float)):
                    attribute_path = attribute["name"]

                    # Check for custom display name in mappings first
                    mapping = ATTRIBUTE_MAPPINGS.get(attribute_path, {})
                    display_name = mapping.get("name_suffix")

                    # Fall back to API displayName or attribute name
                    if not display_name:
                        display_name = attribute.get("displayName", attribute_path)

                    entities.append(
                        TibberDataAttributeSensor(
                            coordinator=coordinator,
                            device_id=device_id,
                            attribute_path=attribute_path,
                            attribute_name=display_name
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

        # Don't set device_class or state_class in description - both will be
        # determined dynamically when we have actual data available
        return SensorEntityDescription(
            key=capability_name,
            name=None,  # Let the entity's name property handle the full name
            device_class=None,  # Determined dynamically via property
            state_class=None,  # Determined dynamically via property
            native_unit_of_measurement=None,  # Determined dynamically via property
            icon=mapping.get("icon"),
        )

    def _infer_device_class_from_value_and_unit(self, value: Any, unit: str) -> SensorDeviceClass | None:
        """Infer device class from value and unit."""
        # Check if the value is a string - if so, use ENUM device class
        if isinstance(value, str):
            return SensorDeviceClass.ENUM

        # Special handling for percentage sensors
        if unit == "%":
            # Only consider it a battery sensor if capability name suggests battery/storage
            capability_lower = self._capability_name.lower()
            if any(keyword in capability_lower for keyword in ["battery", "storage", "stateofcharge", "charge"]):
                return SensorDeviceClass.BATTERY
            # Otherwise, percentage sensors (like power flow %) should have no device class
            return None

        unit_mappings: dict[str, SensorDeviceClass] = {
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

    def _infer_state_class_from_value(self, capability_name: str, value: Any, unit: str) -> Optional[SensorStateClass]:
        """Infer state class from capability name, value, and unit."""
        # Check if the value is a string or None - if so, no state_class
        if value is None or isinstance(value, str):
            # String values and None should not have a state class
            return None

        capability_lower = capability_name.lower()

        # Periodic energy sensors (hourly, daily, weekly, monthly) should have NO state class
        # These reset to 0 at period boundaries and should not be treated as cumulative totals
        if any(period in capability_lower for period in [".hour.", ".day.", ".week.", ".month.", ".year."]):
            if unit in ["kWh", "Wh"] or "energy" in capability_lower:
                return None

        # Non-periodic energy units (kWh, Wh) use TOTAL state class
        # These are storage levels or lifetime totals that can increase or decrease
        if unit in ["kWh", "Wh"]:
            return SensorStateClass.TOTAL

        # Other energy-related capabilities without energy units also use TOTAL
        if "energy" in capability_lower:
            return SensorStateClass.TOTAL

        # Power, temperature, battery level are measurements
        if any(keyword in capability_lower for keyword in ["power", "temperature", "battery", "level", "current", "voltage", "signal"]):
            return SensorStateClass.MEASUREMENT

        # Default to measurement for numeric values
        return SensorStateClass.MEASUREMENT

    @property
    def device_class(self) -> Optional[SensorDeviceClass]:
        """Return the device class, determined dynamically from current value."""
        # Check if mapping has explicit device_class
        mapping = CAPABILITY_MAPPINGS.get(self._capability_name, {})
        device_class_str = mapping.get("device_class")
        if device_class_str:
            try:
                return SensorDeviceClass(device_class_str)
            except (ValueError, TypeError):
                pass

        # Get current capability data
        capability_data = self.capability_data
        if not capability_data:
            return None

        value = capability_data.get("value")
        unit = capability_data.get("unit", "")

        # Infer device class from value and unit
        return self._infer_device_class_from_value_and_unit(value, unit)

    @property
    def state_class(self) -> Optional[SensorStateClass]:
        """Return the state class, determined dynamically from current value."""
        # Check if mapping has explicit state_class
        mapping = CAPABILITY_MAPPINGS.get(self._capability_name, {})
        if "state_class" in mapping:
            state_class_str = mapping.get("state_class")
            if state_class_str:
                try:
                    return SensorStateClass(state_class_str)
                except (ValueError, TypeError):
                    pass

        # Get current capability data
        capability_data = self.capability_data
        if not capability_data:
            return None

        value = capability_data.get("value")
        unit = capability_data.get("unit", "")

        # Determine state class based on current value
        return self._infer_state_class_from_value(self._capability_name, value, unit)

    @property
    def native_value(self) -> Optional[float | int | str]:
        """Return the state of the sensor."""
        capability_data = self.capability_data
        if not capability_data:
            return None

        value = capability_data.get("value")
        unit = capability_data.get("unit", "")

        # Apply title case to string values (for ENUM sensors)
        if isinstance(value, str):
            # Check if this is an ENUM sensor by checking device class or inferring from string value
            device_class = self.device_class
            is_enum = (
                device_class == SensorDeviceClass.ENUM or
                (device_class is None and isinstance(value, str))
            )
            if is_enum:
                return value.title()

        # Convert meters to kilometers for range/distance sensors
        if isinstance(value, (int, float)) and unit == "m" and "range" in self._capability_name.lower():
            return round(value / 1000, 1)  # Convert to km with 1 decimal place

        # Convert decimal ratios to percentages for powerFlow distribution sensors
        # API returns values like 0.9 (meaning 90%) for powerFlow distribution ratios
        if isinstance(value, (int, float)) and unit == "%" and value <= 1.0:
            # Only apply to capabilities that start with "powerFlow."
            if self._capability_name.startswith("powerFlow.") and 0 <= value <= 1.0:
                return round(value * 100, 1)  # Convert 0.9 to 90.0

        return value

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement."""
        capability_data = self.capability_data
        if not capability_data:
            return None

        unit = capability_data.get("unit", "")

        # Convert meters to kilometers for range/distance sensors
        if unit == "m" and "range" in self._capability_name.lower():
            return "km"

        return unit

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
            precision: Optional[int] = capability_data["precision"]
            return precision
        return None

    @property
    def options(self) -> Optional[list[str]]:
        """Return the list of possible states for ENUM sensors."""
        # Only provide options for string-valued sensors (ENUM device class)
        if self.device_class == SensorDeviceClass.ENUM:
            capability_name = self._capability_name.lower()

            # Check if API provides availableValues for this ENUM
            capability_data = self.capability_data
            if capability_data and "availableValues" in capability_data:
                # Use API-provided values and apply title case formatting
                available_values = capability_data.get("availableValues", [])
                if isinstance(available_values, list) and available_values:
                    return [str(val).title() for val in available_values]

            # Define known options for specific capabilities (in title case to match native_value)
            if "connectivity" in capability_name and ("cellular" in capability_name or "wifi" in capability_name):
                return ["Connected", "Disconnected", "Poor", "Fair", "Good", "Excellent", "Unknown"]
            elif "connector.status" in capability_name or "plug" in capability_name:
                return ["Connected", "Disconnected", "Unknown"]
            elif "charging.status" in capability_name or "charging_status" in capability_name:
                return ["Idle", "Charging", "Complete", "Error", "Unknown"]
            elif "status" in capability_name:
                return ["Idle", "Active", "Error", "Unknown"]

            # For unknown ENUM sensors, we can't predict options
            # Home Assistant will accept any string value
            return None
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


class TibberDataAttributeSensor(TibberDataAttributeEntity, SensorEntity):
    """Sensor entity for non-boolean device attributes."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        attribute_path: str,
        attribute_name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, device_id, attribute_path, attribute_name)

        # Set entity description based on attribute type
        self.entity_description = self._get_entity_description(attribute_path, attribute_name)

    def _get_entity_description(
        self,
        attribute_path: str,
        attribute_name: str
    ) -> SensorEntityDescription:
        """Get entity description for attribute."""
        # Get mapping configuration
        mapping = ATTRIBUTE_MAPPINGS.get(attribute_path, {})

        # Get attribute data to determine type
        attribute_data = self.attribute_data
        value = attribute_data.get("value") if attribute_data else None

        # Determine device class
        device_class: Optional[SensorDeviceClass] = None
        device_class_str = mapping.get("device_class")
        if device_class_str:
            try:
                device_class = SensorDeviceClass(device_class_str)
            except ValueError:
                device_class = self._infer_device_class_from_attribute(attribute_path, value)
        else:
            device_class = self._infer_device_class_from_attribute(attribute_path, value)

        # String values should not have state_class
        state_class = None if isinstance(value, str) else SensorStateClass.MEASUREMENT

        return SensorEntityDescription(
            key=attribute_path,
            name=None,  # Let the entity's name property handle the full name
            device_class=device_class,
            state_class=state_class,
            icon=mapping.get("icon"),
        )

    def _infer_device_class_from_attribute(
        self,
        attribute_path: str,
        value: Any
    ) -> Optional[SensorDeviceClass]:
        """Infer device class from attribute path and value."""
        # String values should use ENUM device class
        if isinstance(value, str):
            return SensorDeviceClass.ENUM

        path_lower = attribute_path.lower()

        # Check for known attribute patterns
        if "vin" in path_lower or "serial" in path_lower or "id" in path_lower:
            return None  # No specific device class for identifiers
        elif "version" in path_lower or "firmware" in path_lower:
            return None  # No specific device class for version strings

        return None

    @property
    def native_value(self) -> Optional[str | int | float]:
        """Return the state of the sensor."""
        attribute_data = self.attribute_data
        if not attribute_data:
            return None

        value = attribute_data.get("value")

        # String values are returned as-is (no title case for attributes)
        return value

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the entity category."""
        # Check mapping configuration first
        mapping = ATTRIBUTE_MAPPINGS.get(self._attribute_path, {})
        if "entity_category" in mapping:
            entity_cat_str = mapping["entity_category"]
            try:
                return EntityCategory(entity_cat_str)
            except ValueError:
                pass

        # Get attribute data to check if diagnostic
        attribute_data = self.attribute_data
        if attribute_data and attribute_data.get("is_diagnostic", False):
            return EntityCategory.DIAGNOSTIC
        return None

    @property
    def icon(self) -> Optional[str]:
        """Return the icon for the entity."""
        # Check if entity description has an icon
        if hasattr(self.entity_description, 'icon') and self.entity_description.icon:
            return self.entity_description.icon

        # Dynamic icons based on attribute path
        attribute_path = self._attribute_path.lower()

        if "vin" in attribute_path or "serial" in attribute_path:
            return "mdi:identifier"
        elif "version" in attribute_path or "firmware" in attribute_path:
            return "mdi:information-outline"

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = super().extra_state_attributes

        # Add attribute-specific information
        device_data = self.device_data
        if not device_data:
            return attributes

        return attributes