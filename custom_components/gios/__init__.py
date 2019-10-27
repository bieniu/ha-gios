"""The GIOS component."""
import logging
from asyncio import TimeoutError
from datetime import timedelta

import aiohttp
import async_timeout
from aiohttp.client_exceptions import ClientConnectorError
from .pygios import Gios, ApiError, NoStationError

from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import Throttle

from .const import (
    ATTR_ID,
    ATTR_INDEX,
    ATTR_STATION,
    ATTR_VALUE,
    CONF_STATION_ID,
    DATA_CLIENT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

ATTR_GEGR_LAT = "gegrLat"
ATTR_GEGR_LON = "gegrLon"
ATTR_INDEX_LEVEL = "{}IndexLevel"
ATTR_INDEX_LEVEL_NAME = "indexLevelName"
ATTR_PARAM = "param"
ATTR_PARAM_CODE = "paramCode"
ATTR_PARAM_NAME = "paramName"
ATTR_ST_INDEX_LEVEL = "stIndexLevel"
ATTR_STATION_NAME = "stationName"
ATTR_VALUES = "values"

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured GIOS."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up GIOS as config entry."""
    station_id = config_entry.data[CONF_STATION_ID]
    try:
        scan_interval = config_entry.options[CONF_SCAN_INTERVAL]
    except KeyError:
        scan_interval = DEFAULT_SCAN_INTERVAL
    _LOGGER.debug("Using station_id: %s", station_id)

    websession = async_get_clientsession(hass)

    gios = GiosData(
        websession, station_id, scan_interval=timedelta(seconds=scan_interval)
    )

    await gios.async_update()

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][DATA_CLIENT] = {}
    hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id] = gios

    config_entry.add_update_listener(update_listener)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    hass.data[DOMAIN][DATA_CLIENT].pop(config_entry.entry_id)
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True


async def update_listener(hass, entry):
    """Update listener."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, "sensor"))


class GiosData:
    """Define an object to hold GIOS data."""

    def __init__(self, session, station_id, **kwargs):
        """Initialize."""
        self._gios = Gios(station_id, session)
        self.station_id = station_id
        self.sensors = {}
        self.latitude = None
        self.longitude = None
        self.station_name = None
        self.available = True

        self.async_update = Throttle(kwargs[CONF_SCAN_INTERVAL])(self._async_update)

    async def _async_update(self):
        """Update GIOS data."""
        try:
            with async_timeout.timeout(20):
                await self._gios.update()
        except TimeoutError:
            _LOGGER.error("Update states failed: TimeoutError")
        except (ApiError, NoStationError, ClientConnectorError) as error:
            _LOGGER.error("Update states failed: %s", error)
        self.latitude = self._gios.latitude
        self.longitude = self._gios.longitude
        self.station_name = self._gios.station_name
        self.sensors = self._gios.data
        self.available = self._gios.available
