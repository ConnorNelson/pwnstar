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
        self.pwnstar.gateway_write(data)

    @log(logger)
    def eof_received(self):
        data = self.pwnstar.on_recv(b'')
        self.pwnstar.gateway_write_eof()
