"""Constants for EF-PowerOcean-TcpModbus integration."""

from dataclasses import dataclass

DOMAIN = "ef_powerocean_tcpmodbus"
DEFAULT_PORT = 502
DEFAULT_SLAVE = 1
DEFAULT_SCAN_INTERVAL = 10  # seconds
DEFAULT_BATTERY_CAPACITY = 5.0  # kWh – workaround, register 40528 unreliable

CONF_BATTERY_CAPACITY = "battery_capacity"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PV_STRINGS = "pv_strings"

DEFAULT_PV_STRINGS = 2
PV_CURRENT_THRESHOLD = (
    0.05  # A – below this value string current is treated as 0 (phantom voltage)
)

# Used in config_flow connection test only
REG_STATUS = 42081  # UINT16 – 1 = Online


@dataclass(frozen=True)
class RegisterDef:
    key: str
    name: str
    block_index: int
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = None
    entity_category: str | None = None
    icon: str | None = None
    size: int = 2


# TODO
# DEFAULT_BATTERY_COUNT muss über config vom User vorgeben werden


@dataclass(frozen=True)
class BlockDef:
    start_register: int
    content: list[RegisterDef]
    num_read_regs: int = 100


DEFAULT_BATTERY_COUNT = 2
LIMIT_CHARGE = 2500  # 2.5 kW per module
LIMIT_DISCHARGE = 3300  # 3.3 kW per module

MOD_REGISTER_MAP = {
    "serial_number": 40004,
    "blocks": [
        BlockDef(
            start_register=40519,
            content=[
                RegisterDef(
                    "house_power", "House Power", 0, "W", "power", "measurement"
                ),
                RegisterDef("grid_power", "Grid Power", 2, "W", "power", "measurement"),
                RegisterDef(
                    "solar_power",
                    "Solar Power",
                    4,
                    "W",
                    "power",
                    "measurement",
                ),
                RegisterDef(
                    "battery_power",
                    "Battery Power",
                    6,
                    "W",
                    "power",
                    "measurement",
                ),
                RegisterDef(
                    "battery_soc",
                    "Battery SOC",
                    8,
                    "%",
                    "battery",
                    "measurement",
                    size=1,
                ),
                # RegisterDef("inverter_ac_power", "Inverter AC Power", 11, "W", "power", "measurement"),
                RegisterDef(
                    "min_soc_limit",
                    "Min SOC Limit",
                    17,
                    "%",
                    "battery",
                    "measurement",
                    size=1,
                ),
                RegisterDef(
                    "bat_temp_warn_max",
                    "Battery Temp Warning Max",
                    21,
                    "°C",
                    "temperature",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "bat_temp_warn_min",
                    "Battery Temp Warning Min",
                    22,
                    "°C",
                    "temperature",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "limit_inv_power",
                    "Inverter Current Max Power",
                    27,
                    "W",
                    "power",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "limit_inv_max",
                    "Inverter Nominal Power Limit",
                    29,
                    "W",
                    "power",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "battery_voltage",
                    "Battery Voltage",
                    55,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "battery_current",
                    "Battery Current",
                    57,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "battery_temperature",
                    "Battery Temperature",
                    59,
                    "°C",
                    "temperature",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "voltage_l1",
                    "Grid Voltage L1",
                    61,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "voltage_l2",
                    "Grid Voltage L2",
                    63,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "voltage_l3",
                    "Grid Voltage L3",
                    65,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "current_l1",
                    "Grid Current L1",
                    67,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "current_l2",
                    "Grid Current L2",
                    69,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "current_l3",
                    "Grid Current L3",
                    71,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "inverter_temperature",
                    "Inverter Temperature",
                    73,
                    "°C",
                    "temperature",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "frequency",
                    "Grid Frequency",
                    75,
                    "Hz",
                    "frequency",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv1_voltage",
                    "PV String 1 Voltage",
                    77,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv2_voltage",
                    "PV String 2 Voltage",
                    79,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv3_voltage",
                    "PV String 3 Voltage",
                    81,
                    "V",
                    "voltage",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv1_current",
                    "PV String 1 Current",
                    83,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv2_current",
                    "PV String 2 Current",
                    85,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
                RegisterDef(
                    "pv3_current",
                    "PV String 3 Current",
                    87,
                    "A",
                    "current",
                    "measurement",
                    "diagnostic",
                ),
            ],
        ),
        BlockDef(
            start_register=42081,
            num_read_regs=4,
            content=[
                RegisterDef(
                    "battery_count",
                    "Battery Module Count",
                    0,
                    None,
                    "battery",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "soc_battery_1",
                    "SOC Battery 1",
                    1,
                    "%",
                    "battery",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "soc_battery_2",
                    "SOC Battery 2",
                    2,
                    "%",
                    "battery",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
                RegisterDef(
                    "soc_battery_3",
                    "SOC Battery 3",
                    3,
                    "%",
                    "battery",
                    "measurement",
                    "diagnostic",
                    size=1,
                ),
            ],
        ),
        BlockDef(
            start_register=42161,
            content=[
                RegisterDef(
                    "grid_import_total",
                    "Grid Import Total",
                    0,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "grid_import_today",
                    "Grid Import Today",
                    2,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "grid_export_total",
                    "Grid Export Total",
                    16,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "grid_export_today",
                    "Grid Export Today",
                    18,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "bat_charged_total",
                    "Battery Charged Total",
                    64,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "bat_charged_today",
                    "Battery Charged Today",
                    66,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "bat_discharged_total",
                    "Battery Discharged Total",
                    80,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "bat_discharged_today",
                    "Battery Discharged Today",
                    82,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "solar_total",
                    "Solar Yield Total",
                    96,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
                RegisterDef(
                    "solar_today",
                    "Solar Yield Today",
                    98,
                    "kWh",
                    "energy",
                    "total_increasing",
                ),
            ],
        ),
    ],
}
