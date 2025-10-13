"""Base entity classes for Tibber Data integration."""
from __future__ import annotations

from typing import Any, Dict, Optional

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
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
        self._cached_device_data: Optional[Dict[str, Any]] = None
        self._device_cache_coordinator_update: Optional[Any] = None

    @property
    def device_data(self) -> Optional[Dict[str, Any]]:
        """Get device data from coordinator with caching.

        Returns cached device data to avoid repeated lookups during state updates.
        Cache is tied to coordinator data object identity, and maintains previous
        data if new data is temporarily unavailable during coordinator transitions.
        """
        coordinator_data = self.coordinator.data

        # If no coordinator data, return previous cache to maintain availability
        if not coordinator_data:
            return self._cached_device_data

        # Check if cache is valid for current coordinator data (use data object id as cache key)
        current_data_id = id(coordinator_data)
        if self._device_cache_coordinator_update == current_data_id:
            return self._cached_device_data

        # Cache miss - fetch and cache the data
        if "devices" not in coordinator_data:
            # Keep previous cache if structure is invalid, but mark this data as seen
            # so we don't keep checking on every property access
            if self._cached_device_data is not None:
                self._device_cache_coordinator_update = current_data_id
        else:
            new_device_data = coordinator_data["devices"].get(self._device_id)
            if new_device_data is not None:
                # Update cache with new valid data and mark as current
                self._cached_device_data = new_device_data
                self._device_cache_coordinator_update = current_data_id
            else:
                # Device not found in new data
                # If we have cached data, mark current data as seen but keep old cache
                # This prevents returning None when device temporarily missing from coordinator
                if self._cached_device_data is not None:
                    self._device_cache_coordinator_update = current_data_id
                # If no cache exists, don't mark as seen - keep trying on next access

        return self._cached_device_data

    @property
    def home_data(self) -> Optional[Dict[str, Any]]:
        """Get home data for this device."""
        device_data = self.device_data
        if not device_data:
            return None

        home_id = device_data.get("home_id")
        if not home_id or not self.coordinator.data or "homes" not in self.coordinator.data:
            return None

        home_data: Optional[Dict[str, Any]] = self.coordinator.data["homes"].get(home_id)
        return home_data

    @property
    def available(self) -> bool:
        """Return True if entity is available.

        Entity is available if:
        1. We have device data (from coordinator or cache), AND
        2. Device is online according to the last known state, AND
        3. Either coordinator's last update was successful OR we have cached data

        This ensures entities don't become unavailable:
        - During coordinator updates (we check cached data)
        - After restart (if coordinator has data, entities are available)
        - During transient failures (cached data keeps entities available)
        """
        device_data = self.device_data
        if not device_data:
            return False

        # Entity is available if device is online according to last known state
        online_status: bool = device_data.get("online", False)
        if not online_status:
            return False

        # If we have device data and device is online, entity is available
        # We trust the data we have (either fresh from coordinator or cached)
        # This prevents unavailability during coordinator transitions and after restarts
        return True

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

        # Get device name using our helper logic
        device_name = self._get_device_display_name(device_data)

        # Link device to its home hub
        home_id = device_data.get("home_id")

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_name,
            manufacturer=device_data.get("manufacturer", MANUFACTURER),
            model=device_data.get("model", "Unknown"),
            sw_version=self._get_firmware_version(),
            suggested_area=suggested_area,
            configuration_url="https://data-api.tibber.com/clients/manage",
            connections=self._get_device_connections(),
        )

        # Only add via_device if we have a home_id
        if home_id:
            device_info["via_device"] = (DOMAIN, f"home_{home_id}")

        return device_info

    def _get_firmware_version(self) -> Optional[str]:
        """Extract firmware version from device attributes."""
        device_data = self.device_data
        if not device_data or "attributes" not in device_data:
            return None

        # Look for firmware version in attributes
        for attr in device_data["attributes"]:
            if attr.get("name") == "firmware.version":
                version: Optional[str] = attr.get("value")
                return version

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
        # Enable all entities by default
        # The available property will handle runtime availability
        return True

    def _get_capability_data(self, capability_name: str) -> Optional[Dict[str, Any]]:
        """Get capability data by name."""
        device_data = self.device_data
        if not device_data or "capabilities" not in device_data:
            return None

        for capability in device_data["capabilities"]:
            if capability.get("name") == capability_name:
                capability_data: Optional[Dict[str, Any]] = capability
                return capability_data

        return None

    def _get_attribute_data(self, attribute_path: str) -> Optional[Dict[str, Any]]:
        """Get attribute data by path."""
        device_data = self.device_data
        if not device_data or "attributes" not in device_data:
            return None

        for attribute in device_data["attributes"]:
            if attribute.get("name") == attribute_path:
                attribute_data: Optional[Dict[str, Any]] = attribute
                return attribute_data

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

    def _get_device_display_name(self, device_data: Dict[str, Any]) -> str:
        """Get display name for device with fallback logic."""
        device_name = device_data.get("name") or ""
        device_name = device_name.strip() if device_name else ""

        # Check if device name is invalid (empty, whitespace, or variations of "no name")
        # Handle case-insensitive variations: "no name", "No name", "<no name>", etc.
        device_name_lower = device_name.lower()
        is_invalid_name = (
            not device_name or
            device_name_lower == "no name" or
            device_name_lower == "<no name>" or
            device_name_lower.strip("<>") == "no name"
        )

        if is_invalid_name:
            manufacturer = device_data.get("manufacturer", "Unknown")
            model = device_data.get("model", "Device")
            # Build a cleaner device name
            if manufacturer and manufacturer != "Unknown" and model and model != "Device":
                device_name = f"{manufacturer} {model}"
            elif model and model != "Device":
                device_name = model
            elif manufacturer and manufacturer != "Unknown":
                device_name = manufacturer
            else:
                # Last resort: use device ID prefix
                device_id = device_data.get("id", "unknown")
                device_name = f"Device {device_id[:8]}"

        return device_name

    def _get_device_slug(self) -> str:
        """Get a clean slug for the device to use in entity_id."""
        device_data = self.device_data
        if not device_data:
            return "unknown_device"

        # Get the device display name
        device_name = self._get_device_display_name(device_data)

        # Convert to lowercase and replace spaces/special chars with underscores
        import re
        slug = device_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '_', slug)
        slug = slug.strip('_')

        return slug or "unknown_device"

    def _slugify_capability_name(self, name: str) -> str:
        """Convert capability name to proper snake_case slug.

        Handles camelCase, PascalCase, and existing snake_case.
        Also handles common compound words like 'isonline' -> 'is_online'.

        Examples:
            availableEnergy -> available_energy
            storage_availableEnergy -> storage_available_energy
            battery_level -> battery_level
            isonline -> is_online
        """
        import re

        # First handle common compound words that should be split
        # This is a list of common prefixes/patterns in lowercase
        compound_patterns = [
            (r'\bisonline\b', 'is_online'),
            (r'\bisoffline\b', 'is_offline'),
            (r'\bisconnected\b', 'is_connected'),
            (r'\bhaserror\b', 'has_error'),
            (r'\bcancharge\b', 'can_charge'),
        ]

        name_lower = name.lower()
        for pattern, replacement in compound_patterns:
            name_lower = re.sub(pattern, replacement, name_lower)

        # If we made replacements, use the modified version
        if name_lower != name.lower():
            name = name_lower

        # Insert underscore before capital letters (camelCase to snake_case)
        name = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
        # Convert to lowercase
        name = name.lower()
        # Replace any remaining non-alphanumeric chars with underscore
        name = re.sub(r'[^a-z0-9]+', '_', name)
        # Remove duplicate underscores
        name = re.sub(r'_+', '_', name)
        # Strip leading/trailing underscores
        name = name.strip('_')
        return name


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
        """Return entity name (display name without Tibber prefix)."""
        device_data = self.device_data
        if not device_data:
            return f"Unknown Device {self._entity_name_suffix}"

        device_name = self._get_device_display_name(device_data)
        return f"{device_name} {self._entity_name_suffix}"

    @property
    def unique_id(self) -> str:
        """Return unique ID for entity."""
        # Use device ID and entity suffix to create unique ID
        suffix_clean = self._entity_name_suffix.lower().replace(" ", "_")
        return f"tibber_data_{self._device_id}_{suffix_clean}"

    @property
    def suggested_object_id(self) -> str:
        """Return suggested object_id (entity_id without domain)."""
        device_slug = self._get_device_slug()
        # Apply slugification to handle any special characters or camelCase
        suffix_slug = self._slugify_capability_name(self._entity_name_suffix)
        return f"tibber_data_{device_slug}_{suffix_slug}"


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
        self._cached_capability_data: Optional[Dict[str, Any]] = None
        self._cache_coordinator_update: Optional[Any] = None
        super().__init__(coordinator, device_id, capability_name)

    @property
    def capability_data(self) -> Optional[Dict[str, Any]]:
        """Get capability data with caching per coordinator update.

        Maintains cached data during coordinator transitions to prevent
        flickering unavailability during updates.
        """
        coordinator_data = self.coordinator.data

        # If no coordinator data, return previous cache
        if not coordinator_data:
            return self._cached_capability_data

        # Check if cache is valid for current coordinator data (use data object id as cache key)
        current_data_id = id(coordinator_data)
        if self._cache_coordinator_update == current_data_id:
            return self._cached_capability_data

        # Cache miss - fetch and cache the data
        new_capability_data = self._get_capability_data(self._capability_name)
        if new_capability_data is not None:
            # Update cache with new valid data and mark as current
            self._cached_capability_data = new_capability_data
            self._cache_coordinator_update = current_data_id
        else:
            # Capability not found in new data
            # If we have cached data, mark current data as seen but keep old cache
            # This prevents returning None when capability temporarily missing
            if self._cached_capability_data is not None:
                self._cache_coordinator_update = current_data_id
            # If no cache exists, don't mark as seen - keep trying on next access

        return self._cached_capability_data

    @property
    def name(self) -> str:
        """Return entity name (display name without Tibber prefix)."""
        device_data = self.device_data
        if not device_data:
            return f"Unknown Device {self._capability_name.replace('_', ' ').title()}"

        device_name = self._get_device_display_name(device_data)
        capability_display_name = self._get_capability_display_name()

        # Check for duplicate displayNames and add prefix if needed
        if self._has_duplicate_display_name():
            prefix = self._capability_name.split(".")[0].title()
            return f"{device_name} {prefix} {capability_display_name}"

        return f"{device_name} {capability_display_name}"

    def _get_capability_display_name(self) -> str:
        """Get the display name for this capability.

        Priority order:
        1. Custom mapping from CAPABILITY_MAPPINGS
        2. Dynamic formatting for energyFlow capabilities
        3. API's displayName field
        4. Formatted capability name
        """
        from .const import CAPABILITY_MAPPINGS

        mapping = CAPABILITY_MAPPINGS.get(self._capability_name, {})
        if "display_name" in mapping:
            return mapping["display_name"]

        if "energyflow" in self._capability_name.lower():
            return self._format_energy_flow_name(self._capability_name)

        capability_data = self.capability_data
        if capability_data and "displayName" in capability_data:
            return capability_data["displayName"]

        return self._capability_name.replace("_", " ").title()

    def _has_duplicate_display_name(self) -> bool:
        """Check if other capabilities on this device have the same displayName."""
        capability_data = self.capability_data
        device_data = self.device_data

        # Only check for API displayName conflicts (not custom names)
        if not capability_data or "displayName" not in capability_data or not device_data:
            return False

        # Only applies to capabilities with dot notation (e.g., battery.level)
        if "." not in self._capability_name:
            return False

        display_name = capability_data["displayName"]
        all_capabilities = device_data.get("capabilities", [])

        # Check if any other capability shares this displayName
        return any(
            cap.get("displayName") == display_name
            and cap.get("name") != self._capability_name
            for cap in all_capabilities
        )

    @property
    def unique_id(self) -> str:
        """Return unique ID for capability entity."""
        return f"tibber_data_{self._device_id}_{self._capability_name}"

    @property
    def suggested_object_id(self) -> str:
        """Return suggested object_id (entity_id without domain).

        Uses the formatted display name to ensure consistency with Home Assistant's
        auto-generated entity_id suggestions when recreating entities.
        """
        device_slug = self._get_device_slug()
        # Use the formatted display name instead of raw capability name
        # This ensures entity_id matches what HA would suggest from the name
        capability_display = self._get_capability_display_name()
        capability_slug = self._slugify_capability_name(capability_display)
        return f"tibber_data_{device_slug}_{capability_slug}"

    @property
    def available(self) -> bool:
        """Return True if capability is available.

        Entity is available if:
        1. Device is available (online and has device data), AND
        2. We have capability data (either fresh or cached)

        This allows entities to remain available with cached data when capabilities
        are temporarily missing from API responses (e.g., at hour boundaries).

        Note: The capability_data property returns cached data if the capability
        is temporarily missing, so this check will keep entities available as long
        as they once had valid data.
        """
        if not super().available:
            return False

        # Entity is available if we have capability data (fresh or cached)
        return self.capability_data is not None

    @property
    def entity_category(self) -> Optional[EntityCategory]:
        """Return the entity category for diagnostic capabilities."""
        capability_name_lower = self._capability_name.lower()

        # Primary operational metrics should NOT be diagnostic
        # Charging current/voltage are operational metrics for EV chargers
        operational_keywords = ["charging", "charge"]
        if any(keyword in capability_name_lower for keyword in operational_keywords):
            return None

        # Capabilities that are considered diagnostic (technical/troubleshooting info)
        diagnostic_keywords = [
            "signal", "rssi", "wifi", "lqi", "snr",  # Connectivity metrics
            "voltage", "current", "frequency",  # Electrical diagnostics (only if not charging-related)
            "firmware", "version", "update",  # Software info
            "uptime", "runtime", "cycles",  # Usage stats
            "error", "warning", "status_code",  # Error tracking
        ]

        # Check if capability name contains diagnostic keywords
        if any(keyword in capability_name_lower for keyword in diagnostic_keywords):
            return EntityCategory.DIAGNOSTIC

        return None

    def _format_energy_flow_name(self, capability_name: str) -> str:
        """Format energy flow capability names dynamically.

        Handles both formats:
        - {destination}.energyFlow.{period}.{action/source}
        - energyFlow.{period}.{destination}.{action/source}
        """
        parts = capability_name.split(".")

        # Parse components
        destination: Optional[str] = None
        source: Optional[str] = None
        time_period: Optional[str] = None
        action: Optional[str] = None
        metric_type: Optional[str] = None  # Additional metric type (e.g., total, net, available)

        destinations = {"load", "grid", "solar", "battery"}
        periods = {"hour", "day", "week", "month", "year", "minute"}
        actions = {"charged", "discharged", "produced", "consumed", "imported", "exported", "generated"}
        metric_types = {"total", "net", "available", "stored", "capacity", "remaining"}

        # Track if we're in a "source" section (e.g., "source.grid")
        found_source_keyword = False

        for i, part in enumerate(parts):
            part_lower = part.lower()

            if part_lower in destinations and not destination:
                destination = part.title()
            elif part_lower == "source":
                # Mark that we found "source", next destination part is the source
                found_source_keyword = True
            elif found_source_keyword and part_lower in destinations:
                # This is the source destination (e.g., "grid" in "source.grid")
                source = part.title()
                found_source_keyword = False
            elif part_lower.startswith("source") and len(part_lower) > 6:
                # Handle "sourceGrid" format (without dot)
                source = part[6:].title()
            elif part_lower in periods:
                time_period = part.title()
            elif part_lower in actions:
                action = part.title()
            elif part_lower in metric_types:
                metric_type = part.title()

        # Fallback if no destination found
        if not destination:
            return capability_name.replace(".", " ").replace("_", " ").title()

        # Define naming rules per destination
        naming_rules: Dict[str, Dict[str, Any]] = {
            "Battery": {
                "action": lambda a: f"Battery {a}",
                "source_Battery": "Battery Self-Charge",
                "source": lambda s: f"Battery from {s}",
                "metric": lambda m: f"Battery {m}",
                "default": "Battery Energy"
            },
            "Grid": {
                "source_Grid": "Grid Import",
                "source": lambda s: f"Grid from {s}",
                "metric": lambda m: f"Grid {m}",
                "default": "Grid Energy"
            },
            "Load": {
                "source": lambda s: f"Load from {s}",
                "metric": lambda m: f"Load {m}",
                "default": "Load Energy"
            },
            "Solar": {
                "action": lambda a: f"Solar {a}",
                "source_Solar": "Solar Production",
                "source": lambda s: f"Solar from {s}",
                "metric": lambda m: f"Solar {m}",
                "default": "Solar Energy"
            }
        }

        # Get naming rule for this destination
        rules = naming_rules.get(destination, {})

        # Apply naming rules in priority order
        display_name: str
        if action:
            action_func = rules.get("action", lambda a: f"{destination} {a}")
            display_name = action_func(action)
        elif source:
            # Check for specific source match (e.g., "source_Battery")
            source_key = f"source_{source}"
            if source_key in rules:
                display_name = str(rules[source_key])
            else:
                source_func = rules.get("source", lambda s: f"{destination} from {s}")
                display_name = source_func(source)
        elif metric_type:
            metric_func = rules.get("metric", lambda m: f"{destination} {m}")
            display_name = metric_func(metric_type)
        else:
            # If no action, source, or metric_type, use the full capability path for uniqueness
            # Example: battery.energyFlow.day.foo -> "Battery Foo"
            # Look for any remaining unrecognized parts
            unrecognized_parts = [
                p.title() for p in parts
                if p.lower() not in destinations
                and p.lower() not in periods
                and not p.lower().startswith("source")
                and "energy" not in p.lower()
                and "flow" not in p.lower()
            ]

            if unrecognized_parts:
                display_name = f"{destination} {' '.join(unrecognized_parts)}"
            else:
                display_name = str(rules.get("default", f"{destination} Energy"))

        # Add time period suffix if present
        if time_period:
            display_name = f"{display_name} ({time_period})"

        return display_name

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
        self._cached_attribute_data: Optional[Dict[str, Any]] = None
        self._attribute_cache_coordinator_update: Optional[Any] = None
        super().__init__(coordinator, device_id, attribute_name)

    @property
    def attribute_data(self) -> Optional[Dict[str, Any]]:
        """Get attribute data with caching per coordinator update.

        Maintains cached data during coordinator transitions to prevent
        flickering unavailability during updates.
        """
        coordinator_data = self.coordinator.data

        # If no coordinator data, return previous cache
        if not coordinator_data:
            return self._cached_attribute_data

        # Check if cache is valid for current coordinator data (use data object id as cache key)
        current_data_id = id(coordinator_data)
        if self._attribute_cache_coordinator_update == current_data_id:
            return self._cached_attribute_data

        # Cache miss - fetch and cache the data
        new_attribute_data = self._get_attribute_data(self._attribute_path)
        if new_attribute_data is not None:
            # Update cache with new valid data and mark as current
            self._cached_attribute_data = new_attribute_data
            self._attribute_cache_coordinator_update = current_data_id
        else:
            # Attribute not found in new data
            # If we have cached data, mark current data as seen but keep old cache
            # This prevents returning None when attribute temporarily missing
            if self._cached_attribute_data is not None:
                self._attribute_cache_coordinator_update = current_data_id
            # If no cache exists, don't mark as seen - keep trying on next access

        return self._cached_attribute_data

    @property
    def unique_id(self) -> str:
        """Return unique ID for attribute entity."""
        path_clean = self._attribute_path.replace(".", "_")
        return f"tibber_data_{self._device_id}_{path_clean}"

    @property
    def suggested_object_id(self) -> str:
        """Return suggested object_id (entity_id without domain).

        Uses the attribute name (display name) to ensure consistency with Home Assistant's
        auto-generated entity_id suggestions when recreating entities.
        """
        device_slug = self._get_device_slug()
        # Use the attribute name (display name) instead of raw attribute path
        # This ensures entity_id matches what HA would suggest from the name
        # _entity_name_suffix contains the attribute_name passed to constructor
        attribute_slug = self._slugify_capability_name(self._entity_name_suffix)
        return f"tibber_data_{device_slug}_{attribute_slug}"

    @property
    def available(self) -> bool:
        """Return True if attribute is available."""
        # Attributes like connectivity are always reportable
        # even for offline devices (they report the offline status)
        device_data = self.device_data
        return device_data is not None

    @property
    def entity_category(self) -> Optional[EntityCategory]:
        """Return the entity category for diagnostic attributes."""
        attribute_data = self.attribute_data
        if attribute_data and attribute_data.get("isDiagnostic", False):
            return EntityCategory.DIAGNOSTIC
        return None

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
        attributes["last_seen"] = device_data.get("lastSeen")

        return attributes