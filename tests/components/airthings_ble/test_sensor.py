"""Test the Airthings Wave sensor."""

from copy import deepcopy
import logging
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest

from homeassistant.components.airthings_ble.const import DEFAULT_SCAN_INTERVAL, DOMAIN
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import (
    CORENTIUM_HOME_2_DEVICE_INFO,
    CORENTIUM_HOME_2_SERVICE_INFO,
    WAVE_ENHANCE_DEVICE_INFO,
    WAVE_ENHANCE_SERVICE_INFO,
    create_device,
    create_entry,
    patch_airthings_ble,
    patch_async_ble_device_from_address,
    patch_async_discovered_service_info,
)

from tests.common import async_fire_time_changed

_LOGGER = logging.getLogger(__name__)


@pytest.mark.parametrize(
    ("unique_suffix", "expected_sensor_name"),
    [
        ("lux", "Illuminance"),
        ("noise", "Ambient noise"),
    ],
)
async def test_translation_keys_wave_enhance(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    unique_suffix: str,
    expected_sensor_name: str,
) -> None:
    """Test that translated sensor names are correct."""
    entry = create_entry(hass, WAVE_ENHANCE_SERVICE_INFO, WAVE_ENHANCE_DEVICE_INFO)
    device = create_device(
        entry, device_registry, WAVE_ENHANCE_SERVICE_INFO, WAVE_ENHANCE_DEVICE_INFO
    )

    with (
        patch_async_ble_device_from_address(WAVE_ENHANCE_SERVICE_INFO.device),
        patch_async_discovered_service_info([WAVE_ENHANCE_SERVICE_INFO]),
        patch_airthings_ble(WAVE_ENHANCE_DEVICE_INFO),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert device is not None
    assert device.name == "Airthings Wave Enhance (123456)"

    unique_id = f"{WAVE_ENHANCE_DEVICE_INFO.address}_{unique_suffix}"
    entity_id = entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id)
    assert entity_id is not None

    state = hass.states.get(entity_id)
    assert state is not None

    expected_value = WAVE_ENHANCE_DEVICE_INFO.sensors[unique_suffix]
    assert state.state == str(expected_value)

    expected_name = f"Airthings Wave Enhance (123456) {expected_sensor_name}"
    assert state.attributes.get("friendly_name") == expected_name


async def test_disabled_connectivity_mode_corentium_home_2(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test that translated sensor names are correct for disabled sensors."""
    entry = create_entry(
        hass,
        CORENTIUM_HOME_2_SERVICE_INFO,
        CORENTIUM_HOME_2_DEVICE_INFO,
    )
    device = create_device(
        entry,
        device_registry,
        CORENTIUM_HOME_2_SERVICE_INFO,
        CORENTIUM_HOME_2_DEVICE_INFO,
    )

    with (
        patch_async_ble_device_from_address(CORENTIUM_HOME_2_SERVICE_INFO.device),
        patch_async_discovered_service_info([CORENTIUM_HOME_2_SERVICE_INFO]),
        patch_airthings_ble(CORENTIUM_HOME_2_DEVICE_INFO),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert device is not None
    assert device.name == "Airthings Corentium Home 2 (123456)"

    unique_id = f"{CORENTIUM_HOME_2_DEVICE_INFO.address}_connectivity_mode"

    entity_id = entity_registry.async_get_entity_id(Platform.SENSOR, DOMAIN, unique_id)
    assert entity_id is not None

    entity_entry = entity_registry.async_get(entity_id)
    assert entity_entry is not None
    assert entity_entry.disabled
    assert entity_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("source_value", "expected_state"),
    [
        (None, STATE_UNKNOWN),
        (123, STATE_UNKNOWN),
        (45.6, STATE_UNKNOWN),
        ("Bluetooth", "bluetooth"),
    ],
)
async def test_connectivity_mode(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
    source_value: Any,
    expected_state: str,
) -> None:
    """Test that non-string connectivity mode values are handled correctly."""
    test_device = deepcopy(CORENTIUM_HOME_2_DEVICE_INFO)

    # Non-string value, will be mapped to 'unknown' state
    test_device.sensors["connectivity_mode"] = source_value

    entry = create_entry(hass, CORENTIUM_HOME_2_SERVICE_INFO, test_device)
    create_device(entry, device_registry, CORENTIUM_HOME_2_SERVICE_INFO, test_device)

    with (
        patch_async_ble_device_from_address(CORENTIUM_HOME_2_SERVICE_INFO.device),
        patch_async_discovered_service_info([CORENTIUM_HOME_2_SERVICE_INFO]),
        patch_airthings_ble(test_device),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    state = hass.states.get(
        "sensor.airthings_corentium_home_2_123456_connectivity_mode"
    )
    assert state is not None
    assert state.state == expected_state


async def test_sensor_added_on_later_refresh(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that sensors missing from the first refresh are added later."""
    first_device = deepcopy(WAVE_ENHANCE_DEVICE_INFO)
    del first_device.sensors["battery"]
    later_device = deepcopy(first_device)
    later_device.sensors = {"unknown_key": 1, **first_device.sensors, "battery": 42}
    last_device = deepcopy(later_device)
    last_device.sensors["battery"] = 41

    entry = create_entry(hass, WAVE_ENHANCE_SERVICE_INFO, first_device)
    battery_unique_id = f"{WAVE_ENHANCE_DEVICE_INFO.address}_battery"

    with (
        patch_async_ble_device_from_address(WAVE_ENHANCE_SERVICE_INFO.device),
        patch_async_discovered_service_info([WAVE_ENHANCE_SERVICE_INFO]),
        patch_airthings_ble(first_device) as mock_update,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert (
            entity_registry.async_get_entity_id(
                Platform.SENSOR, DOMAIN, battery_unique_id
            )
            is None
        )
        entity_count = len(
            er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        )

        mock_update.return_value = later_device
        freezer.tick(DEFAULT_SCAN_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        entity_id = entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, battery_unique_id
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == "42"
        assert (
            len(er.async_entries_for_config_entry(entity_registry, entry.entry_id))
            == entity_count + 1
        )

        mock_update.return_value = last_device
        freezer.tick(DEFAULT_SCAN_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert hass.states.get(entity_id).state == "41"
        assert (
            len(er.async_entries_for_config_entry(entity_registry, entry.entry_id))
            == entity_count + 1
        )
        assert not [
            record
            for record in caplog.records
            if record.levelno >= logging.ERROR
            and record.name.startswith("homeassistant.")
        ]
