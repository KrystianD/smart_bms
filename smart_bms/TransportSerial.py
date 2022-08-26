import asyncio
from concurrent.futures import ThreadPoolExecutor

import serial

from smart_bms.ITransport import ITransport

ReadTimeout = 1


class TransportSerial(ITransport):
    def __init__(self, port: str):
        self._serial = serial.Serial(port=port,
                                     timeout=ReadTimeout,
                                     baudrate=9600,
                                     bytesize=serial.EIGHTBITS,
                                     parity=serial.PARITY_NONE,
                                     stopbits=serial.STOPBITS_ONE)
        self._executor = ThreadPoolExecutor(max_workers=1)

    def close(self):
        self._executor.shutdown()
        self._serial.close()

    async def write(self, data: bytes):
        self._serial.write(data)

    async def read(self, size: int) -> bytes:
        data = await asyncio.get_event_loop().run_in_executor(self._executor, self._serial.read, size)
        if len(data) == 0:
            raise asyncio.exceptions.TimeoutError()
        return data

    def flush_input(self):
        self._serial.flushInput()


__all__ = [
    "TransportSerial",
]
