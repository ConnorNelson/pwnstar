#!/usr/bin/env python

import sys
import argparse
import json
import logging
import asyncio

from pwnstar.tubes import ProcessProtocol


logging.basicConfig(level=logging.INFO)


async def run_server(protocol_factory, host, port):
    loop = asyncio.get_running_loop()

    server = await loop.create_server(protocol_factory,
                                      host=host,
                                      port=port)

    async with server:
        await server.serve_forever()


async def run_local(protocol_factory):
    loop = asyncio.get_running_loop()

    gateway = protocol_factory()

    await loop.connect_read_pipe(lambda: gateway, sys.stdin)
    await loop.connect_write_pipe(lambda: gateway, sys.stdout)

    await gateway.exit_future

    return gateway.history


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', nargs=2, metavar=('host', 'port'))
    parser.add_argument('--history', default=None, type=argparse.FileType('w'))
    parser.add_argument('--remote', nargs=2, metavar=('host', 'port'))
    parser.add_argument('local', nargs='*')
    args = parser.parse_args()

    if args.local and args.remote:
        parser.error('cannot have both local and remote arguments')
    elif not (args.local or args.remote):
        parser.error('must have local or remote arguments')

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

    if args.local:
        def protocol_factory():
            return ProcessProtocol(args.local)

    if args.server:
        await run_server(protocol_factory, *args.server)

    else:
        history = await run_local(protocol_factory)

    if args.history:
        json_data = json.dump(
            [{
                k: v if type(v) is not bytes else v.decode('latin')
                for k, v in e.items()
            }
            for e in history],
            args.history,
            indent=4)


def main():
    asyncio.run(async_main())


if __name__ == '__main__':
    main()
