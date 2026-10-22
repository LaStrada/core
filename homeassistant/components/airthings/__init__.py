"""The Airthings integration."""

from datetime import timedelta
import logging

from airthings import Airthings

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_SECRET, DOMAIN
from .coordinator import AirthingsConfigEntry, AirthingsDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=6)


async def async_setup_entry(hass: HomeAssistant, entry: AirthingsConfigEntry) -> None:
    """Set up Airthings from a config entry."""
    airthings = Airthings(
        entry.data[CONF_ID],
        entry.data[CONF_SECRET],
        async_get_clientsession(hass),
    )

    coordinator = AirthingsDataUpdateCoordinator(hass, airthings, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: AirthingsConfigEntry) -> None:
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: AirthingsConfigEntry, device_entry: dr.AnyDeviceEntry
) -> bool:
    """Allow removing a device that Airthings no longer returns."""
    if entry.state is not ConfigEntryState.LOADED:
        return False
    return not any(
        identifier[0] == DOMAIN and identifier[1] in entry.runtime_data.data
        for identifier in device_entry.identifiers
    )
