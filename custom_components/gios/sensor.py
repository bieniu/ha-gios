"""
Support for the GIOŚ service.

For more details about this platform, please refer to the documentation at
https://github.com/bieniu/ha-gios
"""

from datetime import timedelta
import logging
import aiohttp

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL, HTTP_OK, ATTR_ATTRIBUTION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .const import DEFAULT_NAME, CONF_STATION_ID, STATIONS_URL, ATTR_ID

_LOGGER = logging.getLogger(__name__)

__VERSION__ = "0.2.4"

STATION_URL = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}"
SENSOR_URL = "http://api.gios.gov.pl/pjp-api/rest/data/getData/{}"
INDEXES_URL = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}"

CONF_IGNORED_CONDITIONS = "ignored_conditions"

DEFAULT_ATTRIBUTION = {"Data provided by GIOŚ"}
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)

VOLUME_MICROGRAMS_PER_CUBIC_METER = "µg/m³"
ICON = "mdi:blur"

ATTR_PM10 = "PM10"
ATTR_PM25 = "PM25"
ATTR_NO2 = "NO2"
ATTR_C6H6 = "C6H6"
ATTR_SO2 = "SO2"
ATTR_O3 = "O3"
ATTR_CO = "CO"
ATTR_AQI = "AQI"
ATTR_NAME = "name"
ATTR_INDEX = "index"
ATTR_VALUE = "value"
ATTR_VALUES = "values"
ATTR_PARAM = "param"
ATTR_PARAM_NAME = "paramName"
ATTR_PARAM_CODE = "paramCode"
ATTR_INDEX_LEVEL = "{}IndexLevel"
ATTR_INDEX_LEVEL_NAME = "indexLevelName"
ATTR_STATION_NAME = "stationName"
ATTR_GEGR_LAT = "gegrLat"
ATTR_GEGR_LON = "gegrLon"
ATTR_ST_INDEX_LEVEL = "stIndexLevel"
ATTR_STATION = "station"

SENSOR_TYPES = {
    ATTR_PM10.lower(),
    ATTR_PM25.lower(),
    ATTR_NO2.lower(),
    ATTR_C6H6.lower(),
    ATTR_SO2.lower(),
    ATTR_O3.lower(),
    ATTR_CO.lower(),
    ATTR_AQI.lower(),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_ID, None): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_IGNORED_CONDITIONS, default=[]): vol.All(
            cv.ensure_list, [vol.In(SENSOR_TYPES)]
        ),
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configure the platform and add the sensors."""
    name = config.get(CONF_NAME)
    station_id = config.get(CONF_STATION_ID)
    _LOGGER.debug("Using station_id: %s", station_id)

    data = GiosData(station_id, scan_interval=config[CONF_SCAN_INTERVAL])

    await data.async_update()

    sensors = []
    ignored_conditions = config[CONF_IGNORED_CONDITIONS]
    for sensor in data.sensors:
        if not sensor.replace(".", "").lower() in ignored_conditions:
            sensors.append(GiosSensor(name, sensor, data))
    async_add_entities(sensors, True)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a GIOS entities from a config_entry."""
    station_id = config_entry.data[CONF_STATION_ID]
    name = config_entry.data[CONF_NAME]
    scan_interval = DEFAULT_SCAN_INTERVAL
    _LOGGER.debug("Using station_id: %s", station_id)

    data = GiosData(station_id, scan_interval=scan_interval)

    await data.async_update()

    sensors = []
    for sensor in data.sensors:
        sensors.append(GiosSensor(name, sensor, data))
    async_add_entities(sensors, True)


class GiosSensor(Entity):
    """Define an GIOS sensor."""

    def __init__(self, name, kind, data):
        """Initialize."""
        self._name = name
        self.kind = kind
        self.gios = data
        self._state = None
        self._attrs = {ATTR_ATTRIBUTION: DEFAULT_ATTRIBUTION}
        self._icon = ICON
        self._unit_of_measurement = VOLUME_MICROGRAMS_PER_CUBIC_METER

    @property
    def state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_STATION] = self.gios.station_name
        if self.kind != ATTR_AQI:
            self._attrs[ATTR_INDEX] = self.gios.sensors[self.kind][ATTR_INDEX]
            self._attrs[ATTR_NAME] = self.gios.sensors[self.kind][ATTR_NAME]
        return self._attrs

    @property
    def name(self):
        """Return the name."""
        return "{} {}".format(self._name, self.kind)

    @property
    def icon(self):
        """Return the icon."""
        if self.kind == ATTR_AQI:
            if self._state == "bardzo dobry":
                self._icon = "mdi:emoticon-excited"
            elif self._state == "dobry":
                self._icon = "mdi:emoticon-happy"
            elif self._state == "umiarkowany":
                self._icon = "mdi:emoticon-neutral"
            elif self._state == "dostateczny":
                self._icon = "mdi:emoticon-sad"
            elif self._state == "zły":
                self._icon = "mdi:emoticon-dead"
        return self._icon

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return "{}-{}-{}".format(self.gios.latitude, self.gios.longitude, self.kind)

    @property
    def state(self):
        """Return the state."""
        self._state = self.gios.sensors[self.kind][ATTR_VALUE]
        if self._state:
            if self.kind != ATTR_AQI:
                self._state = round(self._state)
            return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self.kind != ATTR_AQI:
            return self._unit_of_measurement

    async def async_update(self):
        """Get the data from GIOS."""
        await self.gios.async_update()

        if not self.gios.sensors[self.kind][ATTR_VALUE]:
            _LOGGER.error("No value for %s sensor value in GIOS data!", self.kind)
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

        self.async_update = Throttle(kwargs[CONF_SCAN_INTERVAL])(self._async_update)

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
                _LOGGER.error(
                    "Wrong station_id. There is no station %s!", self.station_id
                )

        url = STATION_URL.format(self.station_id)
        station_data = await self.async_retreive_data(url)
        _LOGGER.debug("Station %s data retrieved", self.station_id)
        if station_data:
            for sensor in station_data:
                self.sensors[sensor[ATTR_PARAM][ATTR_PARAM_CODE]] = {
                    ATTR_ID: sensor[ATTR_ID],
                    ATTR_NAME: sensor[ATTR_PARAM][ATTR_PARAM_NAME],
                }

        for sensor in self.sensors:
            if sensor != ATTR_AQI:
                url = SENSOR_URL.format(self.sensors[sensor][ATTR_ID])
                sensor_data = await self.async_retreive_data(url)
                _LOGGER.debug("Sensor %s data retrieved", self.sensors[sensor][ATTR_ID])
                if sensor_data:
                    if sensor_data[ATTR_VALUES][0][ATTR_VALUE]:
                        self.sensors[sensor][ATTR_VALUE] = sensor_data[ATTR_VALUES][0][
                            ATTR_VALUE
                        ]
                    else:
                        self.sensors[sensor][ATTR_VALUE] = sensor_data[ATTR_VALUES][1][
                            ATTR_VALUE
                        ]

        url = INDEXES_URL.format(self.station_id)
        indexes_data = await self.async_retreive_data(url)
        _LOGGER.debug("Indexes data retrieved")
        if indexes_data:
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

    async def async_retreive_data(self, url):
        """Retreive data from GIOS site via aiohttp."""
        data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except aiohttp.ClientError as error:
            _LOGGER.error("Could not fetch data: %s", error)
        _LOGGER.debug("Data retrieved from GIOS, status: %s", resp.status)
        if resp.status != HTTP_OK:
            _LOGGER.error("Could not fetch data, status: %s", resp.status)
        return data
