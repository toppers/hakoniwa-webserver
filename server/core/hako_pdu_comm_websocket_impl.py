import asyncio
import websockets
import struct
from server.core.data_packet import DataPacket
from server.core.hako_pdu_comm_interface import HakoPduCommInterface

class HakoPduCommWebSocketImpl(HakoPduCommInterface):
    _instance = None

    def __init__(self):
        if HakoPduCommWebSocketImpl._instance is not None:
            raise Exception("This class is a singleton!")
        #self.connections = []
        self.connections = {}  # コネクションとPDU情報のマッピング {websocket: (robot_name, channel_id)}
        self.advertised_pdus = []
        HakoPduCommWebSocketImpl._instance = self
        self.buffer_callback = None

    def setBuffer(self, buffer_callback):
        self.buffer_callback = buffer_callback

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = HakoPduCommWebSocketImpl()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return cls._instance

    async def handler(self, websocket, path):
        #self.connections.append(websocket)
        print(f"New connection established: {websocket.remote_address}")
        try:
            async for message in websocket:
                #print(f"Received message {message}")
                packet = DataPacket.decode(message)
                # Declare 系のメッセージかどうかをチェックしてログを表示
                if packet.is_declare_pdu_for_read():
                    print(f"DeclarePduForRead received from {packet.get_robot_name()}/{packet.get_channel_id()}")
                    self.connections[websocket] = (packet.get_robot_name(), packet.get_channel_id())
                elif packet.is_declare_pdu_for_write():
                    print(f"DeclarePduForWrite received from {packet.get_robot_name()}/{packet.get_channel_id()}")
                else:
                    #print(f"Normal packet received from {packet.get_robot_name()}")                 
                    self.buffer_callback(packet)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with code {e.code}: {e.reason}")
        finally:
            self.unregister_connection(websocket)

    def unregister_connection(self, websocket):
        """コネクションを安全に削除"""
        if websocket in self.connections:
            del self.connections[websocket]
            print(f"Connection unregistered: {websocket.remote_address}")

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

    async def publish_pdu(self, packet: DataPacket):
        """特定のPDU情報を持つクライアントにのみデータを送信"""
        target_robot = packet.get_robot_name()
        target_channel_id = packet.get_channel_id()

        # 適切な接続を検索
        for conn, (robot_name, channel_id) in self.connections.items():
            if robot_name == target_robot and channel_id == target_channel_id:
                try:
                    await conn.send(packet.encode())
                    #print(f"Sent packet to {robot_name}/{channel_id}")
                except Exception as e:
                    print(f"Error sending packet to {robot_name}/{channel_id}: {e}")
                    self.unregister_connection(conn)  # クリーンアップ

    def run(self, host='localhost', port=8765):
        loop = asyncio.new_event_loop()  # 新しいイベントループを作成
        asyncio.set_event_loop(loop)  # 新しいイベントループをこのスレッドに設定

        start_server = websockets.serve(self.handler, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")

        loop.run_until_complete(start_server)
        loop.run_forever()
