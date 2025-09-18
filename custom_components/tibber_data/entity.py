"""Base entity classes for Tibber Data integration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import TibberDataUpdateCoordinator


class TibberDataEntity(CoordinatorEntity[TibberDataUpdateCoordinator]):
    """Base class for Tibber Data entities."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        entity_name_suffix: str
    ) -> None:
        """Initialize base Tibber Data entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._entity_name_suffix = entity_name_suffix

    @property
    def device_data(self) -> Optional[Dict[str, Any]]:
        """Get device data from coordinator."""
        if not self.coordinator.data or "devices" not in self.coordinator.data:
            return None
        return self.coordinator.data["devices"].get(self._device_id)

    @property
    def home_data(self) -> Optional[Dict[str, Any]]:
        """Get home data for this device."""
        device_data = self.device_data
        if not device_data:
            return None

        home_id = device_data.get("home_id")
        if not home_id or not self.coordinator.data or "homes" not in self.coordinator.data:
            return None

        return self.coordinator.data["homes"].get(home_id)

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        device_data = self.device_data
        if not device_data:
            return False

        # Entity is available if device is online
        return device_data.get("online", False)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for device registry."""
        device_data = self.device_data
        if not device_data:
            # Return minimal device info for missing devices
            return DeviceInfo(
                identifiers={(DOMAIN, self._device_id)},
                name=f"Unknown Device ({self._device_id})",
                manufacturer=MANUFACTURER,
                model="Unknown"
            )

        # Get home information for area assignment
        home_data = self.home_data
        suggested_area = home_data.get("displayName") if home_data else None

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_data.get("name", f"Tibber Device {self._device_id}"),
            manufacturer=device_data.get("manufacturer", MANUFACTURER),
            model=device_data.get("model", device_data.get("type", "Unknown")),
            sw_version=self._get_firmware_version(),
            suggested_area=suggested_area,
            configuration_url="https://developer.tibber.com/",
            connections=self._get_device_connections()
        )

    def _get_firmware_version(self) -> Optional[str]:
        """Extract firmware version from device attributes."""
        device_data = self.device_data
        if not device_data or "attributes" not in device_data:
            return None

        # Look for firmware version in attributes
        for attr in device_data["attributes"]:
            if attr.get("name") == "firmware.version":
                return attr.get("value")

        return None

    def _get_device_connections(self) -> set[tuple[str, str]]:
        """Get device connections for device registry."""
        device_data = self.device_data
        if not device_data:
            return set()

        connections = set()

        # Add external ID as a connection if available
        if external_id := device_data.get("external_id"):
            connections.add(("tibber_external_id", external_id))

        return connections

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added."""
        # Enable entities by default for online devices
        return self.available

    def _get_capability_data(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Get capability data by name."""
        device_data = self.device_data
        if not device_data or "capabilities" not in device_data:
            return None

        for capability in device_data["capabilities"]:
            if capability.get("name") == capability_name:
                return capability

        return None

    def _get_attribute_data(self, attribute_path: str) -> Optional[Dict[str, Any]]:
        """Get attribute data by path."""
        device_data = self.device_data
        if not device_data or "attributes" not in device_data:
            return None

        for attribute in device_data["attributes"]:
            if attribute.get("name") == attribute_path:
                return attribute

        return None

    def _get_nested_attribute_value(
        self,
        attributes: Dict[str, Any],
        path: str
    ) -> Any:
        """Get value from nested attribute path (e.g., 'connectivity.online')."""
        keys = path.split(".")
        value = attributes

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value


class TibberDataDeviceEntity(TibberDataEntity):
    """Base class for device-level Tibber Data entities."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        entity_name_suffix: str
    ) -> None:
        """Initialize device entity."""
        super().__init__(coordinator, device_id, entity_name_suffix)

    @property
    def name(self) -> str:
        """Return entity name."""
        device_data = self.device_data
        if not device_data:
            return f"Unknown Device {self._entity_name_suffix}"

        device_name = device_data.get("name", f"Device {self._device_id}")
        return f"{device_name} {self._entity_name_suffix}"

    @property
    def unique_id(self) -> str:
        """Return unique ID for entity."""
        # Use device ID and entity suffix to create unique ID
        suffix_clean = self._entity_name_suffix.lower().replace(" ", "_")
        return f"tibber_data_{self._device_id}_{suffix_clean}"


class TibberDataCapabilityEntity(TibberDataDeviceEntity):
    """Base class for device capability entities (sensors)."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        capability_name: str
    ) -> None:
        """Initialize capability entity."""
        self._capability_name = capability_name
        super().__init__(coordinator, device_id, capability_name)

    @property
    def capability_data(self) -> Optional[Dict[str, Any]]:
        """Get capability data."""
        return self._get_capability_data(self._capability_name)

    @property
    def name(self) -> str:
        """Return entity name."""
        capability_data = self.capability_data
        device_data = self.device_data

        if not device_data:
            return f"Unknown Device {self._capability_name}"

        device_name = device_data.get("name", f"Device {self._device_id}")

        if capability_data and "displayName" in capability_data:
            capability_display_name = capability_data["displayName"]
        else:
            # Fallback to formatted capability name
            capability_display_name = self._capability_name.replace("_", " ").title()

        return f"{device_name} {capability_display_name}"

    @property
    def unique_id(self) -> str:
        """Return unique ID for capability entity."""
        return f"tibber_data_{self._device_id}_{self._capability_name}"

    @property
    def available(self) -> bool:
        """Return True if capability is available."""
        if not super().available:
            return False

        # Capability is available if it has data
        return self.capability_data is not None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        capability_data = self.capability_data
        if not capability_data:
            return {}

        attributes = {}

        # Add capability metadata
        if "lastUpdated" in capability_data:
            attributes["last_updated"] = capability_data["lastUpdated"]

        if "minValue" in capability_data:
            attributes["min_value"] = capability_data["minValue"]

        if "maxValue" in capability_data:
            attributes["max_value"] = capability_data["maxValue"]

        if "precision" in capability_data:
            attributes["precision"] = capability_data["precision"]

        # Add device information
        device_data = self.device_data
        if device_data:
            attributes["device_type"] = device_data.get("type")
            attributes["device_online"] = device_data.get("online")

        return attributes


class TibberDataAttributeEntity(TibberDataDeviceEntity):
    """Base class for device attribute entities (binary sensors)."""

    def __init__(
        self,
        coordinator: TibberDataUpdateCoordinator,
        device_id: str,
        attribute_path: str,
        attribute_name: str
    ) -> None:
        """Initialize attribute entity."""
        self._attribute_path = attribute_path
        super().__init__(coordinator, device_id, attribute_name)

    @property
    def attribute_data(self) -> Optional[Dict[str, Any]]:
        """Get attribute data."""
        return self._get_attribute_data(self._attribute_path)

    @property
    def unique_id(self) -> str:
        """Return unique ID for attribute entity."""
        path_clean = self._attribute_path.replace(".", "_")
        return f"tibber_data_{self._device_id}_{path_clean}"

    @property
    def available(self) -> bool:
        """Return True if attribute is available."""
        # Attributes like connectivity are always reportable
        # even for offline devices (they report the offline status)
        device_data = self.device_data
        return device_data is not None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes: Dict[str, Any] = {}
        device_data = self.device_data

        if not device_data:
            return attributes

        # Add contextual information based on attribute type
        if self._attribute_path.startswith("connectivity"):
            # Add connectivity-related attributes
            for attr in device_data.get("attributes", []):
                if attr.get("name", "").startswith("connectivity"):
                    attr_name = attr["name"].split(".")[-1]  # Get last part of path
                    if attr_name != self._attribute_path.split(".")[-1]:  # Don't duplicate the main attribute
                        key = attr_name.replace("_", " ").lower()
                        attributes[key] = attr.get("value")

        elif self._attribute_path.startswith("firmware"):
            # Add firmware-related attributes
            for attr in device_data.get("attributes", []):
                if attr.get("name", "").startswith("firmware"):
                    attr_name = attr["name"].split(".")[-1]
                    if attr_name != self._attribute_path.split(".")[-1]:
                        key = attr_name.replace("_", " ").lower()
                        attributes[key] = attr.get("value")

        # Add device information
        attributes["device_type"] = device_data.get("type")
        attributes["last_seen"] = device_data.get("lastSeen")

        return attributes