"""The Airthings integration."""
from __future__ import annotations

from datetime import timedelta
import logging

from airthings import AirthingsError
from airthings_sdk import Airthings, AirthingsDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_SECRET, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]
SCAN_INTERVAL = timedelta(minutes=6)

AirthingsDataCoordinatorType = DataUpdateCoordinator[dict[str, AirthingsDevice]]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Airthings from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    airthings = Airthings(
        entry.data[CONF_ID],
        entry.data[CONF_SECRET],
        get_async_client(hass),
    )

    async def _update_method() -> dict[str, AirthingsDevice] | None:
        """Get the latest data from Airthings."""
        try:
            return airthings.update_devices()
        except AirthingsError as err:
            raise UpdateFailed(f"Unable to fetch data: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=_update_method,
        update_interval=SCAN_INTERVAL,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
