"""Test API data models."""
import pytest
from datetime import datetime, timezone
from custom_components.tibber_data.api.models import TibberDevice


class TestTibberDevice:
    """Test TibberDevice model."""

    def test_determine_online_status_from_isonline_attribute(self):
        """Test that isOnline attribute (camelCase) is correctly detected."""
        # Test data with camelCase isOnline attribute
        data = {
            "id": "dm9sdm8g-test-id",
            "externalId": "YV1ZWH5V7P1539402",
            "info": {
                "name": "V60",
                "brand": "Volvo",
                "model": "V60"
            },
            "status": {},
            "capabilities": [],
            "attributes": [
                {
                    "id": "isOnline",
                    "description": "Isonline",
                    "value": True
                }
            ]
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should detect isOnline attribute (case-insensitive)
        assert device.online_status is True
        assert device.name == "V60"
        assert device.manufacturer == "Volvo"
        assert device.model == "V60"

    def test_determine_online_status_from_isonline_false(self):
        """Test offline detection from isOnline attribute."""
        data = {
            "id": "device-456",
            "externalId": "external-456",
            "info": {
                "name": "Offline Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {},
            "capabilities": [],
            "attributes": [
                {
                    "id": "isOnline",
                    "description": "Isonline",
                    "value": False
                }
            ]
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should detect offline status
        assert device.online_status is False

    def test_determine_online_status_from_connectivity_attribute(self):
        """Test online status from connectivity attribute."""
        data = {
            "id": "device-789",
            "externalId": "external-789",
            "info": {
                "name": "Connectivity Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {},
            "capabilities": [],
            "attributes": [
                {
                    "id": "connectivity.wifi",
                    "status": "connected"
                }
            ]
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should detect online from connectivity status
        assert device.online_status is True

    def test_determine_online_status_from_last_seen(self):
        """Test online status determined from lastSeen timestamp."""
        # Recent lastSeen (within 5 minutes)
        recent_time = datetime.now(timezone.utc)
        data = {
            "id": "device-recent",
            "externalId": "external-recent",
            "info": {
                "name": "Recent Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {
                "lastSeen": recent_time.isoformat()
            },
            "capabilities": [],
            "attributes": []
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should be online (seen within 5 minutes)
        assert device.online_status is True

    def test_determine_online_status_default_true(self):
        """Test that devices default to online when no status info available."""
        data = {
            "id": "device-unknown",
            "externalId": "external-unknown",
            "info": {
                "name": "Unknown Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {},
            "capabilities": [],
            "attributes": []
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should default to online
        assert device.online_status is True

    def test_determine_online_status_with_non_dict_attributes(self):
        """Test that invalid attributes (non-dict) are handled gracefully."""
        data = {
            "id": "device-invalid",
            "externalId": "external-invalid",
            "info": {
                "name": "Invalid Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {},
            "capabilities": [],
            "attributes": [
                "invalid_string",  # Not a dict
                None,  # None value
                {
                    "id": "validAttribute",
                    "value": "test"
                }
            ]
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should handle gracefully and default to online
        assert device.online_status is True

    def test_determine_online_status_fast_path_no_attributes(self):
        """Test fast path when attributes is not a list."""
        data = {
            "id": "device-noattr",
            "externalId": "external-noattr",
            "info": {
                "name": "No Attributes Device",
                "brand": "Test",
                "model": "Model"
            },
            "status": {},
            "capabilities": [],
            "attributes": None  # Not a list
        }

        device = TibberDevice.from_api_data(data, "home-123")

        # Should use fast path and default to online
        assert device.online_status is True

    def test_ev_device_with_capabilities(self):
        """Test EV device with typical capabilities."""
        data = {
            "id": "ev-device-123",
            "externalId": "VIN123456",
            "info": {
                "name": "Model Y",
                "brand": "Tesla",
                "model": "Model Y"
            },
            "status": {},
            "capabilities": [
                {
                    "id": "storage.stateOfCharge",
                    "description": "state of charge",
                    "value": 85,
                    "unit": "%",
                    "lastUpdated": "2025-09-30T10:00:00Z"
                },
                {
                    "id": "range.remaining",
                    "description": "estimated remaining driving range",
                    "value": 350000,
                    "unit": "m",
                    "lastUpdated": "2025-09-30T10:00:00Z"
                },
                {
                    "id": "connector.status",
                    "description": "vehicle plug status",
                    "value": "connected",
                    "unit": "",
                    "lastUpdated": "2025-09-30T10:00:00Z"
                },
                {
                    "id": "charging.status",
                    "description": "vehicle charging status",
                    "value": "charging",
                    "unit": "",
                    "lastUpdated": "2025-09-30T10:00:00Z"
                }
            ],
            "attributes": [
                {
                    "id": "vinNumber",
                    "description": "Vinnumber",
                    "value": "VIN123456"
                },
                {
                    "id": "isOnline",
                    "description": "Isonline",
                    "value": True
                }
            ]
        }

        device = TibberDevice.from_api_data(data, "home-123")

        assert device.name == "Model Y"
        assert device.manufacturer == "Tesla"
        assert device.online_status is True
        assert len(device.capabilities) == 4
        assert len(device.attributes) == 2

        # Check capabilities
        soc_cap = device.get_capability("storage.stateOfCharge")
        assert soc_cap is not None
        assert soc_cap.value == 85
        assert soc_cap.unit == "%"

        range_cap = device.get_capability("range.remaining")
        assert range_cap is not None
        assert range_cap.value == 350000
        assert range_cap.unit == "m"

        connector_cap = device.get_capability("connector.status")
        assert connector_cap is not None
        assert connector_cap.value == "connected"

        charging_cap = device.get_capability("charging.status")
        assert charging_cap is not None
        assert charging_cap.value == "charging"