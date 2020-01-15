import logging
import asyncio

from .utils import log


logger = logging.getLogger("pwnstar.tubes.remote")


class RemoteProtocol(asyncio.Protocol):
    def __init__(self, proxy):
        self.proxy = proxy

    @log(logger)
    def data_received(self, data):
        data = self.proxy.on_recv(data)
        if self.proxy.gateway_write:
            self.proxy.gateway_write(data)

    @log(logger)
    def eof_received(self):
        data = self.proxy.on_recv(b'')
        if self.proxy.gateway_write_eof:
            self.proxy.gateway_write_eof()
        # TODO: May need to think about where proxy.on_exit should be called for network apps
        self.proxy.on_exit()
