import os
import time
import logging
import asyncio

from .utils import log


logger = logging.getLogger('pwnstar.tubes.process')


class ProcessProtocol(asyncio.Protocol):
    def __init__(self, proc_args):
        self.proc_args = proc_args
        self.exit_future = asyncio.Future()
        self.history = []

    @log(logger)
    def connection_made(self, transport):
        loop = asyncio.get_running_loop()

        async def start_target():
            target_transport, target_protocol = await loop.subprocess_exec(
                lambda: TargetProcessProtocol(transport,
                                              self.exit_future,
                                              self.history),
                *self.proc_args,
                close_fds=False,
                env=os.environ)

            self.target_transport = target_transport

        if isinstance(transport, asyncio.WriteTransport):
            loop.create_task(start_target())

    @log(logger)
    def data_received(self, data):
        self.target_transport.get_pipe_transport(0).write(data)
        self.history.append({
            'direction': 'input',
            'data': data,
            'time': time.time()
        })

    @log(logger)
    def eof_received(self):
        self.target_transport.get_pipe_transport(0).write_eof()
        self.history.append({
            'direction': 'input',
            'data': b'',
            'time': time.time()
        })
        return True  # keep connection open

    @log(logger)
    def connection_lost(self, exc):
        pass


class TargetProcessProtocol(asyncio.SubprocessProtocol):
    def __init__(self, gateway_transport, exit_future, history):
        self.gateway_transport = gateway_transport
        self.exit_future = exit_future
        self.history = history

    @log(logger)
    def connection_made(self, transport):
        pass

    @log(logger)
    def pipe_data_received(self, fd, data):
        result = self.gateway_transport.write(data)
        self.history.append({
            'direction': 'output',
            'data': data,
            'time': time.time(),
            'fd': fd
        })

    @log(logger)
    def pipe_connection_lost(self, fd, exc):
        self.history.append({
            'direction': 'output',
            'data': b'',
            'time': time.time(),
            'fd': fd
        })

    @log(logger)
    def process_exited(self):
        self.gateway_transport.close()
        self.exit_future.set_result(True)

    @log(logger)
    def connection_lost(self, exc):
        pass
