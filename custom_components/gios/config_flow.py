"""Adds config flow for GIOS."""
import logging

from async_timeout import timeout
from gios import Gios, NoStationError
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

_LOGGER = logging.getLogger(__name__)


class GiosFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for GIOS."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        websession = async_get_clientsession(self.hass)

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_STATION_ID])
            self._abort_if_unique_id_configured()
            station_id_valid = await self._test_station_id(
                websession, user_input[CONF_STATION_ID]
            )
            if station_id_valid:
                sensors_data_valid = await self._test_sensors_data(
                    websession, user_input[CONF_STATION_ID]
                )
                if not sensors_data_valid:
                    self._errors[CONF_STATION_ID] = "invalid_sensors_data"
            else:
                self._errors[CONF_STATION_ID] = "wrong_station_id"

            if not self._errors:
                return self.async_create_entry(
                    title=user_input[CONF_STATION_ID], data=user_input
                )

        return self._show_config_form(
            name=self.hass.config.location_name, station_id=""
        )

    def _show_config_form(self, name=None, station_id=None):
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """GIOS options callback."""
        return GiosOptionsFlowHandler(config_entry)

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        _LOGGER.warning(
            "GIOŚ configuration from configuration.yaml was imported to "
            "integrations. You can safely remove configuration from configuration.yaml."
        )
        return self.async_create_entry(title="configuration.yaml", data=import_config)

    async def _test_station_id(self, client, station_id):
        """Return true if station_id is valid."""
        try:
            with timeout(30):
                gios = Gios(station_id, client)
                await gios.update()
        except NoStationError:
            return False
        return True

    async def _test_sensors_data(self, client, station_id):
        """Return true if sensors data is valid."""
        with timeout(30):
            gios = Gios(station_id, client)
            await gios.update()
        if gios.available:
            return True
        return False


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
