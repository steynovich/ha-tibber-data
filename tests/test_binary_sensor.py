"""Test binary sensor entities integration."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from homeassistant.core import HomeAssistant
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import STATE_ON, STATE_OFF
from custom_components.tibber_data.binary_sensor import (
    async_setup_entry,
    TibberDataAttributeBinarySensor,
)
from custom_components.tibber_data.const import DOMAIN


class TestTibberDataBinarySensor:
    """Test TibberData binary sensor entities."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock TibberDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.data = {
            "devices": {
                "device-123": {
                    "id": "device-123",
                    "name": "Test EV",
                    "type": "EV",
                    "home_id": "home-456",
                    "online": True,
                    "attributes": {
                        "connectivity": {
                            "online": True,
                            "lastSeen": "2025-09-18T10:30:00Z",
                            "signalStrength": 85
                        },
                        "firmware": {
                            "version": "2025.4.1",
                            "updateAvailable": False,
                            "lastUpdated": "2025-08-15T14:20:00Z"
                        }
                    }
                },
                "device-789": {
                    "id": "device-789",
                    "name": "Smart Charger",
                    "type": "CHARGER",
                    "home_id": "home-456",
                    "online": False,
                    "attributes": {
                        "connectivity": {
                            "online": False,
                            "lastSeen": "2025-09-18T08:00:00Z",
                            "signalStrength": 0
                        },
                        "firmware": {
                            "version": "1.2.3",
                            "updateAvailable": True,
                            "lastUpdated": "2025-07-01T10:00:00Z"
                        }
                    }
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

    @pytest.mark.asyncio
    async def test_binary_sensor_setup(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test binary sensor platform setup."""
        # Mock hass.data structure
        hass.data[DOMAIN] = {
            mock_config_entry.entry_id: {
                "coordinator": mock_coordinator
            }
        }

        entities = []
        async def mock_async_add_entities(new_entities, update_before_add=True):
            entities.extend(new_entities)

        # Setup binary sensor platform
        await async_setup_entry(hass, mock_config_entry, mock_async_add_entities)

        # Should create binary sensors for boolean attributes
        # connectivity.online, firmware.updateAvailable for each device = 4 sensors
        assert len(entities) == 4

        # Verify sensor types
        online_sensors = [e for e in entities if "connectivity_online" in e.unique_id]
        update_sensors = [e for e in entities if "firmware_updateAvailable" in e.unique_id]

        assert len(online_sensors) == 2  # One for each device
        assert len(update_sensors) == 2  # One for each device

    def test_connectivity_binary_sensor_properties(self, mock_coordinator):
        """Test connectivity binary sensor properties."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Test basic properties
        assert sensor.name == "Test EV Online"
        assert sensor.unique_id == "tibber_data_device-123_connectivity_online"
        assert sensor.is_on is True  # Device is online
        assert sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY

        # Test device info
        device_info = sensor.device_info
        assert device_info["identifiers"] == {(DOMAIN, "device-123")}
        assert device_info["name"] == "Test EV"

    def test_update_available_binary_sensor_properties(self, mock_coordinator):
        """Test firmware update available binary sensor properties."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-789",
            attribute_path="firmware.updateAvailable",
            attribute_name="Update Available"
        )

        # Test basic properties
        assert sensor.name == "Smart Charger Update Available"
        assert sensor.unique_id == "tibber_data_device-789_firmware_updateAvailable"
        assert sensor.is_on is True  # Update is available
        assert sensor.device_class == BinarySensorDeviceClass.UPDATE

    def test_binary_sensor_state_unavailable_when_device_offline(self, mock_coordinator):
        """Test binary sensor shows unavailable when device is offline."""
        # Create sensor for offline device
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-789",  # This device is offline
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Sensor should be available (it's reporting the connectivity status)
        # but the value should be False (offline)
        assert sensor.available is True
        assert sensor.is_on is False

    def test_binary_sensor_state_updates(self, mock_coordinator):
        """Test binary sensor state updates when coordinator data changes."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="firmware.updateAvailable",
            attribute_name="Update Available"
        )

        # Initial state - no update available
        assert sensor.is_on is False

        # Update coordinator data - update becomes available
        mock_coordinator.data["devices"]["device-123"]["attributes"]["firmware"]["updateAvailable"] = True

        # Simulate coordinator update
        sensor.async_write_ha_state = MagicMock()
        sensor._handle_coordinator_update()

        # State should be updated
        assert sensor.is_on is True

    def test_binary_sensor_attributes(self, mock_coordinator):
        """Test binary sensor extra attributes."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        extra_state_attributes = sensor.extra_state_attributes

        # Should include relevant connectivity metadata
        assert "last_seen" in extra_state_attributes
        assert "signal_strength" in extra_state_attributes
        assert extra_state_attributes["signal_strength"] == 85

    def test_firmware_binary_sensor_attributes(self, mock_coordinator):
        """Test firmware binary sensor extra attributes."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="firmware.updateAvailable",
            attribute_name="Update Available"
        )

        extra_state_attributes = sensor.extra_state_attributes

        # Should include firmware metadata
        assert "firmware_version" in extra_state_attributes
        assert "last_updated" in extra_state_attributes
        assert extra_state_attributes["firmware_version"] == "2025.4.1"

    def test_missing_attribute_handling(self, mock_coordinator):
        """Test handling of missing attribute data."""
        # Try to create sensor for non-existent attribute
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="non.existent.attribute",
            attribute_name="Non Existent"
        )

        # Should handle gracefully
        assert not sensor.available
        assert sensor.is_on is None

    def test_missing_device_handling(self, mock_coordinator):
        """Test handling of missing device data."""
        # Try to create sensor for non-existent device
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="non-existent-device",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Should handle gracefully
        assert not sensor.available
        assert sensor.is_on is None

    def test_different_device_types_binary_sensors(self, mock_coordinator):
        """Test binary sensors for different device types."""
        # EV connectivity sensor
        ev_sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Charger connectivity sensor
        charger_sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-789",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Should have different states based on device status
        assert ev_sensor.is_on is True   # EV is online
        assert charger_sensor.is_on is False  # Charger is offline

        # But both should be available (reporting connectivity status)
        assert ev_sensor.available is True
        assert charger_sensor.available is True

    def test_binary_sensor_device_class_assignment(self, mock_coordinator):
        """Test proper device class assignment for different binary sensors."""
        # Connectivity sensor
        connectivity_sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Update available sensor
        update_sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="firmware.updateAvailable",
            attribute_name="Update Available"
        )

        assert connectivity_sensor.device_class == BinarySensorDeviceClass.CONNECTIVITY
        assert update_sensor.device_class == BinarySensorDeviceClass.UPDATE

    def test_nested_attribute_access(self, mock_coordinator):
        """Test accessing nested attribute values."""
        sensor = TibberDataAttributeBinarySensor(
            coordinator=mock_coordinator,
            device_id="device-123",
            attribute_path="connectivity.online",
            attribute_name="Online"
        )

        # Should correctly access nested path
        value = sensor._get_nested_attribute_value(
            mock_coordinator.data["devices"]["device-123"]["attributes"],
            "connectivity.online"
        )

        assert value is True

        # Test deeper nesting (if it existed)
        value = sensor._get_nested_attribute_value(
            {"level1": {"level2": {"level3": {"value": False}}}},
            "level1.level2.level3.value"
        )

        assert value is False