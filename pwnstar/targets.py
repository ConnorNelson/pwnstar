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

    stdin = target_transport.get_pipe_transport(0)
    proxy.attach_channel(0,
                         stdin.write,
                         stdin.write_eof,
                         target_transport.get_returncode)
    proxy.target_kill = target_transport.kill


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

    proxy.attach_channel(0,
                         target_write,
                         lambda: target_write(b'\x04'),
                         target_transport.get_returncode)


async def create_remote_target(proxy, *, host=None, port=None, sock=None, channel=None):
    loop = asyncio.get_running_loop()

    if not channel:
        channel = f'{host}:{port}'

    target_transport, target_protocol = await loop.create_connection(
        lambda: pwnstar.tubes.RemoteProtocol(proxy, channel=channel),
        host=host,
        port=port,
        sock=sock)

    proxy.attach_channel(channel,
                         target_transport.write,
                         target_transport.write_eof)
