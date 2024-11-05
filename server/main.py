import argparse
import threading
from server.core.http_server import run_http_server
from server.core.hako_pdu_comm_websocket_impl import HakoPduCommWebSocketImpl
from server.core.rest_api import run_rest_api_server
from server.core.hako_pdu_server import run_hako_pdu_service

def main(asset_name, config_path, delta_time_usec):
    # HTTPサーバーを別スレッドで実行
    print("INFO: start http server")
    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()

    # WebSocketサーバーを別スレッドで実行
    print("INFO: start websocket server")
    websocket_thread = threading.Thread(target=lambda: HakoPduCommWebSocketImpl.get_instance().run(host='0.0.0.0', port=8765))
    websocket_thread.start()

    # PDUサービスを別スレッドで実行
    pdu_service_thread = threading.Thread(
        target=lambda: run_hako_pdu_service(HakoPduCommWebSocketImpl.get_instance(), asset_name, config_path, delta_time_usec)
    )
    pdu_service_thread.start()

    # REST APIサーバーをメインスレッドで実行
    run_rest_api_server()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hakoniwa PDU Web Server")
    parser.add_argument('--asset_name', type=str, required=True, help='The name of the asset')
    parser.add_argument('--config_path', type=str, required=True, help='The path to the configuration file')
    parser.add_argument('--delta_time_usec', type=int, required=True, help='Delta time in microseconds')

    args = parser.parse_args()

    main(args.asset_name, args.config_path, args.delta_time_usec)
