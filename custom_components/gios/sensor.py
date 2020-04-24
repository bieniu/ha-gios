"""Support for the GIOŚ service."""
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONF_NAME,
)
from homeassistant.helpers.entity import Entity

from .const import ATTR_AQI, ATTR_INDEX, ATTR_NAME, ATTR_STATION, ATTR_VALUE, DOMAIN

ATTRIBUTION = {"Data provided by GIOŚ"}
DEFAULT_ICON = "mdi:blur"

ATTR_C6H6 = "C6H6"
ATTR_CO = "CO"
ATTR_NO2 = "NO2"
ATTR_O3 = "O3"
ATTR_PM10 = "PM10"
ATTR_PM25 = "PM25"
ATTR_SO2 = "SO2"

ATTR_STATION_ID = "station_id"
ATTR_STATION_NAME = "station_name"

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


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add a GIOS entities from a config_entry."""
    name = config_entry.data[CONF_NAME]

    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []

    for sensor in coordinator.data:
        if sensor.lower() in SENSOR_TYPES:
            sensors.append(GiosSensor(name, sensor, coordinator))
    async_add_entities(sensors, False)


class GiosSensor(Entity):
    """Define an GIOS sensor."""

    def __init__(self, name, kind, coordinator):
        """Initialize."""
        self._name = name
        self.kind = kind
        self.coordinator = coordinator
        self._state = None
        self._attrs = {ATTR_ATTRIBUTION: ATTRIBUTION}
        self._icon = DEFAULT_ICON
        self._unit_of_measurement = None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        self._attrs[ATTR_STATION] = self.coordinator.gios.station_name
        if self.kind != ATTR_AQI and self.coordinator.data[self.kind][ATTR_INDEX]:
            self._attrs[ATTR_INDEX] = self.coordinator.data[self.kind][ATTR_INDEX]
            self._attrs[ATTR_NAME] = self.coordinator.data[self.kind][ATTR_NAME]
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
        return f"{self.coordinator.gios.station_id}-{self.kind}"

    @property
    def state(self):
        """Return the state."""
        self._state = self.coordinator.data[self.kind][ATTR_VALUE]
        if isinstance(self._state, float):
            self._state = round(self._state)
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        if self.kind != ATTR_AQI:
            self._unit_of_measurement = CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return False

    @property
    def available(self):
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )

    async def async_update(self):
        """Update GIOS entity."""
        await self.coordinator.async_request_refresh()
