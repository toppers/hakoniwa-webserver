import threading
from server.core.http_server import run_http_server
from server.core.hako_web_server import HakoWebSocketServer
from server.core.rest_api import run_rest_api_server

if __name__ == "__main__":
    # HTTPサーバーを別スレッドで実行
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # WebSocketサーバーを別スレッドで実行
    websocket_thread = threading.Thread(target=lambda: HakoWebSocketServer.get_instance().run(host='localhost', port=8765))
    websocket_thread.start()

    # REST APIサーバーをメインスレッドで実行
    run_rest_api_server()
