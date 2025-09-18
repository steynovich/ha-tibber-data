"""Test component initialization integration."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from custom_components.tibber_data import async_setup_entry, async_unload_entry
from custom_components.tibber_data.const import DOMAIN, PLATFORMS


class TestTibberDataInit:
    """Test TibberData component initialization."""

    @pytest.fixture
    def mock_coordinator(self):
        """Mock TibberDataUpdateCoordinator."""
        coordinator = MagicMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        coordinator.data = {
            "homes": {
                "home-123": {"id": "home-123", "displayName": "Test Home"}
            },
            "devices": {
                "device-456": {
                    "id": "device-456",
                    "type": "EV",
                    "name": "Test EV",
                    "home_id": "home-123"
                }
            }
        }
        return coordinator

    @pytest.mark.asyncio
    async def test_successful_setup(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test successful component setup."""
        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ) as mock_client_class:

            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Setup entry
            result = await async_setup_entry(hass, mock_config_entry)

            assert result is True
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]

            # Verify coordinator was created and refreshed
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()

            # Verify platforms are loaded
            assert len(hass.config_entries.async_forward_entry_setups.call_args_list) > 0

    @pytest.mark.asyncio
    async def test_setup_with_invalid_config(self, hass: HomeAssistant):
        """Test setup with invalid configuration."""
        invalid_config_entry = MagicMock(spec=ConfigEntry)
        invalid_config_entry.data = {}  # Missing required fields
        invalid_config_entry.entry_id = "test_entry_invalid"

        # Setup should fail gracefully
        result = await async_setup_entry(hass, invalid_config_entry)

        assert result is False

    @pytest.mark.asyncio
    async def test_setup_with_api_failure(self, hass: HomeAssistant, mock_config_entry):
        """Test setup when API is unavailable."""
        with patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ) as mock_client_class:

            mock_client = AsyncMock()
            mock_client.get_homes.side_effect = Exception("API unavailable")
            mock_client_class.return_value = mock_client

            # Setup should handle API failure gracefully
            result = await async_setup_entry(hass, mock_config_entry)

            # Should still return True but log error
            assert result is True

    @pytest.mark.asyncio
    async def test_device_registry_integration(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test integration with Home Assistant device registry."""
        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ):

            await async_setup_entry(hass, mock_config_entry)

            # Verify devices are registered in device registry
            device_registry = hass.helpers.device_registry.async_get(hass)
            devices = device_registry.devices

            # Should have registered devices from coordinator data
            tibber_devices = [
                device for device in devices.values()
                if DOMAIN in device.config_entries
            ]

            # At least one device should be registered
            assert len(tibber_devices) >= 1

    @pytest.mark.asyncio
    async def test_successful_unload(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test successful component unload."""
        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ):

            # First setup the entry
            await async_setup_entry(hass, mock_config_entry)
            assert DOMAIN in hass.data
            assert mock_config_entry.entry_id in hass.data[DOMAIN]

            # Then unload it
            result = await async_unload_entry(hass, mock_config_entry)

            assert result is True
            # Entry data should be cleaned up
            assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})

    @pytest.mark.asyncio
    async def test_homeassistant_stop_cleanup(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test cleanup when Home Assistant stops."""
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()

        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient",
            return_value=mock_client
        ):

            await async_setup_entry(hass, mock_config_entry)

            # Simulate Home Assistant stop event
            hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
            await hass.async_block_till_done()

            # Verify client cleanup was called
            mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_config_entries(self, hass: HomeAssistant, mock_coordinator):
        """Test handling of multiple configuration entries."""
        # Create two config entries for different users
        config_entry_1 = MagicMock(spec=ConfigEntry)
        config_entry_1.entry_id = "user_1_entry"
        config_entry_1.unique_id = "user_1"
        config_entry_1.data = {
            "access_token": "token_1",
            "refresh_token": "refresh_1",
            "client_id": "client_1"
        }

        config_entry_2 = MagicMock(spec=ConfigEntry)
        config_entry_2.entry_id = "user_2_entry"
        config_entry_2.unique_id = "user_2"
        config_entry_2.data = {
            "access_token": "token_2",
            "refresh_token": "refresh_2",
            "client_id": "client_2"
        }

        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ):

            # Setup both entries
            result_1 = await async_setup_entry(hass, config_entry_1)
            result_2 = await async_setup_entry(hass, config_entry_2)

            assert result_1 is True
            assert result_2 is True

            # Both entries should be in hass.data
            assert config_entry_1.entry_id in hass.data[DOMAIN]
            assert config_entry_2.entry_id in hass.data[DOMAIN]

    @pytest.mark.asyncio
    async def test_reload_entry(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test reloading a configuration entry."""
        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ):

            # Setup entry
            await async_setup_entry(hass, mock_config_entry)
            original_data = hass.data[DOMAIN][mock_config_entry.entry_id]

            # Unload entry
            await async_unload_entry(hass, mock_config_entry)

            # Setup entry again (reload)
            await async_setup_entry(hass, mock_config_entry)
            reloaded_data = hass.data[DOMAIN][mock_config_entry.entry_id]

            # Should have fresh coordinator instance
            assert reloaded_data is not original_data

    @pytest.mark.asyncio
    async def test_platform_loading(self, hass: HomeAssistant, mock_config_entry, mock_coordinator):
        """Test that all required platforms are loaded."""
        with patch(
            "custom_components.tibber_data.TibberDataUpdateCoordinator",
            return_value=mock_coordinator
        ), patch(
            "custom_components.tibber_data.api.client.TibberDataClient"
        ), patch(
            "homeassistant.config_entries.ConfigEntries.async_forward_entry_setups"
        ) as mock_forward:

            await async_setup_entry(hass, mock_config_entry)

            # Verify all expected platforms are loaded
            mock_forward.assert_called_once()
            loaded_platforms = mock_forward.call_args[0][1]

            expected_platforms = set(PLATFORMS)  # From const.py
            loaded_platforms_set = set(loaded_platforms)

            assert loaded_platforms_set == expected_platforms