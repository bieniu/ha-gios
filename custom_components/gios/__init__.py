"""The GIOS component."""
import logging
from datetime import timedelta

import aiohttp

from homeassistant.const import CONF_SCAN_INTERVAL, HTTP_OK
from homeassistant.core import Config, HomeAssistant
from homeassistant.util import Throttle

from .const import (
    ATTR_AQI,
    ATTR_ID,
    ATTR_INDEX,
    ATTR_NAME,
    ATTR_STATION,
    ATTR_VALUE,
    CONF_STATION_ID,
    DATA_CLIENT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STATIONS_URL,
)

INDEXES_URL = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}"
SENSOR_URL = "http://api.gios.gov.pl/pjp-api/rest/data/getData/{}"
STATION_URL = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}"

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

    gios = GiosData(station_id, scan_interval=timedelta(seconds=scan_interval))

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
    """Define an object to hold sensors data."""

    def __init__(self, station_id, **kwargs):
        """Initialize."""
        self.station_id = station_id
        self.sensors = {}
        self.latitude = None
        self.longitude = None
        self.station_name = None

        self.async_update = Throttle(kwargs[CONF_SCAN_INTERVAL])(self._async_update)

    async def _async_update(self):
        """Update GIOS data."""
        station_available = False
        stations = await self._async_retreive_data(STATIONS_URL)
        if not stations:
            self.sensors = {}
            return
        _LOGGER.debug("All stations data retrieved")
        for station in stations:
            if station[ATTR_ID] == self.station_id:
                station_available = True
                self.latitude = station[ATTR_GEGR_LAT]
                self.longitude = station[ATTR_GEGR_LON]
                self.station_name = station[ATTR_STATION_NAME]
        if not station_available:
            _LOGGER.error("Wrong station_id. There is no station %s!", self.station_id)
            self.sensors = {}
            return

        url = STATION_URL.format(self.station_id)
        station_data = await self._async_retreive_data(url)
        if not station_data:
            self.sensors = {}
            return
        _LOGGER.debug("Station %s data retrieved", self.station_id)
        for sensor in station_data:
            self.sensors[sensor[ATTR_PARAM][ATTR_PARAM_CODE]] = {
                ATTR_ID: sensor[ATTR_ID],
                ATTR_NAME: sensor[ATTR_PARAM][ATTR_PARAM_NAME],
            }

        for sensor in self.sensors:
            if sensor != ATTR_AQI:
                url = SENSOR_URL.format(self.sensors[sensor][ATTR_ID])
                sensor_data = await self._async_retreive_data(url)
                try:
                    sensor_data = sensor_data[ATTR_VALUES]
                    if sensor_data[0][ATTR_VALUE]:
                        self.sensors[sensor][ATTR_VALUE] = sensor_data[0][ATTR_VALUE]
                    elif sensor_data[1][ATTR_VALUE]:
                        self.sensors[sensor][ATTR_VALUE] = sensor_data[1][ATTR_VALUE]
                    else:
                        raise ValueError
                    _LOGGER.debug(
                        "Sensor %s data retrieved", self.sensors[sensor][ATTR_ID]
                    )
                except (ValueError, IndexError, TypeError):
                    _LOGGER.error("Incomplete sensors data.")
                    self.sensors = {}
                    return

        url = INDEXES_URL.format(self.station_id)
        indexes_data = await self._async_retreive_data(url)
        _LOGGER.debug("Indexes data retrieved")
        try:
            for sensor in self.sensors:
                if sensor != ATTR_AQI:
                    index_level = ATTR_INDEX_LEVEL.format(
                        sensor.lower().replace(".", "")
                    )
                    self.sensors[sensor][ATTR_INDEX] = indexes_data[index_level][
                        ATTR_INDEX_LEVEL_NAME
                    ].lower()

            self.sensors[ATTR_AQI] = {ATTR_NAME: ATTR_AQI}
            self.sensors[ATTR_AQI][ATTR_VALUE] = indexes_data[ATTR_ST_INDEX_LEVEL][
                ATTR_INDEX_LEVEL_NAME
            ].lower()
        except (TypeError, IndexError, TypeError):
            self.sensors = {}
            _LOGGER.error("Incomplete indexes data.")

    async def _async_retreive_data(self, url):
        """Retreive data from GIOS site via aiohttp."""
        data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except aiohttp.ClientError as error:
            _LOGGER.error("Could not fetch data from %s, error: %s", url, error)
            return
        if resp.status != HTTP_OK:
            _LOGGER.error("Could not fetch data from %s, status: %s", url, resp.status)
        else:
            _LOGGER.debug("Data retrieved from %s, status: %s", url, resp.status)
        return data
