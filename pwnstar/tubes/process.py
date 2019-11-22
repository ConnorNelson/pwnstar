import os
import time
import logging
import asyncio

from .utils import log


logger = logging.getLogger('pwnstar.tubes.process')


class ProcessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, pwnstar):
        self.pwnstar = pwnstar

    @log(logger)
    def pipe_data_received(self, fd, data):
        data = self.pwnstar.on_recv(data, fd)
        if self.pwnstar.gateway_write:
            self.pwnstar.gateway_write(data)

    @log(logger)
    def pipe_connection_lost(self, fd, exc):
        self.pwnstar.on_recv(b'', fd)

    @log(logger)
    def process_exited(self):
        self.pwnstar.on_exit()
        if self.pwnstar.gateway_close:
            self.pwnstar.gateway_close()
