"""Sensor entities for EcoFlow PowerOcean Plus."""

from __future__ import annotations

import logging
from typing import Any
from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    RestoreSensor,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SensorDef,
    ENERGY_SENSOR_MAP,
    SENSOR_MAP,
)
from .coordinator import EcoflowCoordinator

_LOGGER = logging.getLogger(__name__)


# ist doppelt
@dataclass(frozen=False)
class EcoflowSensorDescription(SensorEntityDescription):
    native_unit_of_measurement: str | None = None
    get_checked_value: Callable[..., Any] | None = None
    function_arg: Any | None = None


VALUE_PRECISION = {
    PERCENTAGE: 0,
    UnitOfPower.WATT: 0,
    UnitOfEnergy.KILO_WATT_HOUR: 2,
    UnitOfTemperature.CELSIUS: 1,
    UnitOfFrequency.HERTZ: 2,
    UnitOfElectricPotential.VOLT: 1,
    UnitOfElectricCurrent.AMPERE: 2,
}

SENSORS: list[EcoflowSensorDescription] = [
    EcoflowSensorDescription(
        key="bat_remaining",
        name="Battery Remaining Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EcoflowSensorDescription(
        key="pv1_power",
        name="PV String 1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EcoflowSensorDescription(
        key="pv2_power",
        name="PV String 2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EcoflowSensorDescription(
        key="pv3_power",
        name="PV String 3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EcoflowSensorDescription(
        key="bat_net_energy",
        name="Battery Net Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EcoflowCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list = []
    async_add_entities(
        EcoflowSensor(coordinator, description, entry, description)
        for description in SENSORS
    )

    for sensor in SENSOR_MAP:
        description = EcoflowSensorDescription(
            key=sensor.key,
            name=sensor.name,
            native_unit_of_measurement=sensor.unit,
            device_class=sensor.device_class,
            state_class=sensor.state_class,
        )
        if sensor.entity_category == "diagnostic":
            description.entity_category = EntityCategory.DIAGNOSTIC

        entities.append(EcoflowSensor(coordinator, description, entry, sensor))

    for sensor in ENERGY_SENSOR_MAP:
        description = EcoflowSensorDescription(
            key=sensor.key,
            name=sensor.name,
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
        )
        entities.append(EcoflowSensor(coordinator, description, entry, sensor))

    async_add_entities(entities)


class EcoflowSensor(CoordinatorEntity[EcoflowCoordinator], RestoreSensor):
    entity_description: EcoflowSensorDescription

    def __init__(self, coordinator, description, entry, sensor_definition) -> None:
        super().__init__(coordinator)
        self.entity_description: EcoflowSensorDescription = description
        self.sensor_definition: SensorDef = sensor_definition
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="EcoFlow PowerOcean",
            manufacturer="EcoFlow",
            model="PowerOcean",
            serial_number=coordinator.serial_number,
            sw_version=f"pymodbus: {coordinator.get_pymodbus_version()}",
            entry_type=DeviceEntryType.SERVICE,
        )
        self._restored_value: float | int | str | None = None
        self._last_written_value: float | int | str | None = None

        if self.entity_description.native_unit_of_measurement in VALUE_PRECISION:
            self._attr_suggested_display_precision = VALUE_PRECISION.get(
                self.entity_description.native_unit_of_measurement
            )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_value = self.native_value
        if new_value != self._last_written_value:
            self._last_written_value = new_value
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Restore last known value when sensor is added."""
        await super().async_added_to_hass()
        if (
            last_value := await self.async_get_last_sensor_data()
        ) and last_value.native_value is not None:
            _LOGGER.debug(
                f"Restore Sensor '{self.entity_description.name}' with value: {last_value.native_value}"
            )
            self._restored_value = last_value.native_value
            self._last_written_value = self._restored_value

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value from coordinator, falling back to last value"""
        if self.coordinator.data is not None:
            value = self.coordinator.data.get(self.entity_description.key, None)
            if value is not None:
                # if self.sensor_definition.get_checked_value is not None:
                #     if self.sensor_definition.function_arg:
                #         value = self.sensor_definition.get_checked_value(
                #             value, self.sensor_definition.function_arg
                #         )

                if precision := VALUE_PRECISION.get(
                    self.entity_description.native_unit_of_measurement, None
                ):
                    return (
                        round(value, precision)
                        if precision > 0
                        else int(round(value, 0))
                    )
                else:
                    return value
        return self._last_written_value
