import sys
import pathlib
import asyncio

from aiohttp import web

import pwnstar.tubes
# TODO: deal with custom proxy


async def run_server(create_target, create_proxy, *, host, port):
    loop = asyncio.get_running_loop()

    def protocol_factory():
        proxy = create_proxy()
        return pwnstar.tubes.GatewayProtocol(create_target, proxy)

    server = await loop.create_server(protocol_factory, host=host, port=port)

    async with server:
        await server.serve_forever()


async def run_webserver(create_target, create_proxy, *, host, port, tty=False):
    loop = asyncio.get_running_loop()
    static_dir = pathlib.Path(__file__).parent / 'ws_static'

    async def index_handler(request):
        return web.FileResponse(static_dir / 'index.html')

    async def tty_handler(request):
        return web.json_response(tty)

    async def ws_handler(request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        proxy = create_proxy()

        proxy.gateway_write = lambda data: loop.create_task(ws.send_bytes(data))
        proxy.gateway_write_eof = lambda: loop.create_task(ws.close())  # TODO: maybe should be websocket.transport.write_eof? Need to think about websocket shutdown semantics
        proxy.gateway_close = lambda: loop.create_task(ws.close())

        target = await create_target(proxy)

        async for msg in ws:
            data = msg.data.encode()
            if not data:
                data = proxy.on_send(b'')
                proxy.target_write_eof()
                # await websocket.wait_closed()
                # break
            data = proxy.on_send(data)
            proxy.target_write(data)

    app = web.Application()
    app.add_routes([web.get('/', index_handler),
                    web.get('/tty', tty_handler),
                    web.get('/ws', ws_handler),
                    web.static('/',  static_dir, show_index=True)])

    await web._run_app(app, host=host, port=port)


async def run_local(create_target, create_proxy):
    loop = asyncio.get_running_loop()

    proxy = create_proxy()

    exit_future = asyncio.Future()
    original_exit = proxy.on_exit
    def on_exit(self):
        result = original_exit()
        exit_future.set_result(True)
        return result
    proxy.on_exit = on_exit.__get__(proxy)

    gateway = pwnstar.tubes.GatewayProtocol(create_target, proxy)

    await loop.connect_read_pipe(lambda: gateway, sys.stdin)
    await loop.connect_write_pipe(lambda: gateway, sys.stdout)

    await exit_future

    if proxy.target_get_returncode:
        return_code = proxy.target_get_returncode()
    else:
        return_code = 0

    return return_code
