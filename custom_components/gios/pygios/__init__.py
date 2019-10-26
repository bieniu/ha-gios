"""
Python wrapper for getting air quality data from GIOS.
"""
import logging

from aiohttp import ClientError

_LOGGER = logging.getLogger(__name__)

ATTR_AQI = "AQI"
ATTR_ID = "id"
ATTR_INDEX = "index"
ATTR_INDEX_LEVEL = "{}IndexLevel"
ATTR_NAME = "name"
ATTR_VALUE = "value"

HTTP_OK = 200
URL_INDEXES = "http://api.gios.gov.pl/pjp-api/rest/aqindex/getIndex/{}"
URL_SENSOR = "http://api.gios.gov.pl/pjp-api/rest/data/getData/{}"
URL_STATION = "http://api.gios.gov.pl/pjp-api/rest/station/sensors/{}"
URL_STATIONS = "http://api.gios.gov.pl/pjp-api/rest/station/findAll"


class Gios:
    """Main class to perform GIOS API requests"""

    def __init__(self, station_id, session):
        """Initialize."""
        self._data = {}
        self._available = False
        self.station_id = station_id
        self.latitude = None
        self.longitude = None
        self.station_name = None

        self.session = session

    async def update(self):
        """Update GIOS data."""
        if not self.station_name:
            stations = await self._async_get(URL_STATIONS)
            if not stations:
                return

            for station in stations:
                if station[ATTR_ID] == self.station_id:
                    self.latitude = station["gegrLat"]
                    self.longitude = station["gegrLon"]
                    self.station_name = station["stationName"]

            url = URL_STATION.format(self.station_id)
            station_data = await self._async_get(url)
            if not station_data:
                return
            for sensor in station_data:
                self._data[sensor["param"]["paramCode"]] = {
                    ATTR_ID: sensor[ATTR_ID],
                    ATTR_NAME: sensor["param"]["paramName"],
                }

        for sensor in self._data:
            if sensor != ATTR_AQI:
                url = URL_SENSOR.format(self._data[sensor][ATTR_ID])
                sensor_data = await self._async_get(url)
                sensor_data = sensor_data["values"]
                self._data[sensor][ATTR_VALUE] = sensor_data[0][ATTR_VALUE]

        url = URL_INDEXES.format(self.station_id)
        indexes = await self._async_get(url)
        try:
            for sensor in self._data:
                if sensor != ATTR_AQI:
                    index_level = ATTR_INDEX_LEVEL.format(
                        sensor.lower().replace(".", "")
                    )
                    self._data[sensor][ATTR_INDEX] = indexes[index_level][
                        "indexLevelName"
                    ].lower()

            self._data[ATTR_AQI] = {ATTR_NAME: ATTR_AQI}
            self._data[ATTR_AQI][ATTR_VALUE] = indexes["stIndexLevel"][
                "indexLevelName"
            ].lower()
        except (TypeError, IndexError, TypeError):
            _LOGGER.error("Invalid data from GIOS API")

    async def _async_get(self, url):
        """Retreive data from GIOS API."""
        data = None
        try:
            async with self.session.get(url) as response:
                if response.status != HTTP_OK:
                    _LOGGER.warning(
                        "Invalid response from GIOS API: %s", response.status
                    )
                    raise GiosError(response.status, await response.text())
                data = await response.json()
        except ClientError as error:
            _LOGGER.error("Invalid response from from GIOS API: %s", error)
            return
        _LOGGER.debug("Data retrieved from %s, status: %s", url, response.status)
        return data

    @property
    def data(self):
        """Return the data."""
        return self._data

    @property
    def available(self):
        """Return True is data is available."""
        if len(self._data) > 0:
            self._available = True
        else:
            self._available = False
        return self._available


class GiosError(Exception):
    """Raised when GIOS API request ended in error."""

    def __init__(self, status_code, status):
        """Initialize."""
        Exception.__init__(self, status_code, status)
        self.status_code = status_code
        self.status = status
