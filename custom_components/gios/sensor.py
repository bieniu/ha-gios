"""
Support for the GIOŚ service.

For more details about this platform, please refer to the documentation at
https://github.com/bieniu/ha-gios
"""
import asyncio
import logging
from datetime import timedelta

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME, CONF_SCAN_INTERVAL, HTTP_OK
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle

from .const import (
    _LOGGER,
    ATTR_ID,
    CONF_STATION_ID,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    STATIONS_URL,
)

_LOGGER = logging.getLogger(__name__)

ATTR_AQI = "AQI"
ATTR_C6H6 = "C6H6"
ATTR_CO = "CO"
ATTR_GEGR_LAT = "gegrLat"
ATTR_GEGR_LON = "gegrLon"
ATTR_INDEX = "index"
ATTR_INDEX_LEVEL = "{}IndexLevel"
ATTR_INDEX_LEVEL_NAME = "indexLevelName"
ATTR_NAME = "name"
ATTR_NO2 = "NO2"
ATTR_O3 = "O3"
ATTR_PARAM = "param"
ATTR_PARAM_CODE = "paramCode"
ATTR_PARAM_NAME = "paramName"
ATTR_PM10 = "PM10"
ATTR_PM25 = "PM25"
ATTR_SO2 = "SO2"
ATTR_ST_INDEX_LEVEL = "stIndexLevel"
ATTR_STATION = "station"
ATTR_STATION_NAME = "stationName"
ATTR_VALUE = "value"
ATTR_VALUES = "values"

DEFAULT_ATTRIBUTION = {"Data provided by GIOŚ"}
DEFAULT_ICON = "mdi:blur"

INDEXES_URL = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}"
SENSOR_URL = "http://api.gios.gov.pl/pjp-api/rest/data/getData/{}"
STATION_URL = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}"

VOLUME_MICROGRAMS_PER_CUBIC_METER = "µg/m³"

SENSOR_TYPES = {
    ATTR_AQI.lower(),
    ATTR_C6H6.lower(),
    ATTR_CO.lower(),
    ATTR_NO2.lower(),
    ATTR_O3.lower(),
    ATTR_PM10.lower(),
    ATTR_PM25.lower(),
    ATTR_SO2.lower(),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_ID, None): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configure the platform and add the sensors."""
    del config[CONF_SCAN_INTERVAL]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config
        )
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a GIOS entities from a config_entry."""
    station_id = config_entry.data[CONF_STATION_ID]
    name = config_entry.data[CONF_NAME]
    try:
        scan_interval = config_entry.options[CONF_SCAN_INTERVAL]
    except KeyError:
        scan_interval = DEFAULT_SCAN_INTERVAL
    _LOGGER.debug("Using station_id: %s", station_id)

    data = GiosData(station_id, scan_interval=timedelta(seconds=scan_interval))

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
        self._icon = DEFAULT_ICON
        self._unit_of_measurement = VOLUME_MICROGRAMS_PER_CUBIC_METER

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_STATION] = self.gios.station_name
        if self.kind != ATTR_AQI:
            if self.gios.sensors[self.kind][ATTR_INDEX]:
                self._attrs[ATTR_INDEX] = self.gios.sensors[self.kind][ATTR_INDEX]
                self._attrs[ATTR_NAME] = self.gios.sensors[self.kind][ATTR_NAME]
        return self._attrs

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} {self.kind}"

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
        return f"{self.gios.latitude}-{self.gios.longitude}-{self.kind}"

    @property
    def state(self):
        """Return the state."""
        try:
            self._state = self.gios.sensors[self.kind][ATTR_VALUE]
            if isinstance(self._state, float):
                self._state = round(self._state)
        except (KeyError, ValueError):
            _LOGGER.error("No data for %s", [self.kind])
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self.kind != ATTR_AQI:
            return self._unit_of_measurement

    @property
    def available(self):
        """Return True if entity is available."""
        _LOGGER.debug(f"{self.kind}: {bool(self.gios.sensors)}")
        return bool(self.gios.sensors)

    async def async_update(self):
        """Get the data from GIOS."""
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
                except (ValueError, IndexError):
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
        except (TypeError, IndexError):
            _LOGGER.warning("Incomplete indexes data.")

    async def _async_retreive_data(self, url):
        """Retreive data from GIOS site via aiohttp."""
        data = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()
        except aiohttp.ClientError as error:
            _LOGGER.error("Could not fetch data: %s", error)
            return
        if resp.status != HTTP_OK:
            _LOGGER.error("Could not fetch data, status: %s", resp.status)
        else:
            _LOGGER.debug("Data retrieved from GIOS, status: %s", resp.status)
        return data
