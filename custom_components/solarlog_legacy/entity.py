"""Entity base classes for Solar-Log Legacy integration."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarLogCoordinator


class SolarLogLegacyEntity(CoordinatorEntity[SolarLogCoordinator]):
    """Base entity for Solar-Log Legacy sensors."""

    _attr_has_entity_name = True
    _attr_attribution = "Data provided by Solar-Log"

    def __init__(
        self,
        coordinator: SolarLogCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="Solar-Log Legacy",
            manufacturer="Solar-Log",
            model=coordinator.data.sl_typ if coordinator.data else "Unknown",
            sw_version=coordinator.data.firmware if coordinator.data else None,
            configuration_url=coordinator.host,
        )
