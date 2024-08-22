import asyncio
from core.hako_web_server import HakoWebSocketServer

# グローバルなWebSocketサーバーインスタンス
_websocket_server = None

def get_websocket_server():
    global _websocket_server
    if _websocket_server is None:
        _websocket_server = HakoWebSocketServer()

        # 新しいイベントループを作成し、スレッドに設定
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return _websocket_server

def run_websocket_server():
    websocket_server = get_websocket_server()
    websocket_server.run(host='localhost', port=8765)
