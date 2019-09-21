"""Constants for GIOS integration."""
import logging

_LOGGER = logging.getLogger(__name__)
ATTR_ID = "id"
CONF_STATION_ID = "station_id"
DEFAULT_SCAN_INTERVAL = 1800
DEFAULT_NAME = "GIOŚ"
DOMAIN = "gios"
STATIONS_URL = "http://api.gios.gov.pl/pjp-api/rest/station/findAll"
