from datetime import timedelta
import logging
import aiohttp

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_SCAN_INTERVAL, HTTP_OK,
                                 CONTENT_TYPE_JSON, ATTR_ATTRIBUTION)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

__VERSION__ = '0.0.1'

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
        self._attrs['nazwa'] = self._state = self.gios.sensors[self.type]['name']
        self._attrs['indeks'] = self._state = self.gios.sensors[self.type]['index']
        self._attrs['stacja'] = self.gios.station_name
        self._attrs['szerokość geograficzna'] = self.gios.latitude
        self._attrs['długość geograficzna'] = self.gios.longitude
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
        self._state = self.gios.sensors[self.type]['value']
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
        async with aiohttp.ClientSession() as session:
            async with session.get(STATIONS_URL) as resp:
                stations = await resp.json()
        _LOGGER.debug("Stations data retrieved: %s", resp.status)
        if resp.status == HTTP_OK:
            for station in stations:
                if station['id'] == self.station_id:
                    self.latitude = station['gegrLat']
                    self.longitude = station['gegrLon']
                    self.station_name = station['stationName']

        async with aiohttp.ClientSession() as session:
            async with session.get(STATION_URL.format(self.station_id)) as resp:
                station_data = await resp.json()
        _LOGGER.debug("Station %s data retrieved: %s", self.station_id, resp.status)
        if resp.status == HTTP_OK:
            for i in range(len(station_data)):
                self.sensors[station_data[i]['param']['paramCode']] = {'id': station_data[i]['id'], 'name': station_data[i]['param']['paramName']}

        for sensor in self.sensors:
            async with aiohttp.ClientSession() as session:
                async with session.get(SENSOR_URL.format(self.sensors[sensor]['id'])) as resp:
                    sensor_data = await resp.json()
            _LOGGER.debug("Sensor data retrieved: %s", resp.status)
            if resp.status == HTTP_OK:
                self.sensors[sensor]['value'] = sensor_data['values'][0]['value']

        async with aiohttp.ClientSession() as session:
            async with session.get(INDEXES_URL.format(self.station_id)) as resp:
                indexes_data = await resp.json()
        _LOGGER.debug("Indexes data retrieved: %s", resp.status)
        if resp.status == HTTP_OK:
            for sensor in self.sensors:
                self.sensors[sensor]['index'] = indexes_data['{}IndexLevel'.format(sensor.lower().replace('.',''))]['indexLevelName'].lower()