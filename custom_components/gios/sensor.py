"""
Support for the GIOŚ service.

For more details about this platform, please refer to the documentation at
https://github.com/bieniu/ha-gios
"""
import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

from .const import (
    ATTR_AQI,
    ATTR_INDEX,
    ATTR_NAME,
    ATTR_STATION,
    ATTR_VALUE,
    CONF_STATION_ID,
    DATA_CLIENT,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = {"Data provided by GIOŚ"}
DEFAULT_ICON = "mdi:blur"

ATTR_C6H6 = "C6H6"
ATTR_CO = "CO"
ATTR_NO2 = "NO2"
ATTR_O3 = "O3"
ATTR_PM10 = "PM10"
ATTR_PM25 = "PM25"
ATTR_SO2 = "SO2"

VOLUME_MICROGRAMS_PER_CUBIC_METER = "µg/m³"

SENSOR_TYPES = {
    ATTR_AQI.lower(),
    ATTR_C6H6.lower(),
    ATTR_CO.lower(),
    ATTR_NO2.lower(),
    ATTR_O3.lower(),
    ATTR_PM10.lower(),
    ATTR_PM25.lower(),
    ATTR_SO2.lower(),
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_STATION_ID, None): cv.positive_int,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Configure the platform and add the sensors."""
    del config[CONF_SCAN_INTERVAL]
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data=config
        )
    )


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a GIOS entities from a config_entry."""
    name = config_entry.data[CONF_NAME]

    data = hass.data[DOMAIN][DATA_CLIENT][config_entry.entry_id]

    sensors = []
    for sensor in data.sensors:
        sensors.append(GiosSensor(name, sensor, data))
    async_add_entities(sensors, True)


class GiosSensor(Entity):
    """Define an GIOS sensor."""

    def __init__(self, name, kind, data):
        """Initialize."""
        self._name = name
        self.kind = kind
        self.gios = data
        self._state = None
        self._attrs = {ATTR_ATTRIBUTION: ATTRIBUTION}
        self._icon = DEFAULT_ICON
        self._unit_of_measurement = None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_STATION] = self.gios.station_name
        if self.gios.available:
            if self.kind != ATTR_AQI and self.gios.sensors[self.kind][ATTR_INDEX]:
                self._attrs[ATTR_INDEX] = self.gios.sensors[self.kind][ATTR_INDEX]
                self._attrs[ATTR_NAME] = self.gios.sensors[self.kind][ATTR_NAME]
        return self._attrs

    @property
    def name(self):
        """Return the name."""
        return f"{self._name} {self.kind}"

    @property
    def icon(self):
        """Return the icon."""
        if self.kind == ATTR_AQI:
            if self._state == "bardzo dobry":
                self._icon = "mdi:emoticon-excited"
            elif self._state == "dobry":
                self._icon = "mdi:emoticon-happy"
            elif self._state == "umiarkowany":
                self._icon = "mdi:emoticon-neutral"
            elif self._state == "dostateczny":
                self._icon = "mdi:emoticon-sad"
            elif self._state == "zły":
                self._icon = "mdi:emoticon-dead"
        return self._icon

    @property
    def attribution(self):
        """Return the attribution."""
        return ATTRIBUTION

    @property
    def unique_id(self):
        """Return a unique_id for this entity."""
        return f"{self.gios.latitude}-{self.gios.longitude}-{self.kind}"

    @property
    def state(self):
        """Return the state."""
        if self.gios.available:
            self._state = self.gios.sensors[self.kind][ATTR_VALUE]
            if isinstance(self._state, float):
                self._state = round(self._state)
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self.kind != ATTR_AQI:
            self._unit_of_measurement = VOLUME_MICROGRAMS_PER_CUBIC_METER
        return self._unit_of_measurement

    @property
    def available(self):
        """Return True if entity is available."""
        _LOGGER.debug(f"sensor {self.kind} available: {str(self.gios.available)}")
        return self.gios.available

    async def async_update(self):
        """Get the data from GIOS."""
        await self.gios.async_update()
