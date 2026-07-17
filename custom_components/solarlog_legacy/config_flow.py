"""Config flow for Solar-Log Legacy integration."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.core import callback

from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_HOST,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    TIMEOUT_NORMAL,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    }
)


class SolarLogLegacyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar-Log Legacy."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            try:
                await self._test_connection(host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=host, data={CONF_HOST: host}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow() -> SolarLogLegacyOptionsFlow:
        """Get the options flow for this handler."""
        return SolarLogLegacyOptionsFlow()

    async def _test_connection(self, host: str) -> None:
        """Test if we can connect to the Solar-Log device."""
        try:
            async with aiohttp.ClientSession() as session:
                resp = await session.get(
                    f"{host}/min_cur.js",
                    timeout=aiohttp.ClientTimeout(total=TIMEOUT_NORMAL),
                )
                resp.raise_for_status()
                text = await resp.text(encoding="latin-1")
                if "var Pac" not in text and "var PacArr" not in text:
                    raise CannotConnect
        except aiohttp.ClientError as err:
            raise CannotConnect from err


class SolarLogLegacyOptionsFlow(OptionsFlow):
    """Handle options flow for Solar-Log Legacy."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                    ),
                }
            ),
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
