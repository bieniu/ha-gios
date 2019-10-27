import asyncio

from aiohttp import ClientSession
from pygios import Gios, ApiError, NoStationError

GIOS_STATION_ID = 11794


async def main():
    try:
        async with ClientSession() as websession:
            gios = Gios(GIOS_STATION_ID, websession)
            await gios.update()
    except (ApiError, NoStationError) as error:
        print(f"{error}")
        return

    data = gios.data
    available = gios.available
    latitude = gios.latitude
    longitude = gios.longitude
    station_name = gios.station_name

    if available:
        print(f"Data available: {available}")
        print(
            f"Longitude: {longitude}, latitude: {latitude}, station name: {station_name}"
        )
        print(data)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
