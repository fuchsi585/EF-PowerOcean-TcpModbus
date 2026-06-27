"""Constants for EF-PowerOcean-TcpModbus integration."""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from collections.abc import Callable

DOMAIN = "ef_powerocean_tcpmodbus"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 10  # seconds
DEFAULT_BATTERY_COUNT = 0
DEFAULT_MAX_SOLAR_POWER = 11400
DEFAULT_MAX_GRID_POWER = 15000
DEFAULT_MAX_POWER = 30000

CONF_HOST = "host"
CONF_PORT = "port"
CONF_BATTERY_COUNT = "battery_count"
CONF_MAX_SOLAR_POWER = "solar_power_max"
CONF_MAX_GRID_POWER = "grid_power_max"
CONF_MAX_BATTERY_CHARGED_POWER = "battery_charged_power_max"
CONF_MAX_BATTERY_DISCHARGED_POWER = "battery_discharged_power_max"
CONF_SCAN_INTERVAL = "scan_interval"

# A – below this value string current is treated as 0 (phantom voltage)
PV_CURRENT_THRESHOLD = 0.06
MAX_BATTERY_CHARGED_POWER = 2500
MAX_BATTERY_DISCHARGED_POWER = 3300


@dataclass(frozen=True)
class RegisterDef:
    key: str
    block_index: int
    size: int = 2


@dataclass(frozen=True)
class BlockDef:
    start_register: int
    content: list[RegisterDef]
    num_read_regs: int = 100


@dataclass(frozen=True)
class SensorDef:
    key: str
    name: str
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    entity_category: str | None = None
    get_checked_value: Callable[..., Any] | None = None
    function_arg: Any | None = None


@dataclass(frozen=True)
class EnergySensorDef:
    key: str
    name: str
    reset_at_midnight: bool = False
    is_calculated: bool = False
    max_power: int | None = None


MOD_REGISTER_MAP = {
    "serial_number": 40004,
    "blocks": [
        BlockDef(
            start_register=40519,
            content=[
                RegisterDef(key="house_power", block_index=0),
                RegisterDef(key="grid_power", block_index=2),
                RegisterDef(key="solar_power", block_index=4),
                RegisterDef(key="battery_power", block_index=6),
                RegisterDef(key="battery_soc", block_index=8, size=1),
                # RegisterDef(key="inverter_ac_power", block_index=11),
                RegisterDef(key="min_soc_limit", block_index=17, size=1),
                RegisterDef(key="bat_temp_warn_max", block_index=21, size=1),
                RegisterDef(key="bat_temp_warn_min", block_index=22, size=1),
                RegisterDef(key="limit_inv_power", block_index=27, size=1),
                RegisterDef(key="limit_inv_max", block_index=29, size=1),
                RegisterDef(key="battery_voltage", block_index=55),
                RegisterDef(key="battery_current", block_index=57),
                RegisterDef(key="battery_temperature", block_index=59),
                RegisterDef(key="voltage_l1", block_index=61),
                RegisterDef(key="voltage_l2", block_index=63),
                RegisterDef(key="voltage_l3", block_index=65),
                RegisterDef(key="current_l1", block_index=67),
                RegisterDef(key="current_l2", block_index=69),
                RegisterDef(key="current_l3", block_index=71),
                RegisterDef(key="inverter_temperature", block_index=73),
                RegisterDef(key="frequency", block_index=75),
                RegisterDef(key="pv1_voltage", block_index=77),
                RegisterDef(key="pv2_voltage", block_index=79),
                RegisterDef(key="pv3_voltage", block_index=81),
                RegisterDef(key="pv1_current", block_index=83),
                RegisterDef(key="pv2_current", block_index=85),
                RegisterDef(key="pv3_current", block_index=87),
            ],
        ),
        BlockDef(
            start_register=42081,
            num_read_regs=4,
            content=[
                RegisterDef(key="battery_count", block_index=0, size=1),
                RegisterDef(key="soc_battery_1", block_index=1, size=1),
                RegisterDef(key="soc_battery_2", block_index=2, size=1),
                RegisterDef(key="soc_battery_3", block_index=3, size=1),
            ],
        ),
        BlockDef(
            start_register=42161,
            content=[
                RegisterDef(key="grid_import_total", block_index=0),
                RegisterDef(key="grid_import_today", block_index=2),
                RegisterDef(key="grid_export_total", block_index=16),
                RegisterDef(key="grid_export_today", block_index=18),
                RegisterDef(key="bat_charged_total", block_index=64),
                RegisterDef(key="bat_charged_today", block_index=66),
                RegisterDef(key="bat_discharged_total", block_index=80),
                RegisterDef(key="bat_discharged_today", block_index=82),
                RegisterDef(key="solar_total", block_index=96),
                RegisterDef(key="solar_today", block_index=98),
            ],
        ),
    ],
}


def set_to_zero_below_threshold(value, threshold):
    return 0 if value < threshold else value


SENSOR_MAP: list[SensorDef] = [
    SensorDef(
        key="house_power",
        name="House Power",
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    SensorDef(
        key="grid_power",
        name="Grid Power",
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    SensorDef(
        key="solar_power",
        name="Solar Power",
        unit="W",
        device_class="power",
        state_class="measurement",
        get_checked_value=max,
        function_arg=0,
    ),
    SensorDef(
        key="battery_power",
        name="Battery Power",
        unit="W",
        device_class="power",
        state_class="measurement",
    ),
    SensorDef(
        key="battery_soc",
        name="Battery SOC",
        unit="%",
        device_class="battery",
        state_class="measurement",
    ),
    SensorDef(
        key="min_soc_limit",
        name="Min SOC Limit",
        unit="%",
        device_class="battery",
        state_class="measurement",
    ),
    SensorDef(
        key="bat_temp_warn_max",
        name="Battery Temp Warning Max",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="bat_temp_warn_min",
        name="Battery Temp Warning Min",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="limit_inv_power",
        name="Inverter Current Max Power",
        unit="W",
        device_class="power",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="limit_inv_max",
        name="Inverter Nominal Power Limit",
        unit="W",
        device_class="power",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="battery_voltage",
        name="Battery Voltage",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="battery_current",
        name="Battery Current",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="battery_temperature",
        name="Battery Temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="voltage_l1",
        name="Grid Voltage L1",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="voltage_l2",
        name="Grid Voltage L2",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="voltage_l3",
        name="Grid Voltage L3",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="current_l1",
        name="Grid Current L1",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="current_l2",
        name="Grid Current L2",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="current_l3",
        name="Grid Current L3",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="inverter_temperature",
        name="Inverter Temperature",
        unit="°C",
        device_class="temperature",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="frequency",
        name="Grid Frequency",
        unit="Hz",
        device_class="frequency",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="pv1_voltage",
        name="PV String 1 Voltage",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="pv2_voltage",
        name="PV String 2 Voltage",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="pv3_voltage",
        name="PV String 3 Voltage",
        unit="V",
        device_class="voltage",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="pv1_current",
        name="PV String 1 Current",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
        get_checked_value=set_to_zero_below_threshold,
        function_arg=PV_CURRENT_THRESHOLD,
    ),
    SensorDef(
        key="pv2_current",
        name="PV String 2 Current",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
        get_checked_value=set_to_zero_below_threshold,
        function_arg=PV_CURRENT_THRESHOLD,
    ),
    SensorDef(
        key="pv3_current",
        name="PV String 3 Current",
        unit="A",
        device_class="current",
        state_class="measurement",
        entity_category="diagnostic",
        get_checked_value=set_to_zero_below_threshold,
        function_arg=PV_CURRENT_THRESHOLD,
    ),
    SensorDef(
        key="battery_count",
        name="Battery Module Count",
        unit=None,
        device_class=None,
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="soc_battery_1",
        name="SOC Battery 1",
        unit="%",
        device_class="battery",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="soc_battery_2",
        name="SOC Battery 2",
        unit="%",
        device_class="battery",
        state_class="measurement",
        entity_category="diagnostic",
    ),
    SensorDef(
        key="soc_battery_3",
        name="SOC Battery 3",
        unit="%",
        device_class="battery",
        state_class="measurement",
        entity_category="diagnostic",
    ),
]


ENERGY_SENSOR_MAP: list[EnergySensorDef] = [
    EnergySensorDef(
        "grid_import_total",
        "Grid Import Total",
        max_power=CONF_MAX_GRID_POWER,
    ),
    EnergySensorDef(
        "grid_import_today",
        "Grid Import Today",
        reset_at_midnight=True,
        max_power=CONF_MAX_GRID_POWER,
    ),
    EnergySensorDef(
        "grid_export_total", "Grid Export Total", max_power=CONF_MAX_SOLAR_POWER
    ),
    EnergySensorDef(
        "grid_export_today",
        "Grid Export Today",
        reset_at_midnight=True,
        max_power=CONF_MAX_SOLAR_POWER,
    ),
    EnergySensorDef(
        "bat_charged_total",
        "Battery Charged Total",
        max_power=CONF_MAX_BATTERY_CHARGED_POWER,  # MAX_BATTERY_CHARGED_POWER * DEFAULT_BATTERY_COUNT,
    ),
    EnergySensorDef(
        "bat_charged_today",
        "Battery Charged Today",
        reset_at_midnight=True,
        max_power=CONF_MAX_BATTERY_CHARGED_POWER,  # MAX_BATTERY_CHARGED_POWER * DEFAULT_BATTERY_COUNT,
    ),
    EnergySensorDef(
        "bat_discharged_total",
        "Battery Discharged Total",
        max_power=CONF_MAX_BATTERY_DISCHARGED_POWER,  # MAX_BATTERY_DISCHARGED_POWER * DEFAULT_BATTERY_COUNT,
    ),
    EnergySensorDef(
        "bat_discharged_today",
        "Battery Discharged Today",
        reset_at_midnight=True,
        max_power=CONF_MAX_BATTERY_DISCHARGED_POWER,  # MAX_BATTERY_DISCHARGED_POWER * DEFAULT_BATTERY_COUNT,
    ),
    EnergySensorDef("solar_total", "Solar Yield Total", max_power=CONF_MAX_SOLAR_POWER),
    EnergySensorDef(
        "solar_today",
        "Solar Yield Today",
        reset_at_midnight=True,
        max_power=CONF_MAX_SOLAR_POWER,
    ),
    EnergySensorDef(
        "house_energy_today",
        "House Consumption Today",
        reset_at_midnight=True,
        is_calculated=True,
        max_power=CONF_MAX_GRID_POWER,
    ),
    EnergySensorDef(
        "house_energy_total",
        "House Consumption Total",
        is_calculated=True,
        max_power=CONF_MAX_GRID_POWER,
    ),
]
