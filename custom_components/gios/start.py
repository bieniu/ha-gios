from aiohttp import ClientSession
import asyncio

from pygios import Gios
from pygios import GiosError


async def main():
    try:
        async with ClientSession() as websession:
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

            await gios.update()

            print(f"Data available: {available}")
            print(f"Longitude: {longitude}, latitude: {latitude}, station name: {station_name}")
            print(data)
    except GiosError:
        print(f"{GiosError.status_code}, {GiosError.status}")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()