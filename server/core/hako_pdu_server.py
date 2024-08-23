import asyncio
import time
from server.core.hako_pdu_comm_interface import HakoPduCommInterface, HakoPduInfo

class HakoPduServer:
    def __init__(self, socket: HakoPduCommInterface):
        self.socket = socket

    async def start_service(self):
        print("HakoPduService is starting...")
        while True:
            pdu_info = HakoPduInfo(pdu_type="example_type", pdu_name="example_name")
            pdu_data_json = '{"key": "value"}'
            await self.socket.publish_pdu(pdu_info, pdu_data_json)  # awaitを追加
            await asyncio.sleep(5)  # asyncio.sleepを使って非同期に5秒待機

def run_hako_pdu_service(socket: HakoPduCommInterface):
    service = HakoPduServer(socket)
    asyncio.run(service.start_service())  # asyncio.runで非同期関数を実行
