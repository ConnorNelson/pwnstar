import logging
import asyncio

from .utils import log


logger = logging.getLogger("pwnstar.tubes.remote")


class RemoteProtocol(asyncio.Protocol):
    def __init__(self, proxy, channel=None):
        self.proxy = proxy
        self.channel = channel

    @log(logger)
    def data_received(self, data):
        self.proxy.on_recv(data, self.channel)

    @log(logger)
    def eof_received(self):
        self.proxy.on_recv(b'', self.channel)
        self.proxy.on_exit()
