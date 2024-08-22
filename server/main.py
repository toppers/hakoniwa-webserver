import asyncio
from aiohttp import web
import aiohttp_cors
import os
import threading
from core.hako_web_server import HakoWebSocketServer
from http.server import SimpleHTTPRequestHandler, HTTPServer

class StaticFileHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        script_dir = os.path.dirname(__file__)
        static_dir = os.path.join(script_dir, 'static')
        os.chdir(static_dir)
        super().__init__(*args, directory='.', **kwargs)

def run_http_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, StaticFileHandler)
    print("Starting HTTP server on port 8000...")
    httpd.serve_forever()

async def start_handler(request):
    data = await request.json()
    if data.get('event') == 'start':
        print("Received START event via REST API")
        await websocket_server.send_to_clients("START event triggered!")  # 非同期で呼び出す
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

def run_websocket_server():
    global websocket_server
    websocket_server = HakoWebSocketServer()

    # 新しいイベントループを作成し、スレッドに設定
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    websocket_server.run(host='localhost', port=8765)

if __name__ == "__main__":
    # HTTPサーバーを別スレッドで実行
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # WebSocketサーバーを別スレッドで実行
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.start()

    # REST APIサーバーをメインスレッドで実行
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = loop.run_until_complete(init_app())
    web.run_app(app, host='localhost', port=8080)
