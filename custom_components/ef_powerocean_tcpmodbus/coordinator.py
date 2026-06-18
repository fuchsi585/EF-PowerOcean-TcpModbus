"""DataUpdateCoordinator for EcoFlow PowerOcean Plus."""

from __future__ import annotations

import asyncio
import logging
import struct
from datetime import timedelta

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    LIMIT_CHARGE,
    LIMIT_DISCHARGE,
    PV_CURRENT_THRESHOLD,
    DEFAULT_SLAVE,
    MOD_REGISTER_MAP,
    DEFAULT_BATTERY_COUNT,
)

_LOGGER = logging.getLogger(__name__)

SLEEP_TIME_AFTER_RECONNECT = 1
SLEEP_TIME_AFTER_HEARTBEAT_FAILED = 35


class EcoflowCoordinator(DataUpdateCoordinator):
    """Fetches data from EcoFlow PowerOcean Plus via Modbus TCP."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        battery_capacity: float,
        scan_interval: int,
        pv_strings: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host = host
        self.port = port
        self._battery_capacity = battery_capacity
        self._pv_strings = pv_strings
        self.serial_number: str | None = None
        self._client: AsyncModbusTcpClient = AsyncModbusTcpClient(
            self.host, port=self.port, timeout=5, reconnect_delay=0, retries=0
        )
        self._client.unit_id = DEFAULT_SLAVE
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Modbus helpers
    # ------------------------------------------------------------------
    async def async_client_shutdown(self) -> None:
        """Integration-Shutdown, closing connection"""
        _LOGGER.info("PowerOcean Shutdown. Closing Connection!")
        self._client.close()
        await super().async_shutdown()

    async def async_connect_client(self) -> None:
        """First Client-Connect"""
        await self._client.connect()

        if not self._client.connected:
            _LOGGER.error("Modbus TCP not connected to %s:%s", self.host, self.port)
        else:
            self.serial_number = await self.async_get_serial_number()
            _LOGGER.info(
                "Modbus TCP is connected to %s:%s (SN: %s)",
                self.host,
                self.port,
                self.serial_number,
            )

    async def async_get_serial_number(self) -> str:
        raw = await self.async_read_block(MOD_REGISTER_MAP["serial_number"], 8)
        sn = "".join(chr((r >> 8) & 0xFF) + chr(r & 0xFF) for r in raw)
        return sn.strip().replace("\x00", "")

    async def async_reconnect(self) -> bool:
        """Client-Reconnect"""
        delays = [0, 5, 30, 120]
        _LOGGER.info("PowerOcean is not connected. Start reconnect!")

        for i, delay in enumerate(delays):
            async with self._lock:
                if delay > 0:
                    _LOGGER.info(f"Reconnect failed! Wait {delay}s until next attempt.")
                    await asyncio.sleep(delay)

                _LOGGER.info(f"Modbus TCP reconnect (Attempt {i + 1}/4)...")
                if await self._client.connect() and self._client.connected:
                    _LOGGER.info("Reconnect successful!")
                    await asyncio.sleep(SLEEP_TIME_AFTER_RECONNECT)
                    return True
                self._client.close()

        _LOGGER.info(
            "EF-Modbus-TCP: All reconnect attempts failed! – will retry next poll"
        )
        return False

    async def async_read_block(self, addr: int, count: int) -> list[int] | None:
        """Read *count* holding registers starting at *addr*.  Returns None on error."""
        async with self._lock:
            res = await self._client.read_holding_registers(addr, count=count)
            if res.isError():
                # Modbus error response – connection may be stale
                raise ModbusException(
                    f"Modbus error response at 0x{addr:04X} with Exception-Code {res.exception_code}"
                )
            return res.registers

    @staticmethod
    def _decode_register(
        regs: list[int], register_index: int, register_size: int
    ) -> float:
        """Decode a word-swapped 32-bit IEEE 754 float from two 16-bit registers."""
        if not regs:
            return None
        elif register_size == 1:
            return round(float(regs[register_index]), 2)
        elif len(regs) < register_index + 2:
            return None

        try:
            raw = struct.pack("<HH", regs[register_index], regs[register_index + 1])
            value = struct.unpack("<f", raw)[0]
        except struct.error, TypeError:  # FIX: korrekte Python-3-Syntax
            return None

        if abs(value) > 1e9 or value != value:  # guard against NaN / inf
            return None
        return round(value, 2)

    def _get_calculated_values(self, data: dict) -> dict:
        calc_data = {}
        calc_data["battery_capacity"] = self._battery_capacity  # user-configured kWh
        calc_data["bat_remaining"] = round(
            self._battery_capacity * data["battery_soc"] / 100, 2
        )
        calc_data["limit_discharge"] = round(
            data["battery_count"] * LIMIT_DISCHARGE
        )  # 3.3 kW per module
        calc_data["limit_charge"] = round(data["battery_count"] * LIMIT_CHARGE)
        calc_data["bat_net_energy"] = round(
            data["bat_charged_total"] - data["bat_discharged_total"], 2
        )
        calc_data["house_energy_today"] = round(
            data.get("solar_today", 0)
            + data.get("grid_import_today", 0)
            - data.get("grid_export_today", 0)
            - data.get("bat_charged_today", 0)
            + data.get("bat_discharged_today", 0),
            2,
        )
        calc_data["house_energy_total"] = round(
            data.get("solar_total", 0)
            + data.get("grid_import_total", 0)
            - data.get("grid_export_total", 0)
            - data.get("bat_charged_total", 0)
            + data.get("bat_discharged_total", 0),
            0,
        )
        calc_data["pv1_power"] = round(
            data["pv1_current"] * (data["pv1_voltage"] or 0.0), 1
        )
        calc_data["pv2_power"] = round(
            data["pv2_current"] * (data["pv2_voltage"] or 0.0), 1
        )
        calc_data["pv3_power"] = round(
            data["pv3_current"] * (data["pv3_voltage"] or 0.0), 1
        )

        return calc_data

    # ------------------------------------------------------------------
    # Data fetch
    # ------------------------------------------------------------------

    async def _fetch_all(self) -> dict:
        data: dict = {}

        # ── Check Connection, if not -> start reconnection ──
        if not self._client.connected and not await self.async_reconnect():
            raise UpdateFailed("Reconnect failed!")

        try:
            # Read all register blocks
            for register_block in MOD_REGISTER_MAP["blocks"]:
                raw = await self.async_read_block(
                    register_block.start_register, register_block.num_read_regs
                )
                for register in register_block.content:
                    decode_value = self._decode_register(
                        raw, register.block_index, register.size
                    )
                    data[register.key] = decode_value

            if data["battery_count"] != DEFAULT_BATTERY_COUNT:
                _LOGGER.info(
                    f"Readed battery count {data['battery_count']} is unequal -> Skip data! Wait 35s for reconnect!"
                )
                self._client.close()
                await asyncio.sleep(SLEEP_TIME_AFTER_HEARTBEAT_FAILED)
                return None

            data.update(self._get_calculated_values(data))
            return data
        except ModbusException as err:
            _LOGGER.debug(f"Modbus-Error: {repr(err)}. Connection closing...")
            self._client.close()
            return None
        except Exception as err:
            _LOGGER.error(f"Unexpected error during data fetch: {repr(err)}")
            return data

            # # ── Block A: Serial number + operation mode (40004, 12 regs) ──────────
            # if a := await self._read_block(_REG_SERIAL, 12):
            #     # Serial number is ASCII-encoded across registers 0-7 (2 chars each)
            #     sn = "".join(chr((r >> 8) & 0xFF) + chr(r & 0xFF) for r in a[0:8])
            #     data["serial_number"] = sn.strip().replace("\x00", "")
            #     data["operation_mode"] = a[9] if len(a) > 9 else None

            #     data["solar_power"] = max(self._f(b, 4), 0.0)  # 40523 ✅

            #     # Apply threshold to filter phantom currents, zero out unconfigured strings
            #     def _pv_current(raw: float, string_nr: int) -> float:
            #         if string_nr > self._pv_strings:
            #             return 0.0
            #         return raw if raw >= PV_CURRENT_THRESHOLD else 0.0  # FIX: >= statt >

            #     data["pv1_current"] = _pv_current(self._f(d, 22), 1)  # 40602 ✅
            #     data["pv2_current"] = _pv_current(self._f(d, 24), 2)  # 40604 ✅
            #     data["pv3_current"] = _pv_current(
            #         self._f(d, 26), 3
            #     )  # 40606 ⚠️ not in verified list

            #     # FIX: PV-Leistung pro String mit eigener Spannung berechnen
            #     data["pv1_power"] = round(data["pv1_current"] * (data["pv1_voltage"] or 0.0), 1)
            #     data["pv2_power"] = round(data["pv2_current"] * (data["pv2_voltage"] or 0.0), 1)
            #     data["pv3_power"] = round(data["pv3_current"] * (data["pv3_voltage"] or 0.0), 1)

            #     # Solar power: sum of active strings only
            #     data["solar_power"] = round(
            #         sum(data[f"pv{i}_power"] for i in range(1, self._pv_strings + 1)), 1
            #     )

            #     # Grid power: if register 40521 gave None, derive from energy balance as fallback
            #     if data.get("grid_power", None) is None:
            #         house = data.get("house_power", 0)
            #         solar = data.get("solar_power", 0)
            #         bat = data.get("battery_power", 0)
            #         if any(v != 0 for v in [house, solar, bat]):
            #             data["grid_power"] = round(house - solar + bat, 1)
            #             _LOGGER.info(
            #                 f"grid_power derived from balance: {data['grid_power']} W"
            #             )

    async def _async_update_data(self) -> dict:
        try:
            return await self._fetch_all()
        except UpdateFailed:  # noqa: BLE001
            raise UpdateFailed(
                "Reconnect attempts failed! Integration stopped. Retry after 120s.",
                retry_after=120,
            )
