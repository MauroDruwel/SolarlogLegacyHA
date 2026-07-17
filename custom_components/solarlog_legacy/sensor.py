"""Sensor platform for Solar-Log Legacy integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarLogCoordinator, SolarLogLegacyConfigEntry
from .entity import SolarLogLegacyEntity
from .models import SolarLogLegacyData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class SolarLogLegacySensorEntityDescription(SensorEntityDescription):
    """Describe a Solar-Log Legacy sensor."""

    value_fn: Callable[[SolarLogLegacyData], float | int | str | None]


# Sensors matching official HA integration (same translation keys)
STATIC_SENSORS: tuple[SolarLogLegacySensorEntityDescription, ...] = (
    SolarLogLegacySensorEntityDescription(
        key="power_ac",
        translation_key="power_ac",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pac,
    ),
    SolarLogLegacySensorEntityDescription(
        key="power_dc",
        translation_key="power_dc",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.power_dc,
    ),
    SolarLogLegacySensorEntityDescription(
        key="voltage_dc",
        translation_key="voltage_dc",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.voltage_dc if data.voltage_dc > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="total_power",
        translation_key="total_power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        value_fn=lambda data: data.anlagen_kwp if data.anlagen_kwp > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="alternator_loss",
        translation_key="alternator_loss",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.alternator_loss,
    ),
    SolarLogLegacySensorEntityDescription(
        key="capacity",
        translation_key="capacity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.capacity if data.capacity > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="efficiency",
        translation_key="efficiency",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.efficiency if data.efficiency > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _parse_timestamp(data.datum, data.uhrzeit),
    ),
    SolarLogLegacySensorEntityDescription(
        key="yield_day",
        translation_key="yield_day",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
        value_fn=lambda data: data.yield_day_wh if data.yield_day_wh > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="status",
        translation_key="status",
        value_fn=lambda data: data.status_text if data.status_text else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="consumption_ac",
        translation_key="consumption_ac",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.consumption_ac if data.consumption_ac > 0 else None,
    ),
    # Bonus sensors (not in official integration)
    SolarLogLegacySensorEntityDescription(
        key="error_code",
        translation_key="error_code",
        value_fn=lambda data: data.error_text if data.error_text else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="num_inverters",
        translation_key="num_inverters",
        value_fn=lambda data: data.anzahl_wr if data.anzahl_wr > 0 else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="firmware",
        translation_key="firmware",
        value_fn=lambda data: data.firmware if data.firmware else None,
    ),
    SolarLogLegacySensorEntityDescription(
        key="inverter_model",
        translation_key="inverter_model",
        value_fn=lambda data: (
            data.wr_info[0][0] if data.wr_info and len(data.wr_info[0]) > 0 else None
        ),
    ),
)


def _parse_timestamp(datum: str, uhrzeit: str) -> datetime | None:
    """Parse date and time strings into a datetime object."""
    if not datum or not uhrzeit:
        return None
    try:
        return datetime.strptime(f"{datum} {uhrzeit}", "%d.%m.%y %H:%M:%S")
    except ValueError:
        return None


def _build_string_sensors(coordinator: SolarLogCoordinator) -> list[SensorEntity]:
    """Build dynamic per-string sensors based on aPdc array length."""
    entities: list[SensorEntity] = []
    data = coordinator.data

    if not data or not data.apdc:
        return entities

    # Get string names from WRInfo if available
    string_names: list[str] = []
    if data.wr_info and len(data.wr_info) > 0:
        wr = data.wr_info[0]
        if len(wr) > 6 and isinstance(wr[6], list):
            string_names = wr[6]

    for idx, power_val in enumerate(data.apdc):
        # Skip index 0 if it's 0 (some devices put a leading 0)
        if idx == 0 and power_val == 0 and len(data.apdc) > 1:
            continue

        name = string_names[idx] if idx < len(string_names) else f"String {idx}"

        # Power sensor
        entities.append(
            SolarLogStringSensor(
                coordinator,
                SolarLogLegacySensorEntityDescription(
                    key=f"string_{idx}_power",
                    translation_key="string_power",
                    native_unit_of_measurement=UnitOfPower.WATT,
                    device_class=SensorDeviceClass.POWER,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=lambda data, i=idx: _get_string_power(data, i),
                ),
                name,
            )
        )

        # Voltage sensor (from pc.js data)
        if idx < len(data.udcs) and data.udcs[idx] > 0:
            entities.append(
                SolarLogStringSensor(
                    coordinator,
                    SolarLogLegacySensorEntityDescription(
                        key=f"string_{idx}_voltage",
                        translation_key="string_voltage",
                        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                        device_class=SensorDeviceClass.VOLTAGE,
                        state_class=SensorStateClass.MEASUREMENT,
                        value_fn=lambda data, i=idx: _get_string_voltage(data, i),
                    ),
                    name,
                )
            )

    return entities


def _get_string_power(data: SolarLogLegacyData, idx: int) -> int | None:
    """Get power for a specific string, skipping leading 0."""
    if idx == 0 and data.apdc and data.apdc[0] == 0 and len(data.apdc) > 1:
        return None
    if idx < len(data.apdc):
        return data.apdc[idx]
    return None


def _get_string_voltage(data: SolarLogLegacyData, idx: int) -> float | None:
    """Get voltage for a specific string."""
    if idx < len(data.udcs) and data.udcs[idx] > 0:
        return data.udcs[idx]
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SolarLogLegacyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Solar-Log Legacy sensors from a config entry."""
    coordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        SolarLogLegacySensor(coordinator, desc) for desc in STATIC_SENSORS
    ]

    # Add dynamic string sensors
    entities.extend(_build_string_sensors(coordinator))

    async_add_entities(entities)


class SolarLogLegacySensor(SolarLogLegacyEntity, SensorEntity):
    """Representation of a Solar-Log Legacy sensor."""

    entity_description: SolarLogLegacySensorEntityDescription

    def __init__(
        self,
        coordinator: SolarLogCoordinator,
        description: SolarLogLegacySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class SolarLogStringSensor(CoordinatorEntity[SolarLogCoordinator], SensorEntity):
    """Representation of a per-string sensor."""

    _attr_has_entity_name = True
    _attr_attribution = "Data provided by Solar-Log"

    def __init__(
        self,
        coordinator: SolarLogCoordinator,
        description: SolarLogLegacySensorEntityDescription,
        string_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._string_name = string_name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_name = string_name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Solar-Log Legacy",
            manufacturer="Solar-Log",
            model=coordinator.data.sl_typ if coordinator.data else "Unknown",
            sw_version=coordinator.data.firmware if coordinator.data else None,
            configuration_url=coordinator.host,
        )

    @property
    def native_value(self) -> float | int | None:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
