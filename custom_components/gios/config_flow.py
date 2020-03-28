"""Adds config flow for GIOS."""
import asyncio

from aiohttp import ClientError
from aiohttp.client_exceptions import ClientConnectorError
from async_timeout import timeout
from gios import ApiError, Gios, InvalidSensorsData, NoStationError
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (  # pylint:disable=unused-import
    CONF_STATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)


class GiosFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GIOS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        DATA_SCHEMA = vol.Schema(
            {
                vol.Required(CONF_STATION_ID): int,
                vol.Optional(CONF_NAME, default=self.hass.config.location_name): str,
            }
        )

        errors = {}

        if user_input is not None:
            try:
                await self.async_set_unique_id(
                    user_input[CONF_STATION_ID], raise_on_progress=False
                )
                self._abort_if_unique_id_configured()

                websession = async_get_clientsession(self.hass)

                with timeout(30):
                    gios = Gios(user_input[CONF_STATION_ID], websession)
                    await gios.update()

                return self.async_create_entry(
                    title=user_input[CONF_STATION_ID], data=user_input,
                )
            except (ApiError, ClientConnectorError, asyncio.TimeoutError, ClientError):
                errors["base"] = "cannot_connect"
            except NoStationError:
                errors[CONF_STATION_ID] = "wrong_station_id"
            except InvalidSensorsData:
                errors[CONF_STATION_ID] = "invalid_sensors_data"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """GIOS options callback."""
        return GiosOptionsFlowHandler(config_entry)


class GiosOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for GIOS."""

    def __init__(self, config_entry):
        """Initialize Gios options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): int
                }
            ),
        )
