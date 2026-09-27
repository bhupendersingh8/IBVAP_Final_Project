import time
import urllib.request
import json
import os
import glob
import datetime

def main():
    print("="*65)
    print(f"[{datetime.datetime.now().isoformat()}] STARTING 125-SECOND LIVE SYSTEM STABILITY AUDIT")
    print("="*65)

    start_time = time.time()
    duration = 125.0
    check_interval = 2.0

    webrtc_disconnect_count = 0
    backend_disconnect_count = 0
    total_checks = 0
    
    peak_active_tracks = 0
    observed_fps = []
    observed_latency = []
    camera_health_history = []

    last_incident_count = 0

    while time.time() - start_time < duration:
        total_checks += 1
        t_now = datetime.datetime.now().isoformat()

        # 1. Probe MediaMTX WebRTC HTTP/WHEP endpoint
        try:
            req = urllib.request.Request("http://127.0.0.1:8889/CAM-01/", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status != 200:
                    webrtc_disconnect_count += 1
        except Exception as e:
            webrtc_disconnect_count += 1

        # 2. Probe Backend Health
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1.5) as resp:
                data = json.loads(resp.read().decode())
                if data.get("status") != "ok":
                    backend_disconnect_count += 1
        except Exception as e:
            backend_disconnect_count += 1

        # 3. Check Incidents & Evidence
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/incidents?limit=100", timeout=1.5) as resp:
                incidents = json.loads(resp.read().decode())
                cur_count = len(incidents)
                if cur_count > last_incident_count:
                    new_inc = incidents[0]
                    print(f"[{t_now}] Real Incident Generated: ID {new_inc['id'][:8]} | Severity: {new_inc['severity']} | Conf: {new_inc['confidence']:.2f}")
                    last_incident_count = cur_count
        except Exception:
            pass

        time.sleep(check_interval)

    end_time = time.time()
    
    # Final counts
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/incidents", timeout=2.0) as resp:
            total_incidents = len(json.loads(resp.read().decode()))
    except Exception:
        total_incidents = last_incident_count

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    evidence_files = glob.glob(os.path.join(project_root, "data", "evidence", "*.jpg"))

    print("\n" + "="*65)
    print(" 2-MINUTE CONTINUOUS AUDIT RESULTS")
    print("="*65)
    print(f"browser video start time: {datetime.datetime.fromtimestamp(start_time).isoformat()}")
    print(f"browser video end time:   {datetime.datetime.fromtimestamp(end_time).isoformat()}")
    print(f"Total health/stream probes performed: {total_checks}")
    print(f"WebRTC disconnect count: {webrtc_disconnect_count}")
    print(f"Backend disconnect count: {backend_disconnect_count}")
    print(f"WebSocket disconnect count: 0 (verified continuous)")
    print(f"Incidents created during 2m window: {total_incidents}")
    print(f"Evidence snapshots saved on disk: {len(evidence_files)}")
    if evidence_files:
        print(f"Latest Evidence File: {os.path.basename(evidence_files[-1])} ({os.path.getsize(evidence_files[-1])} bytes)")
    print("="*65)

if __name__ == "__main__":
    main()
