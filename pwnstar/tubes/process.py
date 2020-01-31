import os
import time
import logging
import asyncio

from .utils import log


logger = logging.getLogger('pwnstar.tubes.process')


class ProcessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, proxy):
        self.proxy = proxy

    @log(logger)
    def pipe_data_received(self, fd, data):
        self.proxy.on_recv(data, fd)

    @log(logger)
    def pipe_connection_lost(self, fd, exc):
        self.proxy.on_recv(b'', fd)

    @log(logger)
    def process_exited(self):
        self.proxy.on_exit()
