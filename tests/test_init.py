"""Tests for entry setup and unload in Solar-Log Legacy."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_setup_and_unload(hass: HomeAssistant, mock_config_entry) -> None:
    """The entry loads, coordinator updates, and unloads cleanly."""
    mock_data = {
        "pac": 2500,
        "pdc": 2600,
        "udc": 380,
        "con": 1,
        "yield_day": 12.5,
        "status": 3,
        "inverters": [],
    }

    with patch(
        "custom_components.solarlog_legacy.coordinator.SolarLogCoordinator._async_update_data",
        return_value=mock_data,
    ):
        mock_config_entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry.state is ConfigEntryState.LOADED

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
