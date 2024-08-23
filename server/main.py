import threading
from server.core.http_server import run_http_server
from server.core.hako_pdu_comm_websocket_impl import HakoPduCommWebSocketImpl
from server.core.rest_api import run_rest_api_server
from server.core.hako_pdu_server import run_hako_pdu_service

if __name__ == "__main__":
    # HTTPサーバーを別スレッドで実行
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # WebSocketサーバーを別スレッドで実行
    websocket_thread = threading.Thread(target=lambda: HakoPduCommWebSocketImpl.get_instance().run(host='localhost', port=8765))
    websocket_thread.start()

    # PDUサービスを別スレッドで実行
    pdu_service_thread = threading.Thread(target=lambda: run_hako_pdu_service(HakoPduCommWebSocketImpl.get_instance()))
    pdu_service_thread.start()

    # REST APIサーバーをメインスレッドで実行
    run_rest_api_server()
