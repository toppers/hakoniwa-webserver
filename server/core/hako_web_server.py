import asyncio
import websockets
from server.core.hako_pdu_comm_interface import HakoPduCommInterface, HakoPduInfo

class HakoWebSocketServer(HakoPduCommInterface):
    _instance = None  # シングルトンインスタンス

    def __init__(self):
        if HakoWebSocketServer._instance is not None:
            raise Exception("This class is a singleton!")
        self.connections = []
        self.advertised_pdus = []
        HakoWebSocketServer._instance = self

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = HakoWebSocketServer()

            # 新しいイベントループを作成し、スレッドに設定
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return cls._instance

    async def handler(self, websocket, path):
        self.connections.append(websocket)
        try:
            async for message in websocket:
                print(f"Received message: {message}")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed: {e}")
        finally:
            self.connections.remove(websocket)

    async def broadcast(self, message):
        for conn in self.connections:
            await conn.send(message)

    async def send_to_clients(self, data):
        await self.broadcast(f"Server event: {data}")

    async def advertise_pdu(self, pdu_info: HakoPduInfo):
        self.advertised_pdus.append(pdu_info)
        print(f"Advertising PDU: {pdu_info.pdu_name} of type {pdu_info.pdu_type}")

    async def publish_pdu(self, pdu_info: HakoPduInfo, pdu_data_json: str):
        message_str = pdu_info.get_message_str(pdu_data_json)
        print(f"Broadcasting PDU: {message_str}")
        await self.broadcast(message_str)

    def run(self, host='localhost', port=8765):
        start_server = websockets.serve(self.handler, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")
        
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
