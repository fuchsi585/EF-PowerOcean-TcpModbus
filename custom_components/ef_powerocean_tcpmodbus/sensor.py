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
    EnergySensorDef,
    ENERGY_SENSOR_MAP,
    SENSOR_MAP,
)
from .coordinator import EcoflowCoordinator
from datetime import datetime
from homeassistant.util import dt

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
        key="battery_capacity",
        name="Battery Nominal Capacity",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
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
    # ── Energy – Lifetime ─────────────────────────────────────────────────────
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
        entities.append(EcoflowEnergySensor(coordinator, sensor, entry))

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
            self._last_written_value = last_value.native_value

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value from coordinator, falling back to last value"""
        if self.coordinator.data is not None:
            value = self.coordinator.data.get(self.entity_description.key, None)
            if value is not None:
                if self.sensor_definition.get_checked_value is not None:
                    if self.sensor_definition.function_arg:
                        value = self.sensor_definition.get_checked_value(
                            value, self.sensor_definition.function_arg
                        )

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


class EcoflowEnergySensor(CoordinatorEntity[EcoflowCoordinator], RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: EcoflowCoordinator,
        definition: EnergySensorDef,
        entry,
    ) -> None:
        super().__init__(coordinator)
        self.sensor_definition: EnergySensorDef = definition
        self.name = self.sensor_definition.name
        self._attr_unique_id = f"{entry.entry_id}_{definition.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="EcoFlow PowerOcean",
            manufacturer="EcoFlow",
            model="PowerOcean",
            serial_number=coordinator.serial_number,
            sw_version=f"pymodbus {coordinator.get_pymodbus_version()}",
            entry_type=DeviceEntryType.SERVICE,
        )

        self._restored_value: float | int | str | None = None
        self._last_written_value: float | int | str | None = None
        self._attr_suggested_display_precision = VALUE_PRECISION.get(
            self._attr_native_unit_of_measurement
        )
        self._last_checked_time: datetime = None

    async def async_added_to_hass(self) -> None:
        """Wird aufgerufen, wenn die Entität hinzugefügt wird."""
        await super().async_added_to_hass()
        # Den letzten Status aus der Datenbank laden
        if (
            last_value := await self.async_get_last_sensor_data()
        ) and last_value.native_value is not None:
            _LOGGER.info(
                f"Restore Sensor '{self.sensor_definition.name}' with value: {last_value.native_value}"
            )
            self._restored_value = last_value.native_value
            self._last_written_value = self._restored_value

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        new_value = self.native_value
        self._last_checked_time = dt.now()
        if new_value != self._last_written_value:
            self._last_written_value = new_value
            self.async_write_ha_state()

    @property
    def native_value(self) -> float | int | None:
        if self.coordinator.data is None:
            _LOGGER.info(
                f"Coordinator-data is None. Return {self._last_written_value} at {dt.now().time()} für Sensor {self.sensor_definition.key}"
            )
            return self._last_written_value

        now = dt.now()
        current_energy = self.coordinator.data.get(self.sensor_definition.key, None)
        if current_energy is None:
            _LOGGER.info(
                f"Current_energy is None. Return {self._last_written_value} at {dt.now().time()} für Sensor {self.sensor_definition.key}"
            )
            return self._last_written_value

        if self._last_checked_time is None:
            _LOGGER.info(
                f"Last checked time is None. Return {current_energy} at {now.time()} für Sensor {self.sensor_definition.key}"
            )
            return current_energy
        elif (now - self._last_checked_time).total_seconds() < 1:
            _LOGGER.debug(
                f"dt is less then one secend. Return {self._last_written_value} für Sensor {self.sensor_definition.key}. Delta-t: {(now - self._last_checked_time).total_seconds()}"
            )
            return self._last_written_value
        elif (
            self.sensor_definition.reset_at_midnight
            and current_energy == 0
            and self._last_written_value > 0
            and now.hour == 0
            and now.minute < 1
        ):
            # Reset nur zwischen 00:00 und 00:01 erlauben
            _LOGGER.info(f"Reset bei {now.time()} Uhr für {self.sensor_definition.key}")
            return 0
        else:
            dt_hours = (now - self._last_checked_time).total_seconds() / 3600
            # Nur innerhalb einer 1h Stunde prüfen, danach ist das Gap zu groß
            if 0 < dt_hours <= 1:
                # Anstieg berechnen
                # _LOGGER.info(f"Start check at {now.time()} with last data of {self._last_checked_time.time()}")
                energy_delta = current_energy - self._last_written_value
                calculated_power = energy_delta / dt_hours
                if calculated_power > self.sensor_definition.max_power:
                    # positiver Anstieg und Lesitung über Max-Leistung
                    _LOGGER.warning(
                        f"Rohwert blockiert für Sensor {self.sensor_definition.key}! (Current-Energy: {current_energy} Last-Energy: {self._last_written_value} dt: {dt_hours} Leistung: {int(calculated_power)} Limit: {self.sensor_definition.max_power} Delta: {round(energy_delta, 4)} Now: {now.time()} Last-Check: {self._last_checked_time.time()})"
                    )
                    return self._last_written_value
                else:
                    # negativer Anstieg oder unterhalb der Max-Leistung
                    if current_energy == 0:
                        _LOGGER.warning(
                            f"Rohwert 0 kWh für Sensor {self.sensor_definition.key}! (Current-Energy: {current_energy} Last-Energy: {self._last_written_value} dt: {dt_hours} Leistung: {int(calculated_power)} Limit: {self.sensor_definition.max_power} Delta: {round(energy_delta, 4)} Now: {now.time()} Last-Check: {self._last_checked_time.time()})"
                        )
                    # Rückgabe des aktuellen Wertes nur wenn der neue Wert > letzter Wert ist
                    return (
                        current_energy
                        if current_energy >= self._last_written_value
                        else self._last_written_value
                    )
            else:
                _LOGGER.info(
                    f"Gap zu groß für Sensor {self.sensor_definition.key}! (Current-Energy: {current_energy} Last-Energy: {self._last_written_value} dt: {dt_hours} Leistung: {int(calculated_power)} Limit: {self.sensor_definition.max_power} Delta: {round(energy_delta, 4)} Now: {now.time()} Last-Check: {self._last_checked_time.time()})"
                )
                return current_energy
