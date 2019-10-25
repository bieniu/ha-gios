import aiohttp
import asyncio

from pygios import Gios


async def main():
    async with aiohttp.ClientSession() as websession:
        gios = Gios(11794, websession)
        await gios.update()
        data = gios.data
        available = gios.available
        latitude = gios.latitude
        longitude = gios.longitude
        station_name = gios.station_name

    print(f"Data available: {available}")
    print(f"Longitude: {longitude}, latitude: {latitude}, station name: {station_name}")
    print(data)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()