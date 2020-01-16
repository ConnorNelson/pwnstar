import logging
import asyncio

from .utils import log


logger = logging.getLogger('pwnstar.tubes.gateway')


class GatewayProtocol(asyncio.Protocol):
    def __init__(self, create_target, proxy):
        self.create_target = create_target
        self.proxy = proxy

    def connection_made(self, transport):
        if isinstance(transport, asyncio.WriteTransport):
            self.proxy.gateway_write = transport.write
            self.proxy.gateway_write_eof = transport.write_eof
            self.proxy.gateway_close = transport.close
            asyncio.get_running_loop().create_task(self.create_target(self.proxy))

    @log(logger)
    def data_received(self, data):
        data = self.proxy.on_send(data)
        self.proxy.target_write(data)

    @log(logger)
    def eof_received(self):
        data = self.proxy.on_send(b'')
        self.proxy.target_write_eof()
        return True  # keep connection open
