import asyncio
import websockets
import struct
import asyncio
from typing import Optional
from server.core.data_packet import DataPacket
from server.core.hako_pdu_comm_interface import HakoPduCommInterface

class HakoPduConnection:
    def __init__(self, websocket: websockets.WebSocketServerProtocol) -> None:
        self.websocket: websockets.WebSocketServerProtocol = websocket
        self.lists: list[tuple[str, int]] = []

    def add(self, robot_name: str, channel_id: int) -> None:
        if not self.is_exist(robot_name, channel_id):
            self.lists.append((robot_name, channel_id))
    
    def is_exist(self, robot_name: str, channel_id: int) -> bool:
        return (robot_name, channel_id) in self.lists


class HakoPduConnectionContainer:
    def __init__(self):
        self.connections: dict[websockets.WebSocketServerProtocol, HakoPduConnection] = {}
        self.lock = asyncio.Lock()

    async def add(self, websocket: websockets.WebSocketServerProtocol) -> None:
        async with self.lock:
            if websocket not in self.connections:
                self.connections[websocket] = HakoPduConnection(websocket)

    async def get(self, websocket: websockets.WebSocketServerProtocol) -> Optional[HakoPduConnection]:
        async with self.lock:
            return self.connections.get(websocket, None)

    async def remove(self, websocket: websockets.WebSocketServerProtocol) -> None:
        async with self.lock:
            if websocket in self.connections:
                del self.connections[websocket]

class HakoPduCommWebSocketImpl(HakoPduCommInterface):
    _instance = None

    def __init__(self):
        if HakoPduCommWebSocketImpl._instance is not None:
            raise Exception("This class is a singleton!")
        self.connection_container = HakoPduConnectionContainer()
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
        print(f"New connection established: {websocket.remote_address}")
        await self.connection_container.add(websocket) 
        try:
            async for message in websocket:
                #print(f"Received message {message}")
                packet = DataPacket.decode(message)
                # Declare 系のメッセージかどうかをチェックしてログを表示
                if packet.is_declare_pdu_for_read():
                    print(f"DeclarePduForRead received from {packet.get_robot_name()}/{packet.get_channel_id()}")
                    connection = await self.connection_container.get(websocket)
                    connection.add(packet.get_robot_name(), packet.get_channel_id())
                elif packet.is_declare_pdu_for_write():
                    print(f"DeclarePduForWrite received from {packet.get_robot_name()}/{packet.get_channel_id()}")
                else:
                    #print(f"Normal packet received from {packet.get_robot_name()}")                 
                    self.buffer_callback(packet)
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"Connection closed with code {e.code}: {e.reason}")
        finally:
            await self.unregister_connection(websocket)

    async def unregister_connection(self, websocket):
        """コネクションを安全に削除"""
        print(f"Connection unregistered: {websocket.remote_address}")
        await self.connection_container.remove(websocket)

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
        connections_snapshot = list(self.connection_container.connections.values())
        for conn in connections_snapshot:
            if conn.is_exist(target_robot, target_channel_id):
                try:
                    await conn.websocket.send(packet.encode())
                    #print(f"Sent packet to {target_robot}/{target_channel_id}")
                except websockets.exceptions.ConnectionClosedError:
                    print(f"Connection closed: {conn.websocket.remote_address}")
                    self.unregister_connection(conn.websocket)
                except Exception as e:
                    print(f"Error sending packet to {target_robot}/{target_channel_id}: {e}")
                    self.unregister_connection(conn.websocket)

    def run(self, host='localhost', port=8765):
        print(f'run webserver')
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            print(f'set event loop on asyncio')

            async def start_server():
                print(f"Starting WebSocket server...")
                server = await websockets.serve(self.handler, host, port)
                print(f"WebSocket server started on ws://{host}:{port}")
                return server

            # イベントループで非同期タスクとしてサーバーを起動
            server = loop.run_until_complete(start_server())
            loop.run_forever()
        except Exception as e:
            print(f"WebSocket server encountered an error: {e}")
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

