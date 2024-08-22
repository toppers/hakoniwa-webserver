import asyncio
from core.hako_web_server import HakoWebSocketServer

def get_websocket_server():
    websocket_server = HakoWebSocketServer()

    # 新しいイベントループを作成し、スレッドに設定
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return websocket_server

def run_websocket_server():
    websocket_server = get_websocket_server()
    websocket_server.run(host='localhost', port=8765)
