import asyncio
import hakopy
import threading
import queue
import json
import time
import os
import threading
import struct
from typing import Optional


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

    while not server_instance.on_demand_requests.empty():
        websocket, name, channel_id = server_instance.on_demand_requests.get()
        pdu_data = server_instance.read_pdu(name, channel_id)
        if pdu_data is not None:
            packet = DataPacket(name, channel_id, pdu_data)
            server_instance.socket.send_packet_threadsafe(websocket, packet)
            print(f"INFO: on_demand_requests: sent {name} channel_id={channel_id} data size={len(pdu_data)}")

    for pdu_info in server_instance.pub_pdus:
        if server_instance.socket.is_exist_subscriber(pdu_info.name, pdu_info.info['channel_id']) == False:
            continue
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
            #if pdu_info.info['channel_id'] == 1:
            #    twist = decode_twist(pdu_data)
            #    print(f"twist: {twist}")
            #    print(f"pdu_data: write {pdu_info.name} channel: {pdu_info.info['channel_id']} {pdu_info.info['pdu_size']} {pdu_data}")

            pdu_data_len = len(pdu_data)
            # pdu_data size check
            # if len(pdu_data) > pdu_info.info['pdu_size']:
            #   pdu_data_len = pdu_info.info['pdu_size'] with warning
            # if len(pdu_data) < pdu_info.info['pdu_size']:
            #   good to write with no warning
            if pdu_data_len > pdu_info.info['pdu_size']:
                print(f"WARNING: pdu_data size mismatch: {pdu_info.name} channel_id={pdu_info.info['channel_id']} "
                      f"expected={pdu_info.info['pdu_size']} actual={pdu_data_len}")
                pdu_data = pdu_data[:pdu_info.info['pdu_size']]
                pdu_data_len = pdu_info.info['pdu_size']
            #print(f"pdu_data: write {pdu_info.name} channel: {pdu_info.info['channel_id']} {pdu_info.info['pdu_size']} {pdu_data}")
            ret = hakopy.pdu_write(pdu_info.name, pdu_info.info['channel_id'], pdu_data, pdu_data_len)
            if ret == False:
                print(f"ERROR: can not write pdu data: robot_name={pdu_info.name} channel_id={pdu_info.info['channel_id']}")

    return 0

my_callback = {
    'on_initialize': my_on_initialize,
    'on_simulation_step': my_on_simulation_step,
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
        self.delta_time_usec = delta_time_usec
        self.slp_time_sec = float(delta_time_usec) / 1000000.0
        socket.setBuffer(self.put_pdu_data)

        ret = hakopy.init_for_external()
        #ret = hakopy.asset_register(asset_name, config_path, my_callback, delta_time_usec, hakopy.HAKO_ASSET_MODEL_CONTROLLER)
        if ret == False:
            print(f"ERROR: init_for_external() returns {ret}.")
            return False
        self.pdu_buffers = {}
        self.lock = threading.Lock()
        self.on_demand_requests = queue.Queue()

        self.pub_pdus = []
        self.sub_pdus = []
        for entry in self.config_json['robots']:
            for writer in entry['shm_pdu_writers']:
                info = HakoPduCommInfo(entry['name'], writer)
                self.append_list('pub_pdus', self.pub_pdus, entry['name'], info)
            for reader in entry['shm_pdu_readers']:
                info = HakoPduCommInfo(entry['name'], reader)
                self.append_list('sub_pdus', self.sub_pdus, entry['name'], info)
                #add pub list for avatar read of quest3
                self.append_list('pub_pdus', self.pub_pdus, entry['name'], info)

        time.sleep(1)

    def append_list(self, list_name, target_list, robot_name, new_info: HakoPduCommInfo):
        for entry in target_list:
            if entry.name == new_info.name and entry.info['channel_id'] == new_info.info['channel_id']:
                return
        print(f'append_list({list_name}) : {new_info.name} {new_info.info["channel_id"]} {new_info.info["org_name"]}')
        target_list.append(new_info)
        #hakopy.pdu_create(robot_name, new_info.info['channel_id'], new_info.info['pdu_size'])
        print(f"pdu create: {robot_name} {new_info.info['channel_id']} {new_info.info['pdu_size']}")

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

    def get_pdu_size(self, name: str, channel_id: int) -> Optional[int]:
        for entry in self.pub_pdus:
            if entry.name == name and entry.info['channel_id'] == channel_id:
                return entry.info['pdu_size']
        for entry in self.sub_pdus:
            if entry.name == name and entry.info['channel_id'] == channel_id:
                return entry.info['pdu_size']
        return None

    def read_pdu(self, name: str, channel_id: int) -> Optional[bytes]:
        size = self.get_pdu_size(name, channel_id)
        if size is None:
            return None
        return hakopy.pdu_read(name, channel_id, size)

    def enqueue_on_demand_request(self, request):
        self.on_demand_requests.put(request)

def periodic_task():
    server_instance = HakoPduServer.get_instance()
    loop = server_instance.socket.loop  # WebSocket 側の loop を取得

    #input("ENTER for start...")

    async def periodic_loop():
        while True:
            start_time = time.perf_counter() #sec/float
            await on_simulation_step_async(None)
            end_time = time.perf_counter()

            elapsed_time_msec = (end_time - start_time) * 1000
            sleep_time = (server_instance.delta_time_usec / 1000 - elapsed_time_msec) / 1000
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            else:
                #pass
                print(f"WARNING: on_simulation_step_async() took too long: {elapsed_time_msec:.2f} ms")

    # WebSocket のループにタスクとして登録（安全に）
    loop.call_soon_threadsafe(lambda: asyncio.create_task(periodic_loop()))

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