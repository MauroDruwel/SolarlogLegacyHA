"""The Solar-Log Legacy integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import SolarLogCoordinator, SolarLogLegacyConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SolarLogLegacyConfigEntry) -> bool:
    """Set up Solar-Log Legacy from a config entry."""
    coordinator = SolarLogCoordinator(hass, entry)
    entry.runtime_data = coordinator

    await coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: SolarLogLegacyConfigEntry) -> bool:
    """Unload a config entry."""
    await entry.runtime_data.close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
