import asyncio
import hakopy
import hako_pdu
import threading
import json
import time
import os
import threading
import struct


from server.core.hako_pdu_comm_interface import HakoPduCommInterface
from server.core.data_packet import DataPacket

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

def my_on_simulation_step(context):
    return 0

# for debug
def decode_twist(pdu_data):
    """
    Decode binary data into Twist structure.
    Assumes 'linear' starts at byte offset 20 and is followed by 'angular'.
    """
    if len(pdu_data) < 48:  # Ensure enough bytes for linear (12 bytes) + angular (12 bytes)
        raise ValueError("PDU data size is too small to decode Twist structure")

    # Extract linear and angular components from the binary data
    linear = struct.unpack_from('<ddd', pdu_data, 24)  # 3 floats for linear (x, y, z)
    angular = struct.unpack_from('<ddd', pdu_data, 48)  # 3 floats for angular (x, y, z)

    return {"linear": {"x": linear[0], "y": linear[1], "z": linear[2]},
            "angular": {"x": angular[0], "y": angular[1], "z": angular[2]}}

async def on_simulation_step_async(context):
    #print("INFO: on_simulation_step_async")
    server_instance = HakoPduServer.get_instance()
    if server_instance is None:
        raise RuntimeError("HakoPduServer has not been initialized")

    for pdu_info in server_instance.pub_pdus:
        #print(f"pdu_data: start read {pdu_info.name} channel: {pdu_info.info['channel_id']} {pdu_info.info['pdu_size']}")
        pdu_data = hakopy.pdu_read(pdu_info.name, pdu_info.info['channel_id'], pdu_info.info['pdu_size'])
        if pdu_data is not None:
            #print(f"pdu_data: start publish: {pdu_info.name}")
            packet = DataPacket(pdu_info.name, pdu_info.info['channel_id'], pdu_data)
            await server_instance.socket.publish_pdu(packet)

    for pdu_info in server_instance.sub_pdus:
        packet = server_instance.get_packet(pdu_info.name, pdu_info.info['channel_id'])
        if packet is not None:
            pdu_data = packet.get_pdu_data()
            #print(f"pdu_data: start write {pdu_info.name} channel: {pdu_info.info['channel_id']} {pdu_info.info['pdu_size']}")
            #if pdu_info.info['channel_id'] == 0:
            #    print(f"pdu_data: write {pdu_info.name} channel: {pdu_info.info['channel_id']} {pdu_info.info['pdu_size']} {pdu_data}")
            ret = hakopy.pdu_write(pdu_info.name, pdu_info.info['channel_id'], pdu_data, pdu_info.info['pdu_size'])
            if ret == False:
                print(f"ERROR: can not write pdu data: robot_name={pdu_info.name} channel_id={pdu_info.info['channel_id']}")

    return 0

my_callback = {
    'on_initialize': my_on_initialize,
    'on_simulation_step': my_on_simulation_step,
    'on_manual_timing_control': None,
    'on_reset': my_on_reset
}

def hako_asset_runner():
    ret = hakopy.start()
    print(f"INFO: hako_asset_start() returns {ret}")

class HakoPduServer:
    _instance = None

    @classmethod
    def get_instance(cls, socket=None, asset_name=None, config_path=None, delta_time_usec=None, is_conductor=False):
        if cls._instance is None:
            if None in (socket, asset_name, config_path, delta_time_usec):
                raise ValueError("HakoPduServer instance not initialized. Missing arguments.")
            cls._instance = HakoPduServer(socket, asset_name, config_path, delta_time_usec, is_conductor)

        return cls._instance

    def __init__(self, socket: HakoPduCommInterface, asset_name: str, config_path: str, delta_time_usec, is_conductor=False):
        self.socket = socket
        self.config_json = self._load_json(config_path)
        self.delta_time_usec = delta_time_usec
        self.slp_time_sec = float(delta_time_usec) / 1000000.0
        socket.setBuffer(self.put_pdu_data)

        #ret = hakopy.init_for_external()
        ret = hakopy.asset_register(asset_name, config_path, my_callback, delta_time_usec, hakopy.HAKO_ASSET_MODEL_CONTROLLER)
        if ret == False:
            print(f"ERROR: init_for_external() returns {ret}.")
            return False
        self.pdu_buffers = {}
        self.lock = threading.Lock()

        self.pub_pdus = []
        self.sub_pdus = []
        for entry in self.config_json['robots']:
            for writer in entry['shm_pdu_writers']:
                print(f"pdu writer: {entry['name']}")
                info = HakoPduCommInfo(entry['name'], writer)
                self.sub_pdus.append(info)
                # for avatar publish
                self.pub_pdus.append(info)
                if is_conductor:
                    print(f"pdu create: {entry['name']} {writer['channel_id']} {writer['pdu_size']}")
                    hakopy.pdu_create(entry['name'], writer['channel_id'], writer['pdu_size'])
            for reader in entry['shm_pdu_readers']:
                info = HakoPduCommInfo(entry['name'], reader)
                print(f"pdu reader: {entry['name']}")
                self.pub_pdus.append(info)

        thread = threading.Thread(target=hako_asset_runner)
        thread.daemon = True
        thread.start()
        time.sleep(1)

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

    def put_pdu_data(self, packet: DataPacket):
        key = (packet.robot_name, packet.channel_id)
        #print(f"put_pdu_data: {packet.robot_name} {packet.channel_id}")
        with self.lock:
            self.pdu_buffers[key] = packet

    def get_packet(self, name: str, channel_id: int) -> DataPacket:
        key = (name, channel_id)
        with self.lock:
            if key in self.pdu_buffers:
                data = self.pdu_buffers[key]
                self.pdu_buffers[key] = None  # データのリセット
                return data
            else:
                return None

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

def run_hako_pdu_service(socket: HakoPduCommInterface, asset_name: str, config_path: str, delta_time_usec: int, is_conductor: bool):
    service = HakoPduServer.get_instance(socket, asset_name, config_path, delta_time_usec, is_conductor)
    
    # 定期実行スレッドを開始
    start_periodic_thread()
    
    #asyncio.run(service.start_service())  # 非同期関数を実行
    return None