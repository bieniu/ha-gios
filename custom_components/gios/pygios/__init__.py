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
        self.data = {}
        self.station_id = station_id
        self.latitude = None
        self.longitude = None
        self.station_name = None
        self._station_data = {}

        self.session = session

    async def update(self):  # pylint: disable=too-many-branches
        """Update GIOS data."""
        data = {}

        if not self.station_name:
            stations = await self._get_stations()
            if not stations:
                _LOGGER.error("Invalid measuring stations list from GIOS API.")
                return

            for station in stations:
                if station[ATTR_ID] == self.station_id:
                    self.latitude = station["gegrLat"]
                    self.longitude = station["gegrLon"]
                    self.station_name = station["stationName"]
            if not self.station_name:
                raise NoStationError(
                    f"{self.station_id} is not a valid measuring station ID."
                )

            self._station_data = await self._get_station()

        if not self._station_data:
            _LOGGER.error("Invalid measuring station data from GIOS API.")
            self.station_name = None
            self.data = {}
            return
        try:
            for sensor in self._station_data:
                data[sensor["param"]["paramCode"]] = {
                    ATTR_ID: sensor[ATTR_ID],
                    ATTR_NAME: sensor["param"]["paramName"],
                }
        except (IndexError, TypeError):
            _LOGGER.error("Invalid sensor data from GIOS API.")
            self.data = {}
            return

        try:
            for sensor in data:
                sensor_data = await self._get_sensor(data[sensor][ATTR_ID])
                if sensor_data["values"][0][ATTR_VALUE]:
                    data[sensor][ATTR_VALUE] = sensor_data["values"][0][ATTR_VALUE]
                elif sensor_data["values"][1][ATTR_VALUE]:
                    data[sensor][ATTR_VALUE] = sensor_data["values"][1][ATTR_VALUE]
                else:
                    raise ValueError
        except (ValueError, IndexError, TypeError):
            _LOGGER.error("Invalid sensor data from GIOS API.")
            self.data = {}
            return

        indexes = await self._get_indexes()
        try:
            for sensor in data:
                index_level = ATTR_INDEX_LEVEL.format(sensor.lower().replace(".", ""))
                data[sensor][ATTR_INDEX] = indexes[index_level][
                    "indexLevelName"
                ].lower()

            data[ATTR_AQI] = {ATTR_NAME: ATTR_AQI}
            data[ATTR_AQI][ATTR_VALUE] = indexes["stIndexLevel"][
                "indexLevelName"
            ].lower()
        except (IndexError, TypeError):
            _LOGGER.error("Invalid index data from GIOS API")
            self.data = {}
            return
        self.data = data

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
        url = URL_SENSOR.format(sensor)
        sensor = await self._async_get(url)
        return sensor

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
                    raise ApiError(resp.status)
                data = await resp.json()
        except ClientError as error:
            _LOGGER.error("Invalid response from from GIOS API: %s", error)
            return
        _LOGGER.debug("Data retrieved from %s, status: %s", url, resp.status)
        return data

    @property
    def available(self):
        """Return True is data is available."""
        return bool(self.data)


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
