from abc import abstractmethod


class ITransport:
    @abstractmethod
    async def write(self, data: bytes):
        pass

    @abstractmethod
    async def read(self, size: int) -> bytes:
        pass

    @abstractmethod
    def flush_input(self):
        pass
