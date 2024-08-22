import asyncio
import websockets

class HakoWebSocketServer:
    def __init__(self):
        self.connections = []

    async def handler(self, websocket, path):
        self.connections.append(websocket)
        try:
            async for message in websocket:
                print(f"Received message: {message}")
                await self.broadcast(f"Echo: {message}")
        finally:
            self.connections.remove(websocket)

    async def broadcast(self, message):
        for conn in self.connections:
            await conn.send(message)

    async def send_to_clients(self, data):
        await self.broadcast(f"Server event: {data}")

    def run(self, host='localhost', port=8765):
        start_server = websockets.serve(self.handler, host, port)
        print(f"WebSocket server started on ws://{host}:{port}")
        
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()
