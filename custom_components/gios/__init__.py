"""The GIOS component."""
from homeassistant.core import Config, HomeAssistant
from .config_flow import GiosFlowHandler


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured GIOS."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up GIOS as config entry."""
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True
