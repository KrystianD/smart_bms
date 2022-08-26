import io
import struct
from dataclasses import dataclass
from typing import List

from smart_bms.ITransport import ITransport


class ReadException(Exception):
    pass


START_MARK = 0xdd
READ_COMMAND = 0xa5

COMMAND_BASIC_INFO = 3
COMMAND_CELL_VOLTAGES = 4


def calc_crc(data: bytes) -> int:
    return 0xffff - sum(data) + 1


def create_request_frame(cmd, payload):
    data_w_len = struct.pack("BB", cmd, len(payload)) + payload

    crc_data = struct.pack(">H", calc_crc(data_w_len))

    cmdb = struct.pack("BB", START_MARK, READ_COMMAND) + data_w_len + crc_data + b"\x77"

    return cmdb


def read_from_stream(stream: io.BytesIO, fmt: str):
    size = struct.calcsize(fmt)
    data = stream.read(size)
    values = struct.unpack(">" + fmt, data)
    return values[0]


@dataclass
class SmartBMSBasicInformation:
    voltage: int
    current: int
    remaining_capacity: int
    nominal_capacity: int
    cycles: int
    prod_date: int
    protection_status: int
    soft_ver: int
    rem_cap: int
    charging_enabled: bool
    discharging_enabled: bool
    cells_count: int
    temperatures: List[float]
    cell_balancing_status: List[bool]


class SmartBMSClient:
    def __init__(self, transport: ITransport):
        self._transport = transport

    async def read_basic_information(self) -> SmartBMSBasicInformation:
        data_payload = await self._send_command(COMMAND_BASIC_INFO, b"")

        s = io.BytesIO(data_payload)

        voltage = read_from_stream(s, "H")
        current = read_from_stream(s, "h")
        remaining_capacity = read_from_stream(s, "H")
        nominal_capacity = read_from_stream(s, "H")
        cycles = read_from_stream(s, "H")
        prod_date = read_from_stream(s, "H")
        low_balance = read_from_stream(s, "H")
        high_balance = read_from_stream(s, "H")
        protection_status = read_from_stream(s, "H")
        soft_ver = read_from_stream(s, "B")
        rem_cap = read_from_stream(s, "B")
        mos_status = read_from_stream(s, "B")
        cells_count = read_from_stream(s, "B")
        num_temp = read_from_stream(s, "B")

        temperatures = [(read_from_stream(s, "H") - 2731) / 10 for _ in range(num_temp)]

        cell_balancing_status = []
        for i in range(cells_count):
            if i < 16:
                is_balancing = (low_balance & (1 << i)) != 0
            else:
                is_balancing = (high_balance & (1 << (i - 16))) != 0
            cell_balancing_status.append(is_balancing)

        return SmartBMSBasicInformation(
            voltage=voltage * 10,
            current=current * 10,
            remaining_capacity=remaining_capacity * 10,
            nominal_capacity=nominal_capacity * 10,
            cycles=cycles,
            prod_date=prod_date,
            protection_status=protection_status,
            soft_ver=soft_ver,
            rem_cap=rem_cap,
            charging_enabled=(mos_status & 0x01) != 0,
            discharging_enabled=(mos_status & 0x02) != 0,
            cells_count=cells_count,
            temperatures=temperatures,
            cell_balancing_status=cell_balancing_status,
        )

    async def read_cell_voltages(self):
        data_payload = await self._send_command(COMMAND_CELL_VOLTAGES, b"")
        count = len(data_payload) // 2
        s = io.BytesIO(data_payload)
        return [read_from_stream(s, "H") for _ in range(count)]

    async def _send_command(self, cmd: int, payload: bytes) -> bytes:
        request = create_request_frame(cmd, payload)
        await self._transport.write(request)

        self._transport.flush_input()

        start_mark = await self._read_all(1)
        if start_mark[0] != START_MARK:
            raise ReadException()

        resp_code = await self._read_all(1)
        if resp_code[0] != cmd:
            raise ReadException()

        status_len = await self._read_all(2)

        status, len_ = struct.unpack("BB", status_len)
        if status != 0:
            raise ReadException()

        data_payload = await self._read_all(len_)

        crc_read = await self._read_all(3)

        crc_expected = struct.pack(">H", calc_crc(struct.pack("BB", status, len_) + data_payload))
        assert crc_read[:-1] == crc_expected

        return data_payload

    async def _read_all(self, size: int):
        remaining = size
        data = b""

        while len(data) < size:
            data += await self._transport.read(remaining)
            remaining -= len(data)

        return data


__all__ = [
    "ReadException",
    "SmartBMSBasicInformation",
    "SmartBMSClient",
]
