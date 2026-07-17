"""Models for the Solar-Log Legacy integration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SolarLogLegacyData:
    """Parsed data from Solar-Log JS files."""

    # min_cur.js (polled every 60s)
    datum: str = ""
    uhrzeit: str = ""
    pac: int = 0
    apdc: list[int] = field(default_factory=list)
    pacarr: list[list[int]] = field(default_factory=list)
    pdcarr: list[list[int]] = field(default_factory=list)
    status_code: list[int] = field(default_factory=list)
    error_code: list[int] = field(default_factory=list)

    # base_vars.js (polled every 24h)
    anlagen_kwp: int = 0
    anzahl_wr: int = 0
    serial_nr: int = 0
    firmware: str = ""
    firmware_date: str = ""
    sl_typ: str = ""
    lang: str = ""
    currency: str = ""
    status_codes: list[str] = field(default_factory=list)
    fehler_codes: list[str] = field(default_factory=list)
    wr_info: list[list] = field(default_factory=list)

    # pc.js?min0 (polled every hour)
    yield_day_wh: float = 0
    udcs: list[float] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)
    daily: list[dict] = field(default_factory=list)

    # Computed
    power_dc: int = 0
    voltage_dc: float = 0
    alternator_loss: int = 0
    capacity: float = 0
    efficiency: float = 0
    consumption_ac: int = 0
    status_text: str = ""
    error_text: str = ""

    def compute_derived(self) -> None:
        """Compute derived values from raw data."""
        self.power_dc = sum(self.apdc) if self.apdc else 0

        if self.udcs:
            self.voltage_dc = sum(self.udcs) / len(self.udcs)

        self.alternator_loss = self.power_dc - self.pac

        if self.anlagen_kwp > 0:
            self.capacity = (self.power_dc / self.anlagen_kwp) * 100

        if self.power_dc > 0:
            self.efficiency = (self.pac / self.power_dc) * 100

        if self.pacarr and self.pacarr[0]:
            self.consumption_ac = self.pacarr[0][0]

        if self.status_codes and self.status_code:
            idx = self.status_code[0] if self.status_code else 0
            codes = self.status_codes[0].split(",") if self.status_codes else []
            if idx < len(codes):
                self.status_text = codes[idx].strip()

        if self.fehler_codes and self.error_code:
            idx = self.error_code[0] if self.error_code else 0
            codes = self.fehler_codes[0].split(",") if self.fehler_codes else []
            if idx < len(codes):
                self.error_text = codes[idx].strip()
