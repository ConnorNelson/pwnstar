#!/usr/bin/env python

import os
import sys
import time
import json
import pathlib
import pty
import argparse
import logging
import asyncio

from aiohttp import web

from pwnstar.tubes import ProcessProtocol, RemoteProtocol


logging.basicConfig(level=logging.INFO)


class Pwnstar:
    def __init__(self):
        self.gateway_write = None
        self.gateway_write_eof = None
        self.gateway_close = None
        self.target_write = None
        self.target_write_eof = None
        self.target_get_returncode = None
        self.history = []

    def on_recv(self, data, fd=None):
        self.history.append({
            'direction': 'output',
            'data': data,
            'fd': fd,
            'time': time.time()
        })
        return data

    def on_send(self, data, fd=None):
        self.history.append({
            'direction': 'input',
            'data': data,
            'fd': fd,
            'time': time.time()
        })
        return data

    def on_exit(self):
        history = [
            {
                k: v if type(v) is not bytes else v.decode('latin')
                for k, v in e.items()
            }
            for e in self.history
        ]
        data = {
            'interaction': history,
            'return_code': self.target_get_returncode() if self.target_get_returncode else None
        }

        return data


class GatewayProtocol(asyncio.Protocol):
    def __init__(self, create_target, pwnstar):
        self.create_target = create_target
        self.pwnstar = pwnstar

    def connection_made(self, transport):
        if isinstance(transport, asyncio.WriteTransport):
            self.pwnstar.gateway_write = transport.write
            self.pwnstar.gateway_write_eof = transport.write_eof
            self.pwnstar.gateway_close = transport.close
            asyncio.get_running_loop().create_task(self.create_target(self.pwnstar))

    def data_received(self, data):
        data = self.pwnstar.on_send(data)
        self.pwnstar.target_write(data)

    def eof_received(self):
        data = self.pwnstar.on_send(b'')
        self.pwnstar.target_write_eof()
        return True  # keep connection open


async def create_tty_process_target(pwnstar, *, proc_args):
    loop = asyncio.get_running_loop()

    master, slave = pty.openpty()

    target_transport, target_protocol = await loop.subprocess_exec(
        lambda: ProcessProtocol(pwnstar),
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

    pwnstar.target_write = target_write
    pwnstar.target_write_eof = lambda: target_write(b'\x04')
    pwnstar.target_get_returncode = target_transport.get_returncode


async def create_process_target(pwnstar, *, proc_args):
    loop = asyncio.get_running_loop()

    target_transport, target_protocol = await loop.subprocess_exec(
        lambda: ProcessProtocol(pwnstar),
        *proc_args,
        close_fds=False,
        env=os.environ)

    pwnstar.target_write = target_transport.get_pipe_transport(0).write
    pwnstar.target_write_eof = target_transport.get_pipe_transport(0).write_eof
    pwnstar.target_get_returncode = target_transport.get_returncode


async def create_remote_target(pwnstar, *, host, port):
    loop = asyncio.get_running_loop()

    target_transport, target_protocol = await loop.create_connection(
        lambda: RemoteProtocol(pwnstar),
        host,
        port)

    pwnstar.target_write = target_transport.write
    pwnstar.target_write_eof = target_transport.write_eof


async def run_server(create_target, host, port):
    loop = asyncio.get_running_loop()

    server = await loop.create_server(lambda: GatewayProtocol(create_target, Pwnstar()),
                                      host=host,
                                      port=port)

    async with server:
        await server.serve_forever()


async def run_webserver(create_target, host, port, *, tty=False):
    loop = asyncio.get_running_loop()
    static_dir = pathlib.Path(__file__).parent / 'ws_static'

    async def index_handler(request):
        return web.FileResponse(static_dir / 'index.html')

    async def tty_handler(request):
        return web.json_response(tty)

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        pwnstar = Pwnstar()

        pwnstar.gateway_write = lambda data: loop.create_task(ws.send_bytes(data))
        pwnstar.gateway_write_eof = lambda: loop.create_task(ws.close())  # TODO: maybe should be websocket.transport.write_eof? Need to think about websocket shutdown semantics
        pwnstar.gateway_close = lambda: loop.create_task(ws.close())

        target = await create_target(pwnstar)

        async for msg in ws:
            data = msg.data.encode()
            if not data:
                data = pwnstar.on_send(b'')
                pwnstar.target_write_eof()
                # await websocket.wait_closed()
                # break
            data = pwnstar.on_send(data)
            pwnstar.target_write(data)

    app = web.Application()
    app.add_routes([web.get('/', index_handler),
                    web.get('/tty', tty_handler),
                    web.get('/ws', ws_handler),
                    web.static('/',  static_dir, show_index=True)])

    await web._run_app(app, host=host, port=port)


async def run_local(create_target):
    loop = asyncio.get_running_loop()

    pwnstar = Pwnstar()

    exit_future = asyncio.Future()
    original_exit = pwnstar.on_exit
    def on_exit(self):
        exit_future.set_result(True)
        return original_exit()
    pwnstar.on_exit = on_exit.__get__(pwnstar)

    gateway = GatewayProtocol(create_target, pwnstar)

    await loop.connect_read_pipe(lambda: gateway, sys.stdin)
    await loop.connect_write_pipe(lambda: gateway, sys.stdout)

    await exit_future

    history = pwnstar.history
    if pwnstar.target_get_returncode:
        return_code = pwnstar.target_get_returncode()
    else:
        return_code = 0

    return history, return_code


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', nargs=2, metavar=('host', 'port'))
    parser.add_argument('--webserver', nargs=2, metavar=('host', 'port'))
    parser.add_argument('--history', default=None, type=argparse.FileType('w'))
    parser.add_argument('--tty', default=False, action='store_true')
    parser.add_argument('--returncode', default=False, action='store_true')
    parser.add_argument('--repl', default=False, action='store_true')
    parser.add_argument('--remote', nargs=2, metavar=('host', 'port'))
    parser.add_argument('process', nargs='*')
    args = parser.parse_args()

    if not (args.process or args.remote):
        parser.error('must have process and/or remote arguments')

    if args.tty and not args.process:
        parser.error('tty is only available for process')

    def valid_host_port(host, port):
        try:
            port = int(port)
        except ValueError:
            port = -1
        if port < 0 or port > 65535:
            parser.error('port must be 0-65535')
        return host, port

    if args.server:
        args.server = valid_host_port(*args.server)

    if args.remote:
        args.remote = valid_host_port(*args.remote)

    return args


async def async_main():
    args = parse_arguments()

    input_preprocessor = None
    if args.repl:
        def input_preprocessor(data, *, globals={}, locals={}, scope=[]):
            def process(data):
                try:
                    data = eval(data, globals, locals)
                    if type(data) is not bytes:
                        data = str(data).encode() + b'\n'
                    return data
                except SyntaxError:
                    exec(data, globals, locals)
                    return None

            if data == b'!!!\n':
                # It would be nice to use code.interact and drop into a proper repl sent across the transport
                if scope:
                    data = b''.join(scope[1:])
                    scope.clear()
                    data = process(data)
                else:
                    scope.append(None)
                    return None

            elif scope:
                scope.append(data)
                return None

            elif data.startswith(b'!'):
                data = process(data[1:])

            return data

    if args.process:
        if args.tty:
            def create_target(pwnstar):
                return create_tty_process_target(pwnstar, proc_args=args.process)
        elif args.remote:
            host, port = args.remote
            def create_target(pwnstar):
                async def create_targets(pwnstar):
                    def do_nothing(self):
                        pass
                    pwnstar.on_exit = do_nothing.__get__(pwnstar)
                    proc_pwnstar = Pwnstar()
                    proc_pwnstar.history = pwnstar.history
                    proc_pwnstar.gateway_close = pwnstar.gateway_close
                    await create_process_target(proc_pwnstar, proc_args=args.process)
                    await asyncio.sleep(2) # TODO: be less yolo, need to wait for port to be ready
                    await create_remote_target(pwnstar, host=host, port=port)
                return create_targets(pwnstar)
        else:
            def create_target(pwnstar):
                return create_process_target(pwnstar, proc_args=args.process)

    elif args.remote:
        host, port = args.remote
        def create_target(pwnstar):
            return create_remote_target(pwnstar, host=host, port=port)

    if args.server:
        await run_server(create_target, *args.server)

    elif args.webserver:
        await run_webserver(create_target, *args.webserver, tty=args.tty)

    else:
        history, return_code = await run_local(create_target)

    if args.history:
        history = [
            {
                k: v if type(v) is not bytes else v.decode('latin')
                for k, v in e.items()
            }
            for e in history
        ]
        json.dump(
            {'interaction': history, 'return_code': return_code},
            args.history,
            indent=4)
        args.history.close()

    if args.returncode:
        exit(return_code)


def main():
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
