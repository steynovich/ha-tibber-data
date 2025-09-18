"""Data models for Tibber Data API integration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID


@dataclass
class OAuthSession:
    """Authentication session for accessing Tibber Data API."""

    session_id: str
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: int = 0
    scopes: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_refreshed: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Validate OAuth session data."""
        if not self.access_token:
            raise ValueError("Access token is required")
        if not self.refresh_token:
            raise ValueError("Refresh token is required")
        if not self.user_id:
            raise ValueError("User ID is required")
        if self.token_type != "Bearer":
            raise ValueError("Only Bearer token type is supported")

        # Ensure scopes include required permissions
        required_scopes = {"USER", "HOME"}
        if not required_scopes.issubset(set(self.scopes)):
            raise ValueError(f"Missing required scopes: {required_scopes - set(self.scopes)}")

    @property
    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at == 0:
            return False
        return datetime.now(timezone.utc).timestamp() >= self.expires_at

    @property
    def needs_refresh(self, threshold_seconds: int = 600) -> bool:
        """Check if token should be refreshed (within threshold of expiry)."""
        if self.expires_at == 0:
            return False
        return datetime.now(timezone.utc).timestamp() >= (self.expires_at - threshold_seconds)

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        scopes: Optional[List[str]] = None
    ) -> None:
        """Update token information after refresh."""
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = int(datetime.now(timezone.utc).timestamp() + expires_in)
        self.last_refreshed = datetime.now(timezone.utc)

        if scopes is not None:
            self.scopes = scopes

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OAuthSession:
        """Create OAuthSession from dictionary data."""
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
        """Convert OAuthSession to dictionary for storage."""
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
    def from_api_data(cls, data: Dict[str, Any]) -> TibberHome:
        """Create TibberHome from API response data."""
        return cls(
            home_id=data["id"],
            display_name=data["displayName"],
            time_zone=data["timeZone"],
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
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    precision: Optional[int] = None

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

        # Validate value bounds if specified
        if isinstance(self.value, (int, float)):
            if self.min_value is not None and self.value < self.min_value:
                raise ValueError(f"Value {self.value} is below minimum {self.min_value}")
            if self.max_value is not None and self.value > self.max_value:
                raise ValueError(f"Value {self.value} is above maximum {self.max_value}")

        # Validate last_updated is not in the future
        if self.last_updated > datetime.now(timezone.utc):
            raise ValueError("Last updated timestamp cannot be in the future")

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], device_id: str) -> DeviceCapability:
        """Create DeviceCapability from API response data."""
        capability_id = f"{device_id}_{data['name']}"

        # Parse timestamp
        last_updated = datetime.fromisoformat(data["lastUpdated"].replace("Z", "+00:00"))

        return cls(
            capability_id=capability_id,
            device_id=device_id,
            name=data["name"],
            display_name=data["displayName"],
            value=data["value"],
            unit=data["unit"],
            last_updated=last_updated,
            min_value=data.get("minValue"),
            max_value=data.get("maxValue"),
            precision=data.get("precision")
        )

    @property
    def unique_id(self) -> str:
        """Get unique identifier for Home Assistant."""
        return f"tibber_data_{self.device_id}_{self.name}"

    @property
    def formatted_value(self) -> str:
        """Get formatted value with proper precision."""
        if isinstance(self.value, float) and self.precision is not None:
            return f"{self.value:.{self.precision}f}"
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
    def from_api_data(cls, data: Dict[str, Any], device_id: str, attribute_path: str) -> DeviceAttribute:
        """Create DeviceAttribute from API response data."""
        attribute_id = f"{device_id}_{attribute_path.replace('.', '_')}"

        # Parse timestamp if it's a string
        last_updated = data.get("lastUpdated", datetime.now(timezone.utc))
        if isinstance(last_updated, str):
            last_updated = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))

        # Determine data type from value
        value = data["value"]
        if isinstance(value, bool):
            data_type = "boolean"
        elif isinstance(value, (int, float)):
            data_type = "number"
        elif isinstance(value, datetime):
            data_type = "datetime"
        else:
            data_type = "string"

        return cls(
            attribute_id=attribute_id,
            device_id=device_id,
            name=attribute_path,
            display_name=data.get("displayName", attribute_path.replace("_", " ").title()),
            value=value,
            data_type=data_type,
            last_updated=last_updated,
            is_diagnostic=data.get("is_diagnostic", attribute_path.startswith("connectivity") or attribute_path.startswith("firmware"))
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
    device_type: str
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

        # Validate UUID format for device_id
        try:
            UUID(self.device_id)
        except ValueError:
            raise ValueError("Device ID must be a valid UUID format")

        if not self.home_id:
            raise ValueError("Home ID must reference existing TibberHome")

        # Validate device type
        valid_types = {"EV", "CHARGER", "THERMOSTAT", "SOLAR_INVERTER", "BATTERY", "HEAT_PUMP"}
        if self.device_type not in valid_types:
            raise ValueError(f"Device type must be one of: {valid_types}")

        # last_seen is already properly typed as Optional[datetime]

    @classmethod
    def from_api_data(cls, data: Dict[str, Any], home_id: str) -> TibberDevice:
        """Create TibberDevice from API response data."""
        # Parse last_seen timestamp
        last_seen = None
        if "lastSeen" in data:
            last_seen = datetime.fromisoformat(data["lastSeen"].replace("Z", "+00:00"))

        device = cls(
            device_id=data["id"],
            external_id=data["externalId"],
            device_type=data["type"],
            name=data["name"],
            home_id=home_id,
            online_status=data["online"],
            manufacturer=data.get("manufacturer"),
            model=data.get("model"),
            last_seen=last_seen
        )

        # Add capabilities if present
        if "capabilities" in data:
            for cap_data in data["capabilities"]:
                capability = DeviceCapability.from_api_data(cap_data, device.device_id)
                device.capabilities.append(capability)

        # Add attributes if present
        if "attributes" in data:
            for attr_path, attr_data in data["attributes"].items():
                if isinstance(attr_data, dict):
                    for sub_attr, sub_value in attr_data.items():
                        # Type hints for clarity - sub_attr is str, sub_value is Any
                        full_path: str = f"{attr_path}.{sub_attr}"
                        attribute = DeviceAttribute.from_api_data(
                            {"value": sub_value, "displayName": sub_attr.replace("_", " ").title()},
                            device.device_id,
                            full_path
                        )
                        device.attributes.append(attribute)

        return device

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