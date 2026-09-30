import time
from datetime import datetime, timezone

from services.ingestion.mock_source import MockSource
from services.detection.mock_detector import MockDetector
from services.tracking.bytetrack_adapter import FallbackIoUTracker
from services.rules.rule_engine import RuleEngine
from services.rules.schemas import Zone, ZoneType, Point

def run_benchmark(duration_seconds=5):
    print("====================================")
    print(" IBVAP AI Engine Benchmark")
    print("====================================\n")
    
    # 1. Initialize Components
    print("Initializing Mock Camera, Detector, Tracker, and Rule Engine...")
    camera = MockSource(camera_id="CAM-BENCH", fps=30)
    detector = MockDetector({"latency_ms": 15.0})  # Simulate 15ms inference time
    detector.load_model()
    tracker = FallbackIoUTracker()
    
    # Create a dummy zone in the center of the frame
    zone = Zone(
        zone_id="Z1", name="Restricted Center", camera_id="CAM-BENCH",
        zone_type=ZoneType.RESTRICTED_ZONE,
        points=[Point(0.25, 0.25), Point(0.75, 0.25), Point(0.75, 0.75), Point(0.25, 0.75)]
    )
    rule_engine = RuleEngine(zones=[zone])
    
    # 2. Start Camera
    camera.start()
    time.sleep(1.0) # Wait for buffer to fill
    
    print(f"\nStarting processing loop for {duration_seconds} seconds...")
    frames_processed = 0
    total_latency_ms = 0
    events_generated = 0
    
    start_time = time.time()
    
    while time.time() - start_time < duration_seconds:
        frame = camera.get_latest_frame()
        if not frame:
            time.sleep(0.01)
            continue
            
        loop_start = time.time()
        
        # Pipeline execution
        det_batch = detector.detect_from_camera_frame(frame)
        track_result = tracker.update(det_batch)
        events = rule_engine.evaluate(track_result)
        
        latency = (time.time() - loop_start) * 1000
        total_latency_ms += latency
        frames_processed += 1
        events_generated += len(events)
        
    camera.stop()
    
    # 3. Report Results
    avg_latency = total_latency_ms / frames_processed if frames_processed > 0 else 0
    actual_fps = frames_processed / duration_seconds
    
    print("\n====================================")
    print(" BENCHMARK RESULTS")
    print("====================================")
    print(f"Total time elapsed  : {duration_seconds:.1f} seconds")
    print(f"Frames processed    : {frames_processed}")
    print(f"Average FPS         : {actual_fps:.1f} FPS")
    print(f"Avg Pipeline Latency: {avg_latency:.1f} ms/frame")
    print(f"Spatial Events Found: {events_generated}")
    print("====================================")
    print("\n(Note: This uses mock inference to test pipeline throughput limits without a GPU)")

if __name__ == "__main__":
    run_benchmark()
