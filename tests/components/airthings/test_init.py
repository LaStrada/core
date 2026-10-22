"""Test the Airthings integration setup."""

from airthings import Airthings, AirthingsDevice
from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import WebSocketGenerator

from homeassistant.components.airthings.const import DOMAIN
from homeassistant.components.airthings.coordinator import SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

from . import setup_integration

REJECTED = "Failed to remove device entry, rejected by integration"


@pytest.mark.parametrize("airthings_fixture", ["wave_plus"])
async def test_remove_device(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
    mock_airthings_client: Airthings,
    mock_airthings_device: AirthingsDevice,
    device_registry: dr.DeviceRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a device can only be removed once Airthings no longer returns it."""
    assert await async_setup_component(hass, "config", {})
    await setup_integration(hass, mock_config_entry)
    client = await hass_ws_client(hass)
    device_entry = device_registry.async_get_device_by_identifier(
        (DOMAIN, mock_airthings_device.device_id), mock_config_entry.entry_id
    )
    assert device_entry

    response = await client.remove_device(device_entry.id)
    assert not response["success"]
    assert response["error"]["message"] == REJECTED
    assert device_registry.async_get(device_entry.id)

    mock_airthings_client.update_devices.return_value = {}
    freezer.tick(SCAN_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    response = await client.remove_device(device_entry.id)
    assert response["success"]
    assert device_registry.async_get(device_entry.id) is None


@pytest.mark.parametrize("airthings_fixture", ["wave_plus"])
async def test_remove_device_with_foreign_identifier(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
    mock_airthings_client: Airthings,
    mock_airthings_device: AirthingsDevice,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test identifiers from other integrations do not affect removal."""
    assert await async_setup_component(hass, "config", {})
    await setup_integration(hass, mock_config_entry)
    client = await hass_ws_client(hass)

    live_device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={
            (DOMAIN, mock_airthings_device.device_id),
            ("other", "hub", "device"),
        },
    )
    response = await client.remove_device(live_device.id)
    assert not response["success"]
    assert response["error"]["message"] == REJECTED
    assert device_registry.async_get(live_device.id)

    removed_device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "2930000099"), ("other", "hub", "device2")},
    )
    response = await client.remove_device(removed_device.id)
    assert response["success"]
    assert device_registry.async_get(removed_device.id) is None


@pytest.mark.parametrize("airthings_fixture", ["wave_plus"])
async def test_remove_device_when_not_loaded(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    mock_config_entry: MockConfigEntry,
    mock_airthings_client: Airthings,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test removal is refused while the config entry is not loaded."""
    assert await async_setup_component(hass, "config", {})
    await setup_integration(hass, mock_config_entry)
    removed_device = device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "2930000099")},
    )
    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    response = await client.remove_device(removed_device.id)
    assert not response["success"]
    assert response["error"]["message"] == REJECTED
    assert device_registry.async_get(removed_device.id)
