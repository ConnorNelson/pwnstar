#!/usr/bin/env python

import sys
import pathlib
import argparse
import logging
import asyncio

import pwnstar

logging.basicConfig(level=logging.INFO)


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', nargs=2, metavar=('host', 'port'))
    parser.add_argument('--webserver', nargs=2, metavar=('host', 'port'))
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


async def async_main(process=None,
                     remote=None,
                     server=None,
                     webserver=None,
                     tty=False,
                     returncode=False,
                     repl=False):

    if process:
        if tty:
            def create_target(proxy):
                return pwnstar.create_tty_process_target(proxy, proc_args=process)
        elif remote:
            host, port = remote
            def create_target(proxy, *, host=host, port=port):
                async def create_targets(proxy):
                    def do_nothing(self):
                        pass
                    proxy.on_exit = do_nothing.__get__(proxy)
                    proc_proxy = pwnstar.Proxy()
                    proc_proxy.history = proxy.history
                    proc_proxy.gateway_close = proxy.gateway_close
                    await pwnstar.create_process_target(proc_proxy, proc_args=process)
                    await asyncio.sleep(2) # TODO: be less yolo, need to wait for port to be ready
                    await pwnstar.create_remote_target(proxy, host=host, port=port)
                return create_targets(proxy)
        else:
            def create_target(proxy):
                return pwnstar.create_process_target(proxy, proc_args=process)

    elif remote:
        host, port = remote
        def create_target(proxy, *, host=host, port=port):
            return pwnstar.create_remote_target(proxy, host=host, port=port)

    if server:
        host, port = server
        await pwnstar.run_server(create_target, pwnstar.Proxy, host=host, port=port)

    elif webserver:
        channels = list()
        if remote:
            host, port = remote
            channel = f'{host}:{port}'
            channels.append((channel, channel, [channel], False))
        if process:
            channels.append(('stdio', 0, [1, 2], tty))
        host, port = webserver
        await pwnstar.run_webserver(create_target, pwnstar.Proxy, host=host, port=port, channels=channels)

    else:
        return_code = await pwnstar.run_local(create_target, pwnstar.Proxy)

    if returncode:
        exit(return_code)


def main():
    args = parse_arguments()
    asyncio.run(async_main(args.process, args.remote, args.server, args.webserver,
                           args.tty, args.returncode, args.repl))


if __name__ == '__main__':
    main()
