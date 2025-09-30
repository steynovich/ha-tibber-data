"""Data models for Tibber Data API integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Self
from uuid import UUID


@dataclass
class TibberOAuthSession:
    """OAuth2 session for accessing Tibber Data API (with refresh tokens)."""

    session_id: str
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: int = 0  # Unix timestamp
    scopes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_refreshed: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate OAuth2 session data."""
        if not self.access_token:
            raise ValueError("Access token is required")
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.token_type != "Bearer":
            raise ValueError("Only Bearer token type is supported")

        # Ensure scopes include required baseline permissions
        required_scopes = {
            "openid",
            "data-api-user-read",
            "data-api-homes-read"
        }
        provided_scopes = set(self.scopes)
        if not required_scopes.issubset(provided_scopes):
            missing = required_scopes - provided_scopes
            raise ValueError(f"Missing required scopes: {missing}")

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at == 0:
            return False
        return datetime.now(timezone.utc).timestamp() >= self.expires_at

    @property
    def needs_refresh(self, threshold_seconds: int = 300) -> bool:
        """Check if token should be refreshed (within threshold of expiry).

        Tibber access tokens last ~1 hour, refresh if within 5 minutes of expiry.
        """
        if self.expires_at == 0:
            return False
        return datetime.now(timezone.utc).timestamp() >= (self.expires_at - threshold_seconds)

    def update_tokens(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600,
        scopes: Optional[List[str]] = None
    ) -> None:
        """Update token information after refresh."""
        self.access_token = access_token
        if refresh_token:  # Refresh tokens might be rotated
            self.refresh_token = refresh_token
        self.expires_at = int(datetime.now(timezone.utc).timestamp() + expires_in)
        self.last_refreshed = datetime.now(timezone.utc)

        if scopes is not None:
            self.scopes = scopes

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        """Create TibberOAuthSession from dictionary data."""
        scopes = data.get("scopes", [])
        if isinstance(scopes, str):
            scopes = scopes.split()

        return cls(
            session_id=data.get("session_id", ""),
            user_id=data["user_id"],
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_at", 0),
            scopes=scopes,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            last_refreshed=datetime.fromisoformat(data["last_refreshed"]) if data.get("last_refreshed") else None
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert TibberOAuthSession to dictionary for storage."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scopes": self.scopes,
            "created_at": self.created_at.isoformat(),
            "last_refreshed": self.last_refreshed.isoformat() if self.last_refreshed else None
        }


@dataclass
class TibberHome:
    """Represents a user's physical location with associated devices."""

    home_id: str
    display_name: str
    time_zone: str
    address: Optional[Dict[str, str]] = None
    device_count: int = 0

    def __post_init__(self) -> None:
        """Validate TibberHome data."""
        if not self.home_id:
            raise ValueError("Home ID is required")

        # Validate UUID format
        try:
            UUID(self.home_id)
        except ValueError:
            raise ValueError("Home ID must be a valid UUID format")

        if not self.display_name:
            raise ValueError("Display name must not be empty")

        if not self.time_zone:
            raise ValueError("Time zone is required")

        # Basic timezone validation (should be IANA format)
        if "/" not in self.time_zone and self.time_zone not in ["UTC", "GMT"]:
            raise ValueError("Time zone must be valid IANA timezone identifier")

    @classmethod
    def from_api_data(cls, data: Dict[str, Any]) -> Self:
        """Create TibberHome from API response data."""
        # According to API spec, name is in info.name
        info = data.get("info", {})
        display_name = info.get("name", "Tibber Home Name")

        return cls(
            home_id=data["id"],
            display_name=display_name,
            time_zone=data.get("timeZone", "UTC"),  # Use UTC as fallback
            address=data.get("address"),
            device_count=data.get("deviceCount", 0)
        )

    @property
    def unique_id(self) -> str:
        """Get unique identifier for Home Assistant."""
        return f"tibber_home_{self.home_id}"


@dataclass
class DeviceCapability:
    """Current state values with units for device functions."""

    capability_id: str
    device_id: str
    name: str
    display_name: str
    value: Union[float, str, bool, int]
    unit: str
    last_updated: datetime
    # Note: According to OpenAPI spec v1.json, capabilities don't have minValue/maxValue/precision

    def __post_init__(self) -> None:
        """Validate DeviceCapability data."""
        if not self.capability_id:
            raise ValueError("Capability ID is required")
        if not self.device_id:
            raise ValueError("Device ID is required")
        if not self.name:
            raise ValueError("Capability name is required")
        if not self.display_name:
            raise ValueError("Display name is required")

        # Note: API spec doesn't provide min/max bounds for validation

        # Validate last_updated is not in the future
        if self.last_updated > datetime.now(timezone.utc):
            raise ValueError("Last updated timestamp cannot be in the future")

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], device_id: str) -> Self:
        """Create DeviceCapability from API response data."""
        # According to OpenAPI spec, capabilities have "id" and "description", not "name" and "displayName"
        capability_name = data.get("id", "unknown_capability")
        capability_id = f"{device_id}_{capability_name}"

        # Handle missing timestamp - use current time as fallback
        last_updated = datetime.now(timezone.utc)
        if "lastUpdated" in data:
            last_updated = datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00"))

        return cls(
            capability_id=capability_id,
            device_id=device_id,
            name=capability_name,
            display_name=data.get("description", capability_name.replace("_", " ").title()),
            value=data["value"],
            unit=data.get("unit", ""),
            last_updated=last_updated
        )

    @property
    def unique_id(self) -> str:
        """Get unique identifier for Home Assistant."""
        return f"tibber_data_{self.device_id}_{self.name}"

    @property
    def formatted_value(self) -> str:
        """Get formatted value as string."""
        return str(self.value)


@dataclass
class DeviceAttribute:
    """Metadata including connectivity status, firmware versions, and identifiers."""

    attribute_id: str
    device_id: str
    name: str
    display_name: str
    value: Union[str, int, float, bool, datetime]
    data_type: str
    last_updated: datetime
    is_diagnostic: bool = False

    def __post_init__(self) -> None:
        """Validate DeviceAttribute data."""
        if not self.attribute_id:
            raise ValueError("Attribute ID is required")
        if not self.device_id:
            raise ValueError("Device ID is required")
        if not self.name:
            raise ValueError("Attribute name is required")
        if not self.display_name:
            raise ValueError("Display name is required")

        # Validate data type
        valid_data_types = {"string", "number", "boolean", "datetime"}
        if self.data_type not in valid_data_types:
            raise ValueError(f"Data type must be one of: {valid_data_types}")

        # Validate value matches data type
        if not self._validate_value_type():
            raise ValueError(f"Value {self.value} does not match data type {self.data_type}")

    def _validate_value_type(self) -> bool:
        """Validate that value matches the specified data type."""
        type_map: dict[str, Union[type, tuple[type, ...]]] = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "datetime": datetime
        }

        expected_type = type_map[self.data_type]
        return isinstance(self.value, expected_type)

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], device_id: str, attribute_id: str) -> Self:
        """Create DeviceAttribute from API response data."""
        # According to OpenAPI spec, attributes have "id" field and various structures based on type
        full_attribute_id = f"{device_id}_{attribute_id.replace('.', '_')}"

        # Handle different attribute types based on the OpenAPI spec
        # Extract value based on attribute type
        value = None
        data_type = "string"

        if "value" in data:
            value = data["value"]
            if isinstance(value, bool):
                data_type = "boolean"
            elif isinstance(value, (int, float)):
                data_type = "number"
            elif isinstance(value, str):
                # Check if it's a datetime string
                try:
                    datetime.fromisoformat(value.replace("Z", "+00:00"))
                    data_type = "datetime"
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    data_type = "string"
        elif "status" in data:
            # For connectivity attributes (WiFi, Cellular)
            value = data["status"]
            data_type = "string"
        else:
            # Fallback for other attribute types
            value = str(data.get("description", "unknown"))
            data_type = "string"

        # Use current timestamp as fallback
        last_updated = datetime.now(timezone.utc)

        # Determine if attribute is diagnostic
        # Diagnostic attributes include connectivity, firmware, and status indicators
        attribute_id_lower = attribute_id.lower()
        is_diagnostic = (
            attribute_id.startswith("connectivity") or
            attribute_id.startswith("firmware") or
            "online" in attribute_id_lower or
            "connected" in attribute_id_lower or
            "status" in attribute_id_lower or
            "update" in attribute_id_lower or
            "version" in attribute_id_lower
        )

        return cls(
            attribute_id=full_attribute_id,
            device_id=device_id,
            name=attribute_id,
            display_name=data.get("description", attribute_id.replace("_", " ").replace(".", " ").title()),
            value=value,
            data_type=data_type,
            last_updated=last_updated,
            is_diagnostic=is_diagnostic
        )

    @property
    def unique_id(self) -> str:
        """Get unique identifier for Home Assistant."""
        return f"tibber_data_{self.device_id}_{self.name.replace('.', '_')}"


@dataclass
class TibberDevice:
    """IoT devices connected through Tibber platform."""

    device_id: str
    external_id: str
    name: str
    home_id: str
    online_status: bool
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    last_seen: Optional[datetime] = None
    capabilities: List["DeviceCapability"] = field(default_factory=list)
    attributes: List["DeviceAttribute"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate TibberDevice data."""
        if not self.device_id:
            raise ValueError("Device ID is required")

        # Validate device_id format (more lenient than strict UUID)
        if not self.device_id or len(self.device_id) < 5:
            raise ValueError("Device ID must be a valid identifier")

        if not self.home_id:
            raise ValueError("Home ID must reference existing TibberHome")

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], home_id: str) -> Self:
        """Create TibberDevice from API response data."""
        # Parse last_seen timestamp from status object
        last_seen = None
        status = data.get("status", {})
        if "lastSeen" in status:
            last_seen = datetime.fromisoformat(status["lastSeen"].replace("Z", "+00:00"))

        # Extract device info according to API structure
        info = data.get("info", {})
        name = info.get("name", f"Device {data['id'][:8]}")
        manufacturer = info.get("brand", "Unknown")
        model = info.get("model", "Unknown")

        # Determine online status (might be in attributes or derived from lastSeen)
        online_status = cls._determine_online_status(data, last_seen)

        device = cls(
            device_id=data["id"],
            external_id=data.get("externalId", ""),
            name=name,
            home_id=home_id,
            online_status=online_status,
            manufacturer=manufacturer,
            model=model,
            last_seen=last_seen
        )

        # Add capabilities if present
        if "capabilities" in data:
            for cap_data in data["capabilities"]:
                capability = DeviceCapability.from_api_data(cap_data, device.device_id)
                device.capabilities.append(capability)

        # Add attributes if present - according to OpenAPI spec, attributes is an array
        if "attributes" in data and isinstance(data["attributes"], list):
            for attr_data in data["attributes"]:
                if isinstance(attr_data, dict) and "id" in attr_data:
                    attribute = DeviceAttribute.from_api_data(
                        attr_data,
                        device.device_id,
                        attr_data["id"]
                    )
                    device.attributes.append(attribute)

        return device


    @classmethod
    def _determine_online_status(cls, data: Dict[str, Any], last_seen: Optional[datetime]) -> bool:
        """Determine device online status from available data."""
        # Check if there's an explicit online status in attributes (array structure)
        attributes = data.get("attributes", [])
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict):
                    # Look for connectivity-related attributes
                    attr_id = attr.get("id", "")
                    if "connectivity" in attr_id or "online" in attr_id:
                        if "value" in attr and isinstance(attr["value"], bool):
                            return attr["value"]
                        elif "status" in attr and attr["status"] in ["connected", "online"]:
                            return True
                        elif "status" in attr and attr["status"] in ["disconnected", "offline"]:
                            return False

        # Fallback: consider online if seen within last 5 minutes
        if last_seen:
            five_minutes_ago = datetime.now(timezone.utc).timestamp() - 300
            return last_seen.timestamp() > five_minutes_ago

        # Default: assume online if no information available
        return True

    @property
    def unique_id(self) -> str:
        """Get unique identifier for Home Assistant."""
        return f"tibber_device_{self.device_id}"

    @property
    def is_available(self) -> bool:
        """Check if device is available (online and recently seen)."""
        if not self.online_status:
            return False

        # If we have a last_seen timestamp, check if it's recent (within 5 minutes)
        if self.last_seen:
            time_threshold = datetime.now(timezone.utc).timestamp() - 300  # 5 minutes ago
            return self.last_seen.timestamp() > time_threshold

        # If no last_seen data, trust online_status
        return True

    def get_capability(self, name: str) -> Optional[DeviceCapability]:
        """Get capability by name."""
        for capability in self.capabilities:
            if capability.name == name:
                return capability
        return None

    def get_attribute(self, path: str) -> Optional[DeviceAttribute]:
        """Get attribute by path."""
        for attribute in self.attributes:
            if attribute.name == path:
                return attribute
        return None

    def update_capability_value(
        self,
        name: str,
        value: Union[float, str, bool, int],
        last_updated: Optional[datetime] = None
    ) -> bool:
        """Update capability value. Returns True if updated, False if not found."""
        capability = self.get_capability(name)
        if capability:
            capability.value = value
            capability.last_updated = last_updated or datetime.now(timezone.utc)
            return True
        return False