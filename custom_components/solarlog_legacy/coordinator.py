"""DataUpdateCoordinator for Solar-Log Legacy integration."""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BASE_VARS_INTERVAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PCJS_INTERVAL,
    TIMEOUT_NORMAL,
    TIMEOUT_PCJS,
)
from .models import SolarLogLegacyData

_LOGGER = logging.getLogger(__name__)

type SolarLogLegacyConfigEntry = ConfigEntry[SolarLogCoordinator]


def _fetch_js_var(text: str, name: str) -> str | int | bool | list | None:
    """Extract a JavaScript variable value from the response text."""
    # String: var Name="value"
    match = re.search(r"var\s+" + name + r'\s*=\s*"([^"]*)"', text)
    if match:
        return match.group(1)

    # Integer: var Name=123
    match = re.search(r"var\s+" + name + r"\s*=\s*(-?\d+)", text)
    if match:
        return int(match.group(1))

    # Boolean: var Name=true/false
    match = re.search(r"var\s+" + name + r"\s*=\s*(true|false)", text)
    if match:
        return match.group(1) == "true"

    # Array literal: var Name=[...] or var Name=[[...]]
    arr_match = re.search(r"var\s+" + name + r"\s*=\s*(\[.+?\])\s*[;\n]", text)
    if not arr_match:
        arr_match = re.search(r"var\s+" + name + r"\s*=\s*(\[.+?\])\s*$", text, re.MULTILINE)
    if arr_match:
        return _parse_js_array_literal(arr_match.group(1))

    # new Array(): var Name=new Array(...)
    match = re.search(r"var\s+" + name + r"\s*=\s*new Array\(([^)]+)\)", text)
    if match:
        return _parse_js_new_array(match.group(1))

    return None


def _parse_js_array_literal(raw: str) -> list:
    """Parse a JavaScript array literal like [1,2,3] or [[1,2],[3,4]]."""
    inner = raw.strip()
    if inner.startswith("[["):
        # Nested array
        result = []
        # Extract each inner [...] by finding balanced brackets
        depth = 0
        start = -1
        for i, ch in enumerate(inner):
            if ch == "[":
                if depth == 1:
                    start = i + 1
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 1 and start >= 0:
                    sub = inner[start:i]
                    items = _parse_js_array_items(sub)
                    result.append(items)
                    start = -1
        return result
    else:
        # Simple array
        return _parse_js_array_items(inner[1:-1])


def _parse_js_array_items(raw: str) -> list:
    """Parse comma-separated items from an array."""
    items = []
    for x in raw.split(","):
        x = x.strip().strip('"')
        if not x:
            continue
        try:
            items.append(int(x))
        except ValueError:
            try:
                items.append(float(x))
            except ValueError:
                items.append(x)
    return items


def _parse_js_new_array(raw: str) -> list:
    """Parse a new Array(...) argument list."""
    return _parse_js_array_items(raw)


def _parse_pcjs_history(text: str) -> tuple[float, list[float], list[dict], list[dict]]:
    """Parse pc.js?min0 for yield, voltages, and history.

    Returns: (yield_day_wh, udcs, history, daily)
    """
    yield_day_wh = 0.0
    udcs: list[float] = []
    history: list[dict] = []
    daily: list[dict] = []

    # Parse m[] array entries: "DD.MM.YY HH:MM:SS|val1;val2;..."
    for match in re.finditer(r'm\[mi\+\+\]="([^"]+)"', text):
        parts = match.group(1).split("|")
        if len(parts) != 2:
            continue
        ts = parts[0]
        values = [int(x) for x in parts[1].split(";")]
        if len(values) >= 9:
            entry = {
                "timestamp": ts,
                "pac": values[0],
                "pdc1": values[2],
                "pdc2": values[3],
                "yield_wh": values[4],
                "udc1": values[6],
                "udc2": values[7],
            }
            history.append(entry)
            yield_day_wh = values[4]

            # Use the latest Udc values
            if values[6] > 0:
                udcs = [values[6]]
                if values[7] > 0:
                    udcs.append(values[7])

    # Parse da[] array entries: "DD.MM.YY|max;?"
    for match in re.finditer(r'da\[dx\+\+\]="([^"]+)"', text):
        parts = match.group(1).split("|")
        if len(parts) == 2:
            vals = [int(x) for x in parts[1].split(";")]
            daily.append({"date": parts[0], "max_power": vals[0]})

    return yield_day_wh, udcs, history, daily


class SolarLogCoordinator(DataUpdateCoordinator[SolarLogLegacyData]):
    """Coordinator that polls Solar-Log device locally via JS files."""

    config_entry: SolarLogLegacyConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: SolarLogLegacyConfigEntry) -> None:
        """Initialize the coordinator."""
        self.host: str = config_entry.data[CONF_HOST].rstrip("/")
        self._scan_interval: int = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self._session: aiohttp.ClientSession | None = None
        self._last_base_vars: float = 0
        self._last_pcjs: float = 0

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name="SolarLogLegacy",
            update_interval=timedelta(seconds=self._scan_interval),
        )

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _async_update_data(self) -> SolarLogLegacyData:
        """Fetch data from Solar-Log device."""
        session = await self._ensure_session()
        now = time.time()

        # Always fetch min_cur.js (live data, every 60s)
        try:
            text = await self._fetch_js(session, "min_cur.js", TIMEOUT_NORMAL)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching min_cur.js: {err}") from err

        data = self._parse_min_cur(text)

        # Fetch base_vars.js (system info, every 24h)
        if now - self._last_base_vars > BASE_VARS_INTERVAL or not self.data:
            try:
                text = await self._fetch_js(session, "base_vars.js", TIMEOUT_NORMAL)
                self._parse_base_vars(text, data)
                self._last_base_vars = now
            except aiohttp.ClientError as err:
                _LOGGER.warning("Error fetching base_vars.js: %s", err)

        # Fetch pc.js?min0 (history/yield/voltages, every hour)
        if now - self._last_pcjs > PCJS_INTERVAL or not self.data:
            try:
                text = await self._fetch_js(session, "pc.js?min0", TIMEOUT_PCJS)
                yield_wh, udcs, history, daily = _parse_pcjs_history(text)
                data.yield_day_wh = yield_wh
                data.udcs = udcs
                data.history = history
                data.daily = daily
                self._last_pcjs = now
            except aiohttp.ClientError as err:
                _LOGGER.warning("Error fetching pc.js?min0: %s", err)

        # Inherit base_vars data from previous fetch if not refreshed
        if self.data and not data.status_codes:
            data.status_codes = self.data.status_codes
            data.fehler_codes = self.data.fehler_codes
            data.wr_info = self.data.wr_info
            data.anlagen_kwp = self.data.anlagen_kwp
            data.anzahl_wr = self.data.anzahl_wr
            data.serial_nr = self.data.serial_nr
            data.firmware = self.data.firmware
            data.firmware_date = self.data.firmware_date
            data.sl_typ = self.data.sl_typ
            data.lang = self.data.lang
            data.currency = self.data.currency

        data.compute_derived()
        return data

    async def _fetch_js(self, session: aiohttp.ClientSession, path: str, timeout: int) -> str:
        """Fetch a JS file from the device."""
        url = f"{self.host}/{path}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            resp.raise_for_status()
            return await resp.text(encoding="latin-1")

    def _parse_min_cur(self, text: str) -> SolarLogLegacyData:
        """Parse min_cur.js into a SolarLogLegacyData object."""
        data = SolarLogLegacyData()

        val = _fetch_js_var(text, "Datum")
        if val is not None:
            data.datum = str(val)

        val = _fetch_js_var(text, "Uhrzeit")
        if val is not None:
            data.uhrzeit = str(val)

        val = _fetch_js_var(text, "Pac")
        if val is not None and isinstance(val, int):
            data.pac = val

        val = _fetch_js_var(text, "aPdc")
        if val is not None and isinstance(val, list):
            data.apdc = [int(x) if isinstance(x, str) and x.isdigit() else (x if isinstance(x, int) else 0) for x in val]

        val = _fetch_js_var(text, "PacArr")
        if val is not None and isinstance(val, list):
            data.pacarr = [[int(x) if isinstance(x, str) and x.isdigit() else (x if isinstance(x, int) else 0) for x in inner] for inner in val if isinstance(inner, list)]

        val = _fetch_js_var(text, "PdcArr")
        if val is not None and isinstance(val, list):
            data.pdcarr = [[int(x) if isinstance(x, str) and x.isdigit() else (x if isinstance(x, int) else 0) for x in inner] for inner in val if isinstance(inner, list)]

        # curStatusCode is defined as array then assigned per index
        match = re.search(r"var\s+curStatusCode\s*=\s*new Array\((\d+)\)", text)
        if match:
            count = int(match.group(1))
            codes = []
            for i in range(count):
                m = re.search(r"curStatusCode\[" + str(i) + r"\]\s*=\s*(\d+)", text)
                if m:
                    codes.append(int(m.group(1)))
            data.status_code = codes

        match = re.search(r"var\s+curFehlerCode\s*=\s*new Array\((\d+)\)", text)
        if match:
            count = int(match.group(1))
            codes = []
            for i in range(count):
                m = re.search(r"curFehlerCode\[" + str(i) + r"\]\s*=\s*(\d+)", text)
                if m:
                    codes.append(int(m.group(1)))
            data.error_code = codes

        return data

    def _parse_base_vars(self, text: str, data: SolarLogLegacyData) -> None:
        """Parse base_vars.js and fill in system info fields."""
        val = _fetch_js_var(text, "AnlagenKWP")
        if val is not None and isinstance(val, int):
            data.anlagen_kwp = val

        val = _fetch_js_var(text, "AnzahlWR")
        if val is not None and isinstance(val, int):
            data.anzahl_wr = val

        val = _fetch_js_var(text, "Serialnr")
        if val is not None and isinstance(val, int):
            data.serial_nr = val

        val = _fetch_js_var(text, "Firmware")
        if val is not None:
            data.firmware = str(val)

        val = _fetch_js_var(text, "FirmwareDate")
        if val is not None:
            data.firmware_date = str(val)

        val = _fetch_js_var(text, "SLTyp")
        if val is not None:
            data.sl_typ = str(val)

        val = _fetch_js_var(text, "Lang")
        if val is not None:
            data.lang = str(val)

        val = _fetch_js_var(text, "Currency")
        if val is not None:
            data.currency = str(val)

        # Parse StatusCodes array (defined per inverter)
        for i in range(data.anzahl_wr or 1):
            match = re.search(
                r'StatusCodes\[' + str(i) + r'\]\s*=\s*"([^"]*)"', text
            )
            if match:
                data.status_codes.append(match.group(1))

        # Parse FehlerCodes array (defined per inverter)
        for i in range(data.anzahl_wr or 1):
            match = re.search(
                r'FehlerCodes\[' + str(i) + r'\]\s*=\s*"([^"]*)"', text
            )
            if match:
                data.fehler_codes.append(match.group(1))

        # Parse WRInfo[0] assignment
        match = re.search(r"WRInfo\[(\d+)\]\s*=\s*new Array\(([^)]+)\)", text)
        if match:
            items = [x.strip().strip('"') for x in match.group(2).split(",")]
            data.wr_info = [items]

        # Parse WRInfo[0][6] string names (set separately)
        match = re.search(
            r'WRInfo\[(\d+)\]\[(\d+)\]\s*=\s*new Array\(([^)]+)\)', text
        )
        if match and data.wr_info:
            string_names = [x.strip().strip('"') for x in match.group(3).split(",")]
            # Pad wr_info if needed
            while len(data.wr_info[0]) <= 6:
                data.wr_info[0].append(None)
            data.wr_info[0][6] = string_names

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
