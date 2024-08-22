import threading
from server.core.http_server import run_http_server
from server.core.websocket_server import run_websocket_server
from server.core.rest_api import run_rest_api_server

if __name__ == "__main__":
    # HTTPサーバーを別スレッドで実行
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # WebSocketサーバーを別スレッドで実行
    websocket_thread = threading.Thread(target=run_websocket_server)
    websocket_thread.start()

    # REST APIサーバーをメインスレッドで実行
    run_rest_api_server()
