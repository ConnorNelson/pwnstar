import logging
import asyncio

from .utils import log


logger = logging.getLogger("pwnstar.tubes.remote")


class RemoteProtocol(asyncio.Protocol):
    def __init__(self, host, port, *, input_preprocessor):
        self.host = host
        self.port = port
        self.input_preprocessor = input_preprocessor

    @log(logger)
    def connection_made(self, transport):
        self.transport = transport
        loop = asyncio.get_running_loop()

        async def task():
            target_transport, target_protocol = await loop.create_connection(
                lambda: TargetRemoteProtocol(transport),
                self.host,
                self.port)

            self.target_transport = target_transport

        loop.create_task(task())

    @log(logger)
    def data_received(self, data):
        if self.input_preprocessor:
            try:
                data = self.input_preprocessor(data)
                if data is None:
                    return
            except Exception as e:
                self.transport.write(str(e).encode())
                return
        self.target_transport.write(data)

    @log(logger)
    def eof_received(self):
        self.target_transport.write_eof()
        return True  # keep connection open

    @log(logger)
    def connection_lost(self, exc):
        pass


class TargetRemoteProtocol(asyncio.Protocol):
    def __init__(self, gateway_transport):
        self.gateway_transport = gateway_transport

    @log(logger)
    def connection_made(self, transport):
        pass

    @log(logger)
    def data_received(self, data):
        self.gateway_transport.write(data)

    @log(logger)
    def eof_received(self):
        self.gateway_transport.write_eof()

    @log(logger)
    def connection_lost(self, exc):
        pass
