from datetime import timedelta
import logging
import aiohttp

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_SCAN_INTERVAL, HTTP_OK,
                                 ATTR_ATTRIBUTION)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

__VERSION__ = '0.0.3'

STATIONS_URL = 'http://api.gios.gov.pl/pjp-api/rest/station/findAll'
STATION_URL = 'http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}'
SENSOR_URL = 'http://api.gios.gov.pl/pjp-api/rest/data/getData/{}'
INDEXES_URL = 'http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}'

CONF_STATION_ID = 'station_id'

DEFAULT_NAME = 'GIOŚ'
DEFAULT_ATTRIBUTION = {"Dane dostarczone przez GIOŚ"}
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

VOLUME_MICROGRAMS_PER_CUBIC_METER = 'µg/m³'
ICON = 'mdi:blur'

ATTR_NAME = 'name'
ATTR_INDEX = 'index'
ATTR_VALUE = 'value'
ATTR_VALUES = 'values'
ATTR_ID = 'id'
ATTR_PARAM = 'param'
ATTR_PARAM_NAME = 'paramName'
ATTR_PARAM_CODE = 'paramCode'
ATTR_INDEX_LEVEL = '{}IndexLevel'
ATTR_INDEX_LEVEL_NAME = 'indexLevelName'
ATTR_STATION_NAME = 'stationName'
ATTR_GEGR_LAT = 'gegrLat'
ATTR_GEGR_LON = 'gegrLon'
ATTR_NAME_PL = 'nazwa'
ATTR_INDEX_PL = 'indeks'
ATTR_STATION_PL = 'stacja'
ATTR_LATITUDE_PL = 'szerokość geograficzna'
ATTR_LONGITUDE_PL = 'długość geograficzna'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_STATION_ID, None): cv.positive_int,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL):
        cv.time_period
})


async def async_setup_platform(
        hass, config, async_add_entities, discovery_info=None):
    """Configure the platform and add the sensors."""

    name = config.get(CONF_NAME)
    station_id = config.get(CONF_STATION_ID)
    _LOGGER.debug("Using station_id: %s", station_id)

    data = GiosData(station_id, scan_interval=config[CONF_SCAN_INTERVAL])

    await data.async_update()

    sensors = []
    for sensor in data.sensors:
        sensors.append(GiosSensor(name, sensor, data))
    async_add_entities(sensors, True)


class GiosSensor(Entity):
    """Define an GIOS sensor."""

    def __init__(self, name, type, data):
        """Initialize."""
        self._name = name
        self.type = type
        self.gios = data
        self._state = None
        self._attrs = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._icon = ICON
        self._unit_of_measurement = VOLUME_MICROGRAMS_PER_CUBIC_METER

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        self._attrs[ATTR_NAME_PL] = self.gios.sensors[self.type][ATTR_NAME]
        self._attrs[ATTR_INDEX_PL] = self.gios.sensors[self.type][ATTR_INDEX]
        self._attrs[ATTR_STATION_PL] = self.gios.station_name
        self._attrs[ATTR_LATITUDE_PL] = self.gios.latitude
        self._attrs[ATTR_LONGITUDE_PL] = self.gios.longitude
        return self._attrs

    @property
    def name(self):
        """Return the name."""
        return '{} {}'.format(self._name, self.type)

    @property
    def icon(self):
        """Return the icon."""
        return self._icon

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return '{}-{}-{}'.format(self.gios.latitude, self.gios.longitude,
                                 self.type)

    @property
    def state(self):
        """Return the state."""
        self._state = self.gios.sensors[self.type][ATTR_VALUE]
        _LOGGER.debug("State: %s", self._state)
        if self._state:
            self._state = round(self._state)
            return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    async def async_update(self):
        """Get the data from Airly."""
        await self.gios.async_update()

        if not self.gios.sensors[self.type][ATTR_VALUE]:
            return


class GiosData:
    """Define an object to hold sensors data."""

    def __init__(self, station_id, **kwargs):
        """Initialize."""
        self.station_id = station_id
        self.sensors = {}
        self.latitude = None
        self.longitude = None
        self.station_name = None

        self.async_update = Throttle(
            kwargs[CONF_SCAN_INTERVAL])(self._async_update)

    async def _async_update(self):
        """Update GIOS data."""
        station_available = False
        stations = await self.async_retreive_data(STATIONS_URL)
        _LOGGER.debug("All stations data retrieved")
        if stations:
            for station in stations:
                if station[ATTR_ID] == self.station_id:
                    station_available = True
                    self.latitude = station[ATTR_GEGR_LAT]
                    self.longitude = station[ATTR_GEGR_LON]
                    self.station_name = station[ATTR_STATION_NAME]
            if not station_available:
                _LOGGER.error("Wrong station_id. There is no station %s!",
                              self.station_id)
                return

        url = STATION_URL.format(self.station_id)
        station_data = await self.async_retreive_data(url)
        _LOGGER.debug("Station %s data retrieved", self.station_id)
        if station_data:
            for i in range(len(station_data)):
                self.sensors[station_data[i][ATTR_PARAM][ATTR_PARAM_CODE]] = {
                    ATTR_ID: station_data[i][ATTR_ID],
                    ATTR_NAME: station_data[i][ATTR_PARAM][ATTR_PARAM_NAME]
                }

        for sensor in self.sensors:
            url = SENSOR_URL.format(self.sensors[sensor][ATTR_ID])
            sensor_data = await self.async_retreive_data(url)
            _LOGGER.debug("Sensor %s data retrieved",
                          self.sensors[sensor][ATTR_ID])
            if sensor_data:
                self.sensors[sensor][ATTR_VALUE] = (sensor_data[ATTR_VALUES][0]
                        [ATTR_VALUE])

        url = INDEXES_URL.format(self.station_id)
        indexes_data = await self.async_retreive_data(url)
        _LOGGER.debug("Indexes data retrieved")
        if indexes_data:
            for sensor in self.sensors:
                index_level = (ATTR_INDEX_LEVEL.format(sensor.lower()
                        .replace('.','')))
                self.sensors[sensor][ATTR_INDEX] = (indexes_data[index_level]
                        [ATTR_INDEX_LEVEL_NAME].lower())

    async def async_retreive_data(self, url):
        """Retreive data from GIOS site via aiohttp."""
        data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except aiohttp.ClientError as error:
            _LOGGER.error("Could not fetch data: %s", error)
            return
        _LOGGER.debug("Data retrieved from GIOS, status: %s", resp.status)
        if resp.status == HTTP_OK:
            return data
        else:
            _LOGGER.error("Could not fetch data, status: %s", resp.status)