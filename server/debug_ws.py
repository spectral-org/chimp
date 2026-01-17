
import asyncio
import websockets

async def test_connection():
    uri = "ws://127.0.0.1:8000/ws/simulation"
    print(f"Attempting to connect to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Successfully connected!")
            await websocket.send('{"type": "ping"}')
            print("Sent ping")
            # Wait a bit
            await asyncio.sleep(1)
            print("Closing...")
    except Exception as e:
        print(f"Connection failed: {e}")

asyncio.run(test_connection())
