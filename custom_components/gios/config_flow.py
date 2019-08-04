"""Adds config flow for GIOS."""
import aiohttp
import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant import config_entries, data_entry_flow

from .const import DOMAIN, DEFAULT_NAME, CONF_STATION_ID, ATTR_ID, STATIONS_URL


@callback
def configured_instances(hass):
    """Return a set of configured GIOS instances."""
    return set(
        entry.data[CONF_NAME] for entry in hass.config_entries.async_entries(DOMAIN)
    )


@config_entries.HANDLERS.register(DOMAIN)
class GiosFlowHandler(data_entry_flow.FlowHandler):
    """Config flow for GIOS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            station_id_valid = await self._test_station_id(user_input["station_id"])
            if station_id_valid:
                if user_input[CONF_NAME] not in configured_instances(self.hass):
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )
                self._errors[CONF_NAME] = "name_exists"
            else:
                self._errors["base"] = "wrong_station_id"

        return await self._show_config_form(name=DEFAULT_NAME, station_id="")

    async def _show_config_form(self, name=None, station_id=None):
        """Show the configuration form to edit data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION_ID, default=station_id): int,
                    vol.Optional(CONF_NAME, default=name): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_station_id(self, station_id):
        """Return true if station_id is valid."""

        async with aiohttp.ClientSession() as session:
            async with session.get(STATIONS_URL) as resp:
                stations = await resp.json()
        if stations:
            for station in stations:
                if station[ATTR_ID] == station_id:
                    return True
        return False
