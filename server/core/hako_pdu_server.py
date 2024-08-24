import asyncio
import hakopy
import hako_pdu
import threading
import json
import time
from server.core.hako_pdu_comm_interface import HakoPduCommInterface, HakoPduInfo


class HakoPduCommInfo:
    def __init__(self, name: str, info):
        self.name = name
        self.info = info

def my_on_initialize(context):
    print("INFO: hako asset initialize")
    return 0

def my_on_reset(context):
    print("INFO: hako asset reset")
    return 0

async def on_simulation_step_async(context):
    on_simulation_step(context)
    #print("INFO: on_simulation_step_async")
    server_instance = HakoPduServer.get_instance()
    if server_instance is None:
        raise RuntimeError("HakoPduServer has not been initialized")
    
    for pdu_info in server_instance.pub_pdus:
        pdu_data = server_instance.get_pdu_data(pdu_info.info['name'])
        if pdu_data is not None:
            # get pdu data and publish
            pdu_info = HakoPduInfo(pdu_type=pdu_data['type'], pdu_name=pdu_data['name'])
            pdu_data_json = pdu_data['data']
            #print("Publishing PDU")
            await server_instance.socket.publish_pdu(pdu_info, pdu_data_json)
    return 0

def on_simulation_step(context):
    #print("INFO: on_simulation_step")
    server_instance = HakoPduServer.get_instance()

    for pdu_info in server_instance.pub_pdus:
        pdu = server_instance.pdu_manager.get_pdu(pdu_info.name, pdu_info.info['channel_id'])
        pdu_data = pdu.read()

        #put pdu data on cache
        server_instance.put_pdu_data(pdu_info.info['name'], pdu_info.info['type'], pdu_data)
    #time.sleep(server_instance.slp_time_sec)
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
        self.config_json = self._load_json(config_path)
        self.pdu_manager = hako_pdu.HakoPduManager('/usr/local/lib/hakoniwa/hako_binary/offset', config_path)
        self.delta_time_usec = delta_time_usec
        self.slp_time_sec = float(delta_time_usec) / 1000000.0
        #ret = hakopy.asset_register(asset_name, config_path, my_callback, delta_time_usec, hakopy.HAKO_ASSET_MODEL_CONTROLLER)
        #if ret == False:
        #    print(f"ERROR: hako_asset_register() returns {ret}.")
        #    return None
        ret = hakopy.init_for_external()
        if ret == False:
            print(f"ERROR: init_for_external() returns {ret}.")
            return False
        self.pdu_buffers = {}
        self.lock = threading.Lock()

        self.pub_pdus = []
        for entry in self.config_json['robots']:
            for writer in entry['shm_pdu_writers']:
                info = HakoPduCommInfo(entry['name'], writer)
                self.pub_pdus.append(info)
            for reader in entry['shm_pdu_readers']:
                info = HakoPduCommInfo(entry['name'], reader)
                self.pub_pdus.append(info)        

    def _load_json(self, path):
        try:
            with open(path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"ERROR: File not found '{path}'")
        except json.JSONDecodeError:
            print(f"ERROR: Invalid Json fromat '{path}'")
        except PermissionError:
            print(f"ERROR: Permission denied '{path}'")
        except Exception as e:
            print(f"ERROR: {e}")
        return None

    def put_pdu_data(self, name: str, type_name: str, data):
        msg = {
            'name': name,
            'type': type_name,
            'data': data
        }
        with self.lock:
            self.pdu_buffers[name] = msg

    def get_pdu_data(self, name: str):
        with self.lock:
            if name in self.pdu_buffers:
                data = self.pdu_buffers[name]
                self.pdu_buffers[name] = None
                return data            
            else:
                return None

    #async def start_service(self):
    #    print("HakoPduService is starting...")
    #    ret = hakopy.start()
    #    print(f"INFO: hako_asset_start() returns {ret}")


def periodic_task():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    server_instance = HakoPduServer.get_instance()
    while True:
        loop.run_until_complete(on_simulation_step_async(None))
        time.sleep(server_instance.slp_time_sec)

def start_periodic_thread():
    # 新しいスレッドを作成し、定期的に非同期タスクを実行
    thread = threading.Thread(target=periodic_task)
    thread.start()

def run_hako_pdu_service(socket: HakoPduCommInterface, asset_name: str, config_path: str, delta_time_usec: int):
    service = HakoPduServer.get_instance(socket, asset_name, config_path, delta_time_usec)
    
    # 定期実行スレッドを開始
    start_periodic_thread()
    
    #asyncio.run(service.start_service())  # 非同期関数を実行
    return None