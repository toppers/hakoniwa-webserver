import asyncio
import hakopy
import hako_pdu
import pdu_info
import threading
import copy
import sys
import time
from server.core.hako_pdu_comm_interface import HakoPduCommInterface, HakoPduInfo


def my_on_initialize(context):
    print("INFO: hako asset initialize")
    return 0

def my_on_reset(context):
    print("INFO: hako asset reset")
    return 0

async def on_simulation_step_async(context):
    print("INFO: on_simulation_step_async")
    server_instance = HakoPduServer.get_instance()
    if server_instance is None:
        raise RuntimeError("HakoPduServer has not been initialized")
    
    #TODO get pdu data and publish
    pdu_info = HakoPduInfo(pdu_type="example_type", pdu_name="example_name")
    pdu_data_json = '{"key": "value"}'
    print("Publishing PDU")
    await server_instance.socket.publish_pdu(pdu_info, pdu_data_json)
    return 0

def on_simulation_step(context):
    print("INFO: on_simulation_step")
    #TODO read pdu data

    #TODO put pdu data on cache
    time.sleep(1)
    return 0

my_callback = {
    'on_initialize': my_on_initialize,
    'on_simulation_step': on_simulation_step,
    'on_manual_timing_control': None,
    'on_reset': my_on_reset
}


class HakoPduServer:
    _instance = None

    @classmethod
    def get_instance(cls, socket=None, asset_name=None, config_path=None, delta_time_usec=None):
        if cls._instance is None:
            if None in (socket, asset_name, config_path, delta_time_usec):
                raise ValueError("HakoPduServer instance not initialized. Missing arguments.")
            cls._instance = HakoPduServer(socket, asset_name, config_path, delta_time_usec)

        return cls._instance

    def __init__(self, socket: HakoPduCommInterface, asset_name: str, config_path: str, delta_time_usec):
        self.socket = socket
        self.pdu_manager = hako_pdu.HakoPduManager('/usr/local/lib/hakoniwa/hako_binary/offset', config_path)
        self.delta_time_usec = delta_time_usec
        ret = hakopy.asset_register(asset_name, config_path, my_callback, delta_time_usec, hakopy.HAKO_ASSET_MODEL_CONTROLLER)
        if ret == False:
            print(f"ERROR: hako_asset_register() returns {ret}.")
            return 1
        self.pdu_buffers = {}
        self.lock = threading.Lock()

    def put_pdu_data(self, name: str, data):
        with self.lock:
            self.pdu_buffers[name] = data

    def get_pdu_data(self, name: str):
        with self.lock:
            if name in self.pdu_buffers:
                data = self.pdu_buffers[name]
                self.pdu_buffers[name] = None
                return data            
            else:
                return None

    async def start_service(self):
        print("HakoPduService is starting...")
        ret = hakopy.start()
        print(f"INFO: hako_asset_start() returns {ret}")


def periodic_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        loop.run_until_complete(on_simulation_step_async(None))
        time.sleep(1)

def start_periodic_thread():
    # 新しいスレッドを作成し、定期的に非同期タスクを実行
    thread = threading.Thread(target=periodic_task)
    thread.start()

def run_hako_pdu_service(socket: HakoPduCommInterface, asset_name: str, config_path: str, delta_time_usec: int):
    service = HakoPduServer.get_instance(socket, asset_name, config_path, delta_time_usec)
    
    # 定期実行スレッドを開始
    start_periodic_thread()
    
    asyncio.run(service.start_service())  # 非同期関数を実行