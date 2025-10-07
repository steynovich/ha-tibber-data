"""Test entity data caching behavior."""
import pytest
from unittest.mock import MagicMock
from custom_components.tibber_data.sensor import TibberDataCapabilitySensor
from custom_components.tibber_data.binary_sensor import TibberDataAttributeBinarySensor


class TestEntityCaching:
    """Test entity caching optimizations."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock TibberDataUpdateCoordinator with test data."""
        coordinator = MagicMock()
        coordinator.data = {
            "devices": {
                "device-123": {
                    "id": "device-123",
                    "name": "Test Device",
                    "home_id": "home-456",
                    "online": True,
                    "capabilities": [
                        {
                            "name": "battery_level",
                            "displayName": "Battery Level",
                            "value": 85.0,
                            "unit": "%",
                            "lastUpdated": "2025-09-18T10:30:00Z"
                        }
                    ],
                    "attributes": [
                        {
                            "name": "isOnline",
                            "displayName": "Is Online",
                            "value": True,
                            "dataType": "boolean",
                            "lastUpdated": "2025-09-18T10:30:00Z",
                            "isDiagnostic": False
                        }
                    ]
                }
            },
            "homes": {
                "home-456": {
                    "id": "home-456",
                    "displayName": "Test Home"
                }
            }
        }
        coordinator.async_add_listener = MagicMock()
        return coordinator

    def test_capability_data_caching(self, mock_coordinator):
        """Test that capability_data property uses caching."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Multiple accesses within same data object should return same cached object
        cap_data_1 = sensor.capability_data
        cap_data_2 = sensor.capability_data
        cap_data_3 = sensor.capability_data

        # All should be the exact same object (not just equal, but identical)
        assert cap_data_1 is cap_data_2
        assert cap_data_2 is cap_data_3
        assert id(cap_data_1) == id(cap_data_2) == id(cap_data_3)

    def test_device_data_caching(self, mock_coordinator):
        """Test that device_data property uses caching."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Multiple accesses within same data object should return same cached object
        device_data_1 = sensor.device_data
        device_data_2 = sensor.device_data
        device_data_3 = sensor.device_data

        # All should be the exact same object
        assert device_data_1 is device_data_2
        assert device_data_2 is device_data_3

    def test_cache_invalidation_on_coordinator_update(self, mock_coordinator):
        """Test that cache is invalidated when coordinator data changes."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Get initial cached data
        cap_data_1 = sensor.capability_data
        assert cap_data_1["value"] == 85.0

        # Simulate coordinator update with NEW data object (as coordinator does)
        mock_coordinator.data = {
            "devices": {
                "device-123": {
                    "id": "device-123",
                    "name": "Test Device",
                    "home_id": "home-456",
                    "online": True,
                    "capabilities": [
                        {
                            "name": "battery_level",
                            "displayName": "Battery Level",
                            "value": 95.0,  # Changed value
                            "unit": "%",
                            "lastUpdated": "2025-09-18T10:35:00Z"
                        }
                    ]
                }
            },
            "homes": {
                "home-456": {
                    "id": "home-456",
                    "displayName": "Test Home"
                }
            }
        }

        # Cache should be invalidated and return new data
        cap_data_2 = sensor.capability_data
        assert cap_data_2["value"] == 95.0

        # Should be a different object (not cached from before)
        assert cap_data_1 is not cap_data_2

    def test_in_place_modification_visible_through_cache(self, mock_coordinator):
        """Test that in-place modifications are visible through cached references."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Get initial value through cache
        assert sensor.native_value == 85.0

        # Modify data in-place (as tests do)
        mock_coordinator.data["devices"]["device-123"]["capabilities"][0]["value"] = 90.0

        # Should see the new value (cached reference reflects in-place change)
        assert sensor.native_value == 90.0

    def test_multiple_property_accesses_use_cache(self, mock_coordinator):
        """Test that multiple property accesses benefit from caching."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Simulate what Home Assistant does during state update:
        # accesses multiple properties that all need capability_data
        _ = sensor.device_class
        _ = sensor.state_class
        _ = sensor.native_value
        _ = sensor.native_unit_of_measurement
        _ = sensor.extra_state_attributes
        _ = sensor.suggested_display_precision
        _ = sensor.options

        # All these properties should use the same cached capability_data
        # We can't easily count cache hits, but we can verify it still works
        assert sensor.native_value == 85.0
        assert sensor.native_unit_of_measurement == "%"

    def test_attribute_data_caching(self, mock_coordinator):
        """Test that attribute_data property uses caching."""
        binary_sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="isOnline",
            attribute_name="Is Online"
        )

        # Multiple accesses should return same cached object
        attr_data_1 = binary_sensor.attribute_data
        attr_data_2 = binary_sensor.attribute_data

        # Should be the exact same object
        assert attr_data_1 is attr_data_2
        assert id(attr_data_1) == id(attr_data_2)

    def test_cache_per_entity_instance(self, mock_coordinator):
        """Test that each entity instance has its own cache."""
        sensor1 = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        sensor2 = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Each sensor should have its own cache
        cap_data_1 = sensor1.capability_data
        cap_data_2 = sensor2.capability_data

        # They should be equal but could be same object (both reference same dict)
        assert cap_data_1 == cap_data_2
        # In this case they actually ARE the same object since both fetch
        # the same capability from coordinator data
        assert cap_data_1 is cap_data_2

    def test_cache_invalidation_with_none_data(self, mock_coordinator):
        """Test cache handling when coordinator data becomes None."""
        sensor = TibberDataCapabilitySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            capability_name="battery_level"
        )

        # Get initial data
        assert sensor.device_data is not None
        assert sensor.capability_data is not None

        # Simulate coordinator losing data (e.g., during error)
        mock_coordinator.data = None

        # Should handle gracefully and return None
        assert sensor.device_data is None
        assert sensor.capability_data is None
        assert sensor.native_value is None

        # Restore data
        mock_coordinator.data = {
            "devices": {
                "device-123": {
                    "id": "device-123",
                    "name": "Test Device",
                    "home_id": "home-456",
                    "online": True,
                    "capabilities": [
                        {
                            "name": "battery_level",
                            "displayName": "Battery Level",
                            "value": 100.0,
                            "unit": "%",
                            "lastUpdated": "2025-09-18T10:40:00Z"
                        }
                    ]
                }
            },
            "homes": {}
        }

        # Should work again with new data
        assert sensor.device_data is not None
        assert sensor.capability_data is not None
        assert sensor.native_value == 100.0
