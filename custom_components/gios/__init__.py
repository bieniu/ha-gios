"""The GIOS component."""
from datetime import timedelta
import logging

from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
from gios import ApiError, Gios, InvalidSensorsData, NoStationError

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_STATION_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured GIOS."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up GIOS as config entry."""
    station_id = config_entry.data[CONF_STATION_ID]

    # For backwards compat, set unique ID
    if config_entry.unique_id is None:
        hass.config_entries.async_update_entry(config_entry, unique_id=station_id)

    try:
        scan_interval = timedelta(seconds=config_entry.options[CONF_SCAN_INTERVAL])
    except KeyError:
        scan_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    _LOGGER.debug("Using station_id: %s", station_id)

    websession = async_get_clientsession(hass)

    coordinator = GiosDataUpdateCoordinator(hass, websession, station_id, scan_interval)
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = coordinator

    config_entry.add_update_listener(update_listener)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    hass.data[DOMAIN].pop(config_entry.entry_id)
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True


async def update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


class GiosDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching GIOS data API."""

    def __init__(self, hass, session, station_id, scan_interval):
        """Initialize."""
        self.gios = Gios(station_id, session)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=scan_interval)

    async def _async_update_data(self):
        """Update data via library."""
        try:
            with timeout(30):
                await self.gios.update()
        except (
            ApiError,
            NoStationError,
            ClientConnectorError,
            InvalidSensorsData,
        ) as error:
            raise UpdateFailed(error)
        return self.gios.data
