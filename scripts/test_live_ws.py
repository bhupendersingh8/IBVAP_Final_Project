import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://127.0.0.1:8000/ws/alerts"
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected successfully to WebSocket!")
            for i in range(3):
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                msg_type = data.get("type", "unknown")
                keys = list(data.keys())[:6]
                print(f"Message {i+1} received! Type: {msg_type}, Keys: {keys}")
                if "detections" in data:
                    print(f"  Detections: {len(data['detections'])}")
                if "tracks" in data:
                    print(f"  Tracks: {len(data['tracks'])}")
                if "incident" in data:
                    print(f"  Incident: {data['incident'].get('title')}")
    except Exception as e:
        print(f"WebSocket test exception: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
