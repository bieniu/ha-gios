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
            stations = await self._get_stations()
            if not stations:
                return

            for station in stations:
                if station[ATTR_ID] == self.station_id:
                    self.latitude = station["gegrLat"]
                    self.longitude = station["gegrLon"]
                    self.station_name = station["stationName"]
            if not self.station_name:
                _LOGGER.error(
                    "%s is not a valid measuring station ID.", self.station_id
                )
                raise NoStationError(
                    f"{self.station_id} is not a valid measuring station ID."
                )

            station_data = await self._get_station()
            if not station_data:
                return
            for sensor in station_data:
                self._data[sensor["param"]["paramCode"]] = {
                    ATTR_ID: sensor[ATTR_ID],
                    ATTR_NAME: sensor["param"]["paramName"],
                }

        for sensor in self._data:
            if sensor != ATTR_AQI:
                sensor_data = await self._get_sensor(sensor)
                if sensor_data[0][ATTR_VALUE]:
                    self._data[sensor][ATTR_VALUE] = sensor_data[0][ATTR_VALUE]
                elif sensor_data[1][ATTR_VALUE]:
                    self._data[sensor][ATTR_VALUE] = sensor_data[0][ATTR_VALUE]

        indexes = await self._get_indexes()
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

    async def _get_stations(self):
        """Retreive list of measuring stations."""
        stations = await self._async_get(URL_STATIONS)
        return stations

    async def _get_station(self):
        """Retreive measuring station data."""
        url = URL_STATION.format(self.station_id)
        station = await self._async_get(url)
        return station

    async def _get_sensor(self, sensor):
        """Retreive sensor data."""
        url = URL_SENSOR.format(self._data[sensor][ATTR_ID])
        sensor = await self._async_get(url)
        return sensor["values"]

    async def _get_indexes(self):
        """Retreive indexes data."""
        url = URL_INDEXES.format(self.station_id)
        indexes = await self._async_get(url)
        return indexes

    async def _async_get(self, url):
        """Retreive data from GIOS API."""
        data = None
        try:
            async with self.session.get(url) as resp:
                if resp.status != HTTP_OK:
                    _LOGGER.warning("Invalid response from GIOS API: %s", resp.status)
                    raise ApiError(await resp.text())
                data = await resp.json()
        except ClientError as error:
            _LOGGER.error("Invalid response from from GIOS API: %s", error)
            return
        _LOGGER.debug("Data retrieved from %s, status: %s", url, resp.status)
        return data

    @property
    def data(self):
        """Return the data."""
        return self._data

    @property
    def available(self):
        """Return True is data is available."""
        if len(self._data) > 1:
            self._available = True
        else:
            self._available = False
        return self._available


class ApiError(Exception):
    """Raised when GIOS API request ended in error."""

    def __init__(self, status):
        """Initialize."""
        super(ApiError, self).__init__(status)
        self.status = status


class NoStationError(Exception):
    """Raised when no measuring station error."""

    def __init__(self, status):
        """Initialize."""
        super(NoStationError, self).__init__(status)
        self.status = status
