import logging
import asyncio

from .utils import log


logger = logging.getLogger("pwnstar.tubes.remote")


class RemoteProtocol(asyncio.Protocol):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    @log(logger)
    def connection_made(self, transport):
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
