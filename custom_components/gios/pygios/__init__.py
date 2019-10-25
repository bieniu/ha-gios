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
HTTP_OK = "200"

class Gios():
    """Main class to perform GIOS API requests"""

    def __init__(self, station_id, session: aiohttp.ClientSession):
        self.data = None
        self.availabe = False
        self.station_id = station_id

    async def update(self):
        data = await self._async_get(STATION_URL.format(self.station_id))
        return data

    async def _async_get(self, url):
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

# class GiosError(Exception):
#     """Raised when GIOS API request ended in error."""

#     def __init__(self, status_code, status):
#         self.status_code = status_code
#         self.status = status
