import sys
import json
import pathlib
import asyncio

import aiohttp
import aiohttp.web

import pwnstar.tubes


async def run_server(create_target, create_proxy, *, host, port):
    loop = asyncio.get_running_loop()

    def protocol_factory():
        proxy = create_proxy()
        return pwnstar.tubes.GatewayProtocol(create_target, proxy)

    server = await loop.create_server(protocol_factory, host=host, port=port)

    async with server:
        await server.serve_forever()


async def run_webserver(create_target, create_proxy, *, host, port, channels, start=True):
    loop = asyncio.get_running_loop()
    static_dir = pathlib.Path(__file__).parent / 'ws_static'

    async def index_handler(request):
        return aiohttp.web.FileResponse(static_dir / 'index.html')

    async def info_handler(request):
        return aiohttp.web.json_response({
            'channels': channels
        })

    async def ws_handler(request):
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)

        proxy = create_proxy()

        async def gateway_write_json(data, channel=None):
            await ws.send_bytes(json.dumps({
                'data': data.decode('latin'),
                'channel': channel
            }).encode())

        async def gateway_write_status(status, channel=None):
            await ws.send_bytes(json.dumps({
                'status': status,
                'channel': channel
            }).encode())

        proxy.gateway_write = lambda data, channel: loop.create_task(gateway_write_json(data, channel))
        proxy.gateway_write_eof = lambda channel: loop.create_task(gateway_write_status('close', channel))
        proxy.gateway_close = lambda: loop.create_task(gateway_write_status('close'))

        target = await create_target(proxy)

        await ws.send_bytes(json.dumps({
            'status': 'ready'
        }).encode())

        async for msg in ws:
            json_data = json.loads(msg.data)
            if 'signal' in json_data:
                if json_data['signal'] == 'kill' and proxy.target_kill:
                    proxy.target_kill()
                    proxy.target_killed = True
                continue
            data = json_data['data'].encode('latin')
            channel = json_data['channel']
            if data:
                proxy.on_send(data, channel)
            else:
                proxy.on_send(b'', channel)

        if not proxy.exited.done() and proxy.target_kill:
            proxy.target_kill()
            proxy.target_killed = True

    app = aiohttp.web.Application()
    app.add_routes([aiohttp.web.get('/', index_handler),
                    aiohttp.web.get('/info', info_handler),
                    aiohttp.web.get('/ws', ws_handler),
                    aiohttp.web.static('/',  static_dir, show_index=True)])

    if start:
        await aiohttp.web._run_app(app, host=host, port=port)
    else:
        return app


async def run_local(create_target, create_proxy):
    loop = asyncio.get_running_loop()

    proxy = create_proxy()

    gateway = pwnstar.tubes.GatewayProtocol(create_target, proxy)

    await loop.connect_read_pipe(lambda: gateway, sys.stdin)
    await loop.connect_write_pipe(lambda: gateway, sys.stdout)

    data = await proxy.exited
    return data['return_code']
