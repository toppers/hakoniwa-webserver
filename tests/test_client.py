import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:8765"  # サーバーのWebSocket URI
    async with websockets.connect(uri) as websocket:
        # サーバーにメッセージを送信
        await websocket.send("Hello, Server!")
        print("Sent: Hello, Server!")
        
        # サーバーからの応答を受信
        response = await websocket.recv()
        print(f"Received: {response}")

# イベントループを実行
asyncio.get_event_loop().run_until_complete(test_websocket())
