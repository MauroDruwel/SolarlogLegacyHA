"""Tests for the Solar-Log Legacy config and options flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.solarlog_legacy.config_flow import CannotConnect
from custom_components.solarlog_legacy.const import CONF_SCAN_INTERVAL, DOMAIN


async def test_flow_user_success(hass: HomeAssistant) -> None:
    """Test successful user step configuration."""
    with patch(
        "custom_components.solarlog_legacy.config_flow.SolarLogLegacyConfigFlow._test_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100"},
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == "192.168.1.100"
        assert result2["data"][CONF_HOST] == "192.168.1.100"


async def test_flow_user_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection failure in config flow."""
    with patch(
        "custom_components.solarlog_legacy.config_flow.SolarLogLegacyConfigFlow._test_connection",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: "192.168.1.100"},
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"]["base"] == "cannot_connect"


async def test_options_flow(hass: HomeAssistant, mock_config_entry) -> None:
    """Test updating update interval via options flow."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: 45},
    )
    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 45
