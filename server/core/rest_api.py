import asyncio
from aiohttp import web
import aiohttp_cors
from core.hako_web_server import HakoWebSocketServer

# WebSocketサーバーのインスタンスを取得
websocket_server = HakoWebSocketServer.get_instance()

async def start_handler(request):
    data = await request.json()
    if data.get('event') == 'start':
        print("Received START event via REST API")
        await websocket_server.send_to_clients("START event triggered!")
        return web.json_response({'status': 'ok'})
    return web.json_response({'status': 'error'}, status=400)

async def init_app():
    app = web.Application()

    # CORS設定
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })

    # ルートの設定とCORSの適用
    resource = cors.add(app.router.add_resource("/api/start"))
    cors.add(resource.add_route("POST", start_handler))
    
    return app

def run_rest_api_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = loop.run_until_complete(init_app())
    web.run_app(app, host='localhost', port=8080)
