import logging
import asyncio

from .utils import log


logger = logging.getLogger("pwnstar.tubes.remote")


class RemoteProtocol(asyncio.Protocol):
    def __init__(self, pwnstar):
        self.pwnstar = pwnstar

    @log(logger)
    def data_received(self, data):
        data = self.pwnstar.on_recv(data)
        if self.pwnstar.gateway_write:
            self.pwnstar.gateway_write(data)

    @log(logger)
    def eof_received(self):
        data = self.pwnstar.on_recv(b'')
        if self.pwnstar.gateway_write_eof:
            self.pwnstar.gateway_write_eof()
        # TODO: May need to think about where pwnstar.on_exit should be called for network apps
        self.pwnstar.on_exit()
