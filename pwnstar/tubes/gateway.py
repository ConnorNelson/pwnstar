import logging
import asyncio

from .utils import log


logger = logging.getLogger('pwnstar.tubes.gateway')


class GatewayProtocol(asyncio.Protocol):
    def __init__(self, create_target, proxy, channel=None):
        self.create_target = create_target
        self.proxy = proxy
        self.channel = channel

    def connection_made(self, transport):
        if isinstance(transport, asyncio.WriteTransport):
            self.proxy.gateway_write = lambda data, fd: transport.write(data)
            self.proxy.gateway_write_eof = lambda fd: transport.write_eof()
            self.proxy.gateway_close = transport.close
            asyncio.get_running_loop().create_task(self.create_target(self.proxy))

    @log(logger)
    def data_received(self, data):
        self.proxy.on_send(data, self.channel)

    @log(logger)
    def eof_received(self):
        self.proxy.on_send(b'', self.channel)
        return True  # keep connection open
