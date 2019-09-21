"""The GIOS component."""
from homeassistant.core import Config, HomeAssistant


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up configured GIOS."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up GIOS as config entry."""
    config_entry.add_update_listener(update_listener)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config_entry, "sensor")
    )
    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
    return True


async def update_listener(hass, entry):
    """Update listener."""
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, "sensor"))
