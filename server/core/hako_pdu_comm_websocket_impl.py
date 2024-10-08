import asyncio
import websockets
import struct
from server.core.hako_pdu_comm_interface import HakoPduCommInterface, HakoPduInfo

class HakoPduCommWebSocketImpl(HakoPduCommInterface):
    _instance = None

    def __init__(self):
        if HakoPduCommWebSocketImpl._instance is not None:
            raise Exception("This class is a singleton!")
        self.connections = []
        self.advertised_pdus = []
        HakoPduCommWebSocketImpl._instance = self

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = HakoPduCommWebSocketImpl()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return cls._instance

    async def handler(self, websocket, path):
        self.connections.append(websocket)
        try:
            async for message in websocket:
                print(f"Received message: {message}")
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with code {e.code}: {e.reason}")
        finally:
            self.connections.remove(websocket)

    async def send_message(self, conn, message):
        # メッセージをバイト列に変換
        encoded_message = message.encode('utf-8')
        
        # メッセージの長さを8バイトのバイナリに変換
        message_length = struct.pack('<Q', len(encoded_message))
        #print(f"Sending length: {len(encoded_message)}, binary: {message_length.hex()}")
        # 先にサイズを送信し、その後にメッセージ本体を送信
        await conn.send(message_length)
        await conn.send(encoded_message)

    async def broadcast(self, message):
        if not self.connections:
            #print("No active WebSocket connections to broadcast to.")
            return
        
        for conn in self.connections:
            try:
                #print(f"Sending message to connection: {conn}")
                await self.send_message(conn, message)
                #print("Message sent successfully.")
            except Exception as e:
                print(f"Error sending message: {e}")


    async def send_to_clients(self, data):
        await self.broadcast(f"Server event: {data}")

    async def advertise_pdu(self, pdu_info: HakoPduInfo):
        self.advertised_pdus.append(pdu_info)
        print(f"Advertising PDU: {pdu_info.pdu_name} of type {pdu_info.pdu_type}")

    async def publish_pdu(self, pdu_info: HakoPduInfo, pdu_data_json: str):
        message_str = pdu_info.get_message_str(pdu_data_json)
        #print(f"Broadcasting PDU: {message_str}")
        await self.broadcast(message_str)
        #print("PDU broadcast complete.")

    def run(self, host='localhost', port=8765):
        loop = asyncio.new_event_loop()  # 新しいイベントループを作成
        asyncio.set_event_loop(loop)  # 新しいイベントループをこのスレッドに設定

        start_server = websockets.serve(self.handler, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")

        loop.run_until_complete(start_server)
        loop.run_forever()
