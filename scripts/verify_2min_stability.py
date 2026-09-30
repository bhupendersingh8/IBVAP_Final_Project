import asyncio
import websockets
import json
import time
import urllib.request
import datetime

async def monitor_runtime():
    uri = "ws://127.0.0.1:8000/ws/alerts"
    print(f"[{datetime.datetime.now().isoformat()}] Starting 130-second continuous runtime verification...")
    
    start_time = time.time()
    duration = 130.0 # 2 minutes + 10s buffer
    
    ws_disconnect_count = 0
    webrtc_disconnect_count = 0
    telemetry_msgs = 0
    non_empty_telemetry = 0
    max_active_tracks = 0
    alerts_received = 0
    
    # Check initial DB incident count
    try:
        res = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/incidents").read()
        initial_incidents = len(json.loads(res.decode()))
    except Exception:
        initial_incidents = 0
    print(f"Initial DB incident count: {initial_incidents}")

    while time.time() - start_time < duration:
        try:
            async with websockets.connect(uri) as ws:
                print(f"[{datetime.datetime.now().isoformat()}] WebSocket CONNECTED to {uri}")
                while time.time() - start_time < duration:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        data = json.loads(raw)
                        msg_type = data.get("type")
                        
                        if msg_type == "telemetry":
                            telemetry_msgs += 1
                            tracks = data.get("tracks", [])
                            if len(tracks) > 0:
                                non_empty_telemetry += 1
                                if len(tracks) > max_active_tracks:
                                    max_active_tracks = len(tracks)
                        elif msg_type == "alert":
                            alerts_received += 1
                            print(f"[{datetime.datetime.now().isoformat()}] ALERT DETECTED: {data.get('explanation')} (Track #{data.get('track_id')})")
                    except asyncio.TimeoutError:
                        # Periodically probe WebRTC endpoint http://127.0.0.1:8889/CAM-01/
                        try:
                            probe = urllib.request.urlopen("http://127.0.0.1:8889/CAM-01/", timeout=2.0)
                            if probe.status != 200:
                                webrtc_disconnect_count += 1
                        except Exception:
                            webrtc_disconnect_count += 1
        except Exception as e:
            ws_disconnect_count += 1
            print(f"[{datetime.datetime.now().isoformat()}] WS disconnect / error: {e}, retrying...")
            await asyncio.sleep(1.0)
            
    end_time = time.time()
    
    # Check final DB incident count
    try:
        res = urllib.request.urlopen("http://127.0.0.1:8000/api/v1/incidents").read()
        final_incidents = len(json.loads(res.decode()))
    except Exception:
        final_incidents = 0

    print("\n================== 2-MINUTE RUNTIME METRICS ==================")
    print(f"browser video start time: {datetime.datetime.fromtimestamp(start_time).isoformat()}")
    print(f"browser video end time:   {datetime.datetime.fromtimestamp(end_time).isoformat()}")
    print(f"WebRTC disconnect count:  {webrtc_disconnect_count}")
    print(f"WebSocket disconnect count: {ws_disconnect_count}")
    print(f"telemetry messages received: {telemetry_msgs}")
    print(f"non-empty telemetry messages: {non_empty_telemetry}")
    print(f"maximum active tracks: {max_active_tracks}")
    print(f"alerts generated: {alerts_received}")
    print(f"incidents created: {final_incidents - initial_incidents} (Total in DB: {final_incidents})")
    print("==============================================================")

if __name__ == "__main__":
    asyncio.run(monitor_runtime())
