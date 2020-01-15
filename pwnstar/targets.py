import os
import pty
import asyncio

import pwnstar.tubes


async def create_process_target(proxy, *, proc_args):
    loop = asyncio.get_running_loop()

    target_transport, target_protocol = await loop.subprocess_exec(
        lambda: pwnstar.tubes.ProcessProtocol(proxy),
        *proc_args,
        close_fds=False,
        env=os.environ)

    proxy.target_write = target_transport.get_pipe_transport(0).write
    proxy.target_write_eof = target_transport.get_pipe_transport(0).write_eof
    proxy.target_get_returncode = target_transport.get_returncode


async def create_tty_process_target(proxy, *, proc_args):
    loop = asyncio.get_running_loop()

    master, slave = pty.openpty()

    target_transport, target_protocol = await loop.subprocess_exec(
        lambda: pwnstar.tubes.ProcessProtocol(proxy),
        *proc_args,
        close_fds=False,
        stdin=slave,
        stdout=slave,
        stderr=slave,
        start_new_session=True,
        env=os.environ)

    target_transport._proc.stdin = open(master, 'wb', -1)
    target_transport._proc.stdout = open(master, 'rb', -1)
    target_transport._proc.stderr = open(master, 'rb', -1)
    await target_transport._connect_pipes(None)

    def target_write(data):
        target_transport._proc.stdin.write(data)
        target_transport._proc.stdin.flush()

    proxy.target_write = target_write
    proxy.target_write_eof = lambda: target_write(b'\x04')
    proxy.target_get_returncode = target_transport.get_returncode


async def create_remote_target(proxy, *, host, port):
    loop = asyncio.get_running_loop()

    target_transport, target_protocol = await loop.create_connection(
        lambda: pwnstar.tubes.RemoteProtocol(proxy),
        host,
        port)

    proxy.target_write = target_transport.write
    proxy.target_write_eof = target_transport.write_eof
