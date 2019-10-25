"""
Python wrapper for getting air quality data from GIOS.
"""
import aiohttp
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

INDEXES_URL = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}"
SENSOR_URL = "http://api.gios.gov.pl/pjp-api/rest/data/getData/{}"
STATION_URL = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}"
STATIONS_URL = "http://api.gios.gov.pl/pjp-api/rest/station/findAll"
HTTP_OK = "200"

ATTR_AQI = "AQI"
ATTR_ID = "id"
ATTR_INDEX = "index"
ATTR_NAME = "name"
ATTR_STATION = "station"
ATTR_VALUE = "value"
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

class Gios():
    """Main class to perform GIOS API requests"""

    def __init__(self, station_id, session: aiohttp.ClientSession):
        self._data = {}
        self._available = False
        self._station_id = station_id
        self._latitude = None
        self._longitude = None
        self._station_name = None

        self.session = session

    async def update(self):
        stations = await self._async_get(STATIONS_URL)
        if not stations:
            return

        for station in stations:
            if station[ATTR_ID] == self._station_id:
                self._latitude = station[ATTR_GEGR_LAT]
                self._longitude = station[ATTR_GEGR_LON]
                self._station_name = station[ATTR_STATION_NAME]

        url = STATION_URL.format(self._station_id)
        station_data = await self._async_get(url)
        if not station_data:
            return
        for sensor in station_data:
            self._data[sensor[ATTR_PARAM][ATTR_PARAM_CODE]] = {
                ATTR_ID: sensor[ATTR_ID],
                ATTR_NAME: sensor[ATTR_PARAM][ATTR_PARAM_NAME],
            }

        for sensor in self._data:
            if sensor != ATTR_AQI:
                url = SENSOR_URL.format(self._data[sensor][ATTR_ID])
                sensor_data = await self._async_get(url)
                sensor_data = sensor_data[ATTR_VALUES]
                self._data[sensor][ATTR_VALUE] = sensor_data[0][ATTR_VALUE]


    async def _async_get(self, url):
        """Retreive data from GIOS site via aiohttp."""
        data = None
        # try:
        async with self.session.get(url) as response:
            data = await response.json()
        # except aiohttp.ClientError as error:
        #     _LOGGER.error("Could not fetch data from %s, error: %s", url, error)
        #     return
        # if resp.status != HTTP_OK:
        #     _LOGGER.error("Could not fetch data from %s, status: %s", url, resp.status)
        # else:
        #     _LOGGER.debug("Data retrieved from %s, status: %s", url, resp.status)
        return data

    @property
    def data(self):
        return self._data

    @property
    def available(self):
        if len(self._data) > 0:
            self._available = True
        else:
            self._available = False
        return self._available

    @property
    def latitude(self):
        return self._latitude

    @property
    def longitude(self):
        return self._longitude

    @property
    def station_name(self):
        return self._station_name

# class GiosError(Exception):
#     """Raised when GIOS API request ended in error."""

#     def __init__(self, status_code, status):
#         self.status_code = status_code
#         self.status = status
