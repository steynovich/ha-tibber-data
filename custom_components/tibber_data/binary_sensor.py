"""Binary sensor platform for Tibber Data integration."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DATA_COORDINATOR, ATTRIBUTE_MAPPINGS
from .coordinator import TibberDataUpdateCoordinator
from .entity import TibberDataAttributeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tibber Data binary sensor entities."""
    coordinator: TibberDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][DATA_COORDINATOR]

    entities: List[TibberDataAttributeBinarySensor] = []

    if coordinator.data and "devices" in coordinator.data:
        for device_id, device_data in coordinator.data["devices"].items():
            # Create binary sensor entities for boolean device attributes
            for attribute in device_data.get("attributes", []):
                attribute_path = attribute["name"]
                attribute_value = attribute.get("value")

                # Only create binary sensors for boolean attributes
                if isinstance(attribute_value, bool):
                    # Get display name from mapping or generate one
                    mapping = ATTRIBUTE_MAPPINGS.get(attribute_path, {})
                    display_name = mapping.get("name_suffix", attribute_path.split(".")[-1].replace("_", " ").title())

                    entities.append(
                        TibberDataAttributeBinarySensor(
                            coordinator=coordinator,
                            device_id=device_id,
                            attribute_path=attribute_path,
                            attribute_name=display_name
                        )
                    )

    if entities:
        async_add_entities(entities, True)
        _LOGGER.debug("Added %d binary sensor entities", len(entities))


class TibberDataAttributeBinarySensor(TibberDataAttributeEntity, BinarySensorEntity):
    """Binary sensor entity for device attributes."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        attribute_path: str,
        attribute_name: str
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, device_id, attribute_path, attribute_name)

        # Set entity description based on attribute type
        self.entity_description = self._get_entity_description(attribute_path, attribute_name)

    def _get_entity_description(
        self,
        attribute_path: str,
        attribute_name: str
    ) -> BinarySensorEntityDescription:
        """Get entity description for attribute."""
        # Get mapping configuration
        mapping = ATTRIBUTE_MAPPINGS.get(attribute_path, {})

        # Determine device class based on mapping or attribute path
        device_class = mapping.get("device_class")
        if not device_class:
            device_class = self._infer_device_class_from_path(attribute_path)

        return BinarySensorEntityDescription(
            key=attribute_path,
            name=attribute_name,
            device_class=device_class,
            icon=mapping.get("icon"),
        )

    def _infer_device_class_from_path(self, attribute_path: str) -> Optional[BinarySensorDeviceClass]:
        """Infer device class from attribute path."""
        path_lower = attribute_path.lower()

        if "connectivity" in path_lower and "online" in path_lower:
            return BinarySensorDeviceClass.CONNECTIVITY
        elif "update" in path_lower or "available" in path_lower:
            return BinarySensorDeviceClass.UPDATE
        elif "charging" in path_lower:
            return BinarySensorDeviceClass.BATTERY_CHARGING
        elif "error" in path_lower or "problem" in path_lower:
            return BinarySensorDeviceClass.PROBLEM
        elif "running" in path_lower or "active" in path_lower:
            return BinarySensorDeviceClass.RUNNING
        elif "power" in path_lower:
            return BinarySensorDeviceClass.POWER

        return None

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        attribute_data = self.attribute_data
        if not attribute_data:
            return None

        value = attribute_data.get("value")
        if isinstance(value, bool):
            return value

        # Handle string boolean values
        if isinstance(value, str):
            return value.lower() in ("true", "1", "on", "yes", "enabled")

        # Handle numeric boolean values
        if isinstance(value, (int, float)):
            return bool(value)

        return None

    @property
    def icon(self) -> Optional[str]:
        """Return the icon for the entity."""
        # Check if entity description has an icon
        if hasattr(self.entity_description, 'icon') and self.entity_description.icon:
            return self.entity_description.icon

        # Dynamic icons based on attribute and state
        attribute_path = self._attribute_path.lower()
        is_on = self.is_on

        if "connectivity" in attribute_path and "online" in attribute_path:
            return "mdi:wifi" if is_on else "mdi:wifi-off"
        elif "update" in attribute_path:
            return "mdi:update" if is_on else "mdi:update-lock"
        elif "charging" in attribute_path:
            return "mdi:battery-charging" if is_on else "mdi:battery"
        elif "error" in attribute_path or "problem" in attribute_path:
            return "mdi:alert-circle" if is_on else "mdi:check-circle"
        elif "power" in attribute_path:
            return "mdi:power" if is_on else "mdi:power-off"
        elif "running" in attribute_path or "active" in attribute_path:
            return "mdi:play" if is_on else "mdi:pause"

        return None

    def _get_nested_attribute_value(
        self,
        attributes: Dict[str, Any],
        path: str
    ) -> Any:
        """Get value from nested attribute path (e.g., 'connectivity.online')."""
        # This method is used by the parent class to extract nested values
        # For device attributes, we need to look in the attributes list
        device_data = self.device_data
        if not device_data or "attributes" not in device_data:
            return None

        for attribute in device_data["attributes"]:
            if attribute.get("name") == path:
                return attribute.get("value")

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = super().extra_state_attributes

        # Add attribute-specific information
        device_data = self.device_data
        if not device_data:
            return attributes

        # Add contextual information based on attribute type
        if self._attribute_path.startswith("connectivity"):
            # Add connectivity-related attributes
            for attr in device_data.get("attributes", []):
                if attr.get("name", "").startswith("connectivity"):
                    attr_name_parts = attr["name"].split(".")
                    if len(attr_name_parts) > 1:
                        attr_name = attr_name_parts[-1]  # Get last part of path
                        if attr_name != self._attribute_path.split(".")[-1]:  # Don't duplicate the main attribute
                            key = attr_name.replace("_", " ").lower()
                            attributes[key] = attr.get("value")

        elif self._attribute_path.startswith("firmware"):
            # Add firmware-related attributes
            for attr in device_data.get("attributes", []):
                if attr.get("name", "").startswith("firmware"):
                    attr_name_parts = attr["name"].split(".")
                    if len(attr_name_parts) > 1:
                        attr_name = attr_name_parts[-1]
                        if attr_name != self._attribute_path.split(".")[-1]:
                            key = attr_name.replace("_", " ").lower()
                            attributes[key] = attr.get("value")

        return attributes