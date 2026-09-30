"""
Unit & Integration Tests for IBVAP Unified Ingestion Sources Pipeline
=====================================================================
Validates Section 3 & 4 Architecture Requirements:
1. Unified Pipeline Contract across all 4 sources:
   WEBCAM, VIDEO_FILE, RTSP, MEDIAMTX -> SourceAdapter -> FramePacket -> SharedPreprocessor -> AutonomousAIOrchestrator
2. FramePacket Integrity:
   Preservation of camera_id, timestamp, iso_timestamp, raw_bgr, gpu_tensor,
   and 5 isolated metadata bags (preprocessing, camera, inference, tracking, evidence).
3. Stale Frame Dropping Policy:
   - Frame age calculation and staleness threshold checks
   - Bounded queue buffer dropping under backpressure
   - get_latest_packet() real-time draining
4. Latency Telemetry:
   - Capture latency tracking
   - Preprocessing and multi-tier cascading inference latency
   - Measured FPS calculation
5. Backward Compatibility:
   - get_frame() and get_latest_frame() returning legacy CameraFrame
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Generator

import cv2
import numpy as np
import pytest

# Ensure IBVAP root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.ingestion.frame_packet import FramePacket, SourceType
from services.ingestion.source_adapters import (
    BaseSourceAdapter,
    WebcamAdapter,
    VideoFileAdapter,
    RTSPAdapter,
    MediaMTXAdapter,
    SourceAdapterFactory,
)
from services.ingestion.camera_source import CameraHealth, CameraStats
from services.ingestion.frame_buffer import CameraFrame
from services.preprocessing.shared_preprocessor import SharedPreprocessor
from services.orchestrator.orchestrator import AutonomousAIOrchestrator
from services.orchestrator.cascade_levels import CascadedInferenceResult, CascadeStatus
from services.detection.mock_detector import MockDetector


# ==============================================================================
# FIXTURES & HELPERS
# ==============================================================================

@pytest.fixture
def synthetic_frame() -> np.ndarray:
    """Creates a deterministic synthetic BGR frame (480x640x3)."""
    frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Add synthetic target shape (person-like rectangle)
    cv2.rectangle(frame, (200, 100), (320, 380), (30, 40, 180), -1)
    return frame


@pytest.fixture
def temp_video_file(tmp_path: Path) -> Generator[str, None, None]:
    """Generates a temporary 10-frame synthetic MP4 video file."""
    video_path = str(tmp_path / "synthetic_test_video.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480))
    for i in range(10):
        frame = np.full((480, 640, 3), 100 + i * 5, dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(frame)
    writer.release()
    yield video_path
    if os.path.exists(video_path):
        os.remove(video_path)


@pytest.fixture
def orchestrator() -> AutonomousAIOrchestrator:
    """Initializes AutonomousAIOrchestrator with mock primary detector."""
    mock = MockDetector()
    mock.load_model()
    return AutonomousAIOrchestrator(primary_detector=mock)


@pytest.fixture
def preprocessor() -> SharedPreprocessor:
    """Initializes SharedPreprocessor."""
    return SharedPreprocessor(target_size=(640, 640))


# ==============================================================================
# TEST SUITE
# ==============================================================================

class TestSourceAdapterFactory:
    """Tests factory instantiation and URI auto-detection for all 4 sources."""

    def test_factory_explicit_source_types(self, temp_video_file: str):
        """Verify SourceAdapterFactory correctly instantiates all 4 types explicitly."""
        # 1. WEBCAM
        cam_adapter = SourceAdapterFactory.create_adapter(
            camera_id="CAM-WEBCAM", source_uri=0, source_type=SourceType.WEBCAM
        )
        assert isinstance(cam_adapter, WebcamAdapter)
        assert cam_adapter.source_type == SourceType.WEBCAM
        assert cam_adapter.camera_id == "CAM-WEBCAM"

        # 2. VIDEO_FILE
        vid_adapter = SourceAdapterFactory.create_adapter(
            camera_id="CAM-VID", source_uri=temp_video_file, source_type=SourceType.VIDEO_FILE
        )
        assert isinstance(vid_adapter, VideoFileAdapter)
        assert vid_adapter.source_type == SourceType.VIDEO_FILE
        assert vid_adapter.file_path == temp_video_file

        # 3. RTSP
        rtsp_adapter = SourceAdapterFactory.create_adapter(
            camera_id="CAM-RTSP", source_uri="rtsp://192.168.1.100:554/live", source_type=SourceType.RTSP
        )
        assert isinstance(rtsp_adapter, RTSPAdapter)
        assert rtsp_adapter.source_type == SourceType.RTSP
        assert rtsp_adapter.rtsp_url == "rtsp://192.168.1.100:554/live"

        # 4. MEDIAMTX
        mtx_adapter = SourceAdapterFactory.create_adapter(
            camera_id="CAM-MTX", source_uri="rtsp://127.0.0.1:8554/live", source_type=SourceType.MEDIAMTX
        )
        assert isinstance(mtx_adapter, MediaMTXAdapter)
        assert mtx_adapter.source_type == SourceType.MEDIAMTX

    def test_factory_uri_auto_detection(self, temp_video_file: str):
        """Verify SourceAdapterFactory correctly infers source type from URI pattern."""
        # Integer or webcam string
        a1 = SourceAdapterFactory.create_adapter("C1", "0")
        assert isinstance(a1, WebcamAdapter)
        assert a1.source_type == SourceType.WEBCAM

        # Video file path (.mp4)
        a2 = SourceAdapterFactory.create_adapter("C2", temp_video_file)
        assert isinstance(a2, VideoFileAdapter)
        assert a2.source_type == SourceType.VIDEO_FILE

        # MediaMTX localhost RTSP
        a3 = SourceAdapterFactory.create_adapter("C3", "rtsp://127.0.0.1:8554/stream01")
        assert isinstance(a3, MediaMTXAdapter)
        assert a3.source_type == SourceType.MEDIAMTX

        # Remote network RTSP
        a4 = SourceAdapterFactory.create_adapter("C4", "rtsp://admin:pass@10.0.0.5:554/ch0")
        assert isinstance(a4, RTSPAdapter)
        assert a4.source_type == SourceType.RTSP


class TestUnifiedSourcesPipelineContract:
    """
    Verifies all 4 ingestion sources enter the exact same pipeline contract:
    SourceAdapter -> FramePacket -> SharedPreprocessor -> AutonomousAIOrchestrator
    """

    @pytest.mark.parametrize(
        "source_type,adapter_cls,uri_or_param",
        [
            (SourceType.WEBCAM, WebcamAdapter, 0),
            (SourceType.VIDEO_FILE, VideoFileAdapter, "dummy.mp4"),
            (SourceType.RTSP, RTSPAdapter, "rtsp://192.168.1.50:554/stream"),
            (SourceType.MEDIAMTX, MediaMTXAdapter, "rtsp://127.0.0.1:8554/stream"),
        ],
    )
    def test_four_sources_enter_same_pipeline_contract(
        self,
        source_type: SourceType,
        adapter_cls: type,
        uri_or_param: Any,
        synthetic_frame: np.ndarray,
        preprocessor: SharedPreprocessor,
        orchestrator: AutonomousAIOrchestrator,
    ):
        """
        Tests that all 4 sources output a canonical FramePacket that seamlessly passes through
        SharedPreprocessor and AutonomousAIOrchestrator, enriching all metadata bags.
        """
        cam_id = f"TEST-{source_type.value}"

        # 1. Initialize Adapter
        if source_type == SourceType.WEBCAM:
            adapter = WebcamAdapter(camera_id=cam_id, device_index=0)
        elif source_type == SourceType.VIDEO_FILE:
            adapter = VideoFileAdapter(camera_id=cam_id, file_path=str(uri_or_param), loop=False)
        elif source_type == SourceType.RTSP:
            adapter = RTSPAdapter(camera_id=cam_id, rtsp_url=str(uri_or_param))
        else:  # MEDIAMTX
            adapter = MediaMTXAdapter(camera_id=cam_id, mediamtx_rtsp_url=str(uri_or_param))

        assert adapter.source_type == source_type
        assert isinstance(adapter, BaseSourceAdapter)

        # 2. Simulate Ingestion emitting a canonical FramePacket
        now_epoch = time.time()
        packet = FramePacket(
            camera_id=cam_id,
            frame_id=101,
            source_type=source_type,
            timestamp=now_epoch,
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
            fps=30.0,
            camera_metadata={"origin": source_type.value, "uri": str(uri_or_param)},
        )

        # Push packet into adapter and retrieve it to verify adapter queue contract
        adapter._push_packet(packet)
        retrieved_packet = adapter.get_next_packet()

        assert retrieved_packet is not None
        assert retrieved_packet.camera_id == cam_id
        assert retrieved_packet.source_type == source_type
        assert retrieved_packet.raw_bgr is not None
        assert retrieved_packet.gpu_tensor is None  # Not yet preprocessed

        # 3. Step 2 in Contract: SharedPreprocessor
        preprocessed_packet = preprocessor.preprocess(retrieved_packet)
        assert preprocessed_packet is retrieved_packet
        assert preprocessed_packet.gpu_tensor is not None
        assert "target_size" in preprocessed_packet.preprocessing_metadata
        assert "ratio" in preprocessed_packet.preprocessing_metadata
        assert preprocessed_packet.preprocessing_metadata["original_shape"] == (480, 640)

        # 4. Step 3 in Contract: AutonomousAIOrchestrator
        result = orchestrator.process_packet(
            preprocessed_packet,
            zone_name="PERIMETER_NORTH",
            zone_hazard_score=0.90,
            simulate_established_tracks=True,
        )

        # 5. Contract Output Invariants
        assert isinstance(result, CascadedInferenceResult)
        assert result.camera_id == cam_id
        assert len(result.levels_executed) == 7
        assert result.overall_status in (CascadeStatus.ALERT_TRIGGERED, CascadeStatus.PASS)

        # 6. Metadata Bag Population Verification
        assert preprocessed_packet.camera_metadata["origin"] == source_type.value
        assert "detections_count" in preprocessed_packet.inference_metadata
        assert "overall_status" in preprocessed_packet.inference_metadata
        assert "total_latency_ms" in preprocessed_packet.inference_metadata
        assert "route_score" in preprocessed_packet.inference_metadata
        assert "action_directive" in preprocessed_packet.inference_metadata

        assert "active_tracks_count" in preprocessed_packet.tracking_metadata
        assert "fused_events_count" in preprocessed_packet.tracking_metadata

        assert "incidents" in preprocessed_packet.evidence_metadata
        assert "sha256_hash" in preprocessed_packet.evidence_metadata
        assert "indic_dispatch" in preprocessed_packet.evidence_metadata

    def test_real_video_file_adapter_packet_stream(
        self,
        temp_video_file: str,
        preprocessor: SharedPreprocessor,
        orchestrator: AutonomousAIOrchestrator,
    ):
        """Test VideoFileAdapter end-to-end reading real synthetic video frames."""
        adapter = VideoFileAdapter(
            camera_id="CAM-FILE-01",
            file_path=temp_video_file,
            loop=False,
            config={"buffer_size": 15, "fps_limit": 60},
        )
        adapter.start()
        time.sleep(0.15)  # Wait for reader thread to push frames

        try:
            assert adapter.is_alive() is True
            packet = adapter.get_next_packet()
            assert packet is not None
            assert packet.source_type == SourceType.VIDEO_FILE
            assert packet.camera_id == "CAM-FILE-01"
            assert packet.frame_id >= 1
            assert packet.raw_bgr.shape == (480, 640, 3)

            # Pass through preprocessor and orchestrator
            preprocessor.preprocess(packet)
            result = orchestrator.process_packet(packet)
            assert isinstance(result, CascadedInferenceResult)
            assert result.raw_detections_count >= 0
        finally:
            adapter.stop()
            assert adapter.is_alive() is False


class TestFramePacketIntegrity:
    """Verifies FramePacket retention, immutability contracts, and serialization."""

    def test_frame_packet_fields_retention(self, synthetic_frame: np.ndarray):
        """Verifies FramePacket retains all required core fields and metadata bags."""
        t_epoch = 1700000000.5
        packet = FramePacket(
            camera_id="CAM-ALPHA",
            frame_id=42,
            source_type=SourceType.WEBCAM,
            timestamp=t_epoch,
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
            fps=25.0,
            camera_metadata={"lens": "wide", "exposure": 120},
        )

        assert packet.camera_id == "CAM-ALPHA"
        assert packet.frame_id == 42
        assert packet.source_type == SourceType.WEBCAM
        assert packet.timestamp == t_epoch
        assert packet.raw_bgr is synthetic_frame
        assert packet.width == 640
        assert packet.height == 480
        assert packet.fps == 25.0
        assert packet.gpu_tensor is None

        # Verify all 5 metadata bags exist and are isolated dictionaries
        assert isinstance(packet.preprocessing_metadata, dict)
        assert isinstance(packet.camera_metadata, dict)
        assert isinstance(packet.inference_metadata, dict)
        assert isinstance(packet.tracking_metadata, dict)
        assert isinstance(packet.evidence_metadata, dict)
        assert packet.camera_metadata["lens"] == "wide"

        # Verify ISO timestamp property
        assert "2023-" in packet.iso_timestamp or "T" in packet.iso_timestamp

    def test_frame_packet_post_init_auto_dimensions(self, synthetic_frame: np.ndarray):
        """Verifies automatic shape detection if width/height are unspecified (0)."""
        packet = FramePacket(
            camera_id="CAM-AUTO",
            frame_id=1,
            source_type=SourceType.RTSP,
            timestamp=time.time(),
            raw_bgr=synthetic_frame,
            width=0,
            height=0,
        )
        assert packet.height == 480
        assert packet.width == 640

    def test_frame_packet_to_summary_dict(self, synthetic_frame: np.ndarray):
        """Verifies summary serialization avoids heavy ndarray while retaining bags."""
        packet = FramePacket(
            camera_id="CAM-SUM",
            frame_id=99,
            source_type=SourceType.MEDIAMTX,
            timestamp=time.time(),
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
            camera_metadata={"stream": "live"},
            inference_metadata={"threat": "none"},
        )
        summary = packet.to_summary_dict()

        assert summary["camera_id"] == "CAM-SUM"
        assert summary["frame_id"] == 99
        assert summary["source_type"] == "MEDIAMTX"
        assert summary["has_gpu_tensor"] is False
        assert "raw_bgr" not in summary  # No bulky pixel payload
        assert summary["camera"]["stream"] == "live"
        assert summary["inference"]["threat"] == "none"


class TestStaleFrameDroppingPolicy:
    """Verifies staleness detection and queue dropping policies under latency pressure."""

    def test_frame_packet_staleness_calculation(self, synthetic_frame: np.ndarray):
        """Verify age calculation and is_stale predicate."""
        now = time.time()

        # Fresh frame (0 ms old)
        fresh_packet = FramePacket(
            camera_id="CAM-FRESH",
            frame_id=1,
            source_type=SourceType.WEBCAM,
            timestamp=now,
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
        )
        assert fresh_packet.age_seconds < 0.5
        assert fresh_packet.is_stale(max_age_seconds=1.0) is False

        # Stale frame (3 seconds old)
        stale_packet = FramePacket(
            camera_id="CAM-STALE",
            frame_id=2,
            source_type=SourceType.WEBCAM,
            timestamp=now - 3.0,
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
        )
        assert stale_packet.age_seconds >= 2.9
        assert stale_packet.is_stale(max_age_seconds=1.0) is True
        assert stale_packet.is_stale(max_age_seconds=5.0) is False

    def test_bounded_buffer_stale_drop_policy(self, synthetic_frame: np.ndarray):
        """
        Verify that when adapter bounded buffer overflows, oldest frames are dropped,
        incrementing dropped_count and preserving the most recent frames.
        """
        adapter = WebcamAdapter(camera_id="CAM-DROP-TEST", device_index=0, config={"buffer_size": 3})

        # Push 6 sequential packets into a buffer of size 3
        for fid in range(1, 7):
            pkt = FramePacket(
                camera_id="CAM-DROP-TEST",
                frame_id=fid,
                source_type=SourceType.WEBCAM,
                timestamp=time.time(),
                raw_bgr=synthetic_frame,
                width=640,
                height=480,
            )
            adapter._push_packet(pkt)

        # Buffer size should not exceed 3
        assert adapter._packet_buffer_size == 3

        # Exactly 3 packets should have been dropped (fid 1, 2, 3)
        stats: CameraStats = adapter.get_stats()
        assert stats.dropped_frames == 3

        # Next packet retrieved should be frame_id 4
        next_pkt = adapter.get_next_packet()
        assert next_pkt is not None
        assert next_pkt.frame_id == 4

    def test_get_latest_packet_drops_intermediate_stale_frames(self, synthetic_frame: np.ndarray):
        """
        Verify get_latest_packet() drains intermediate stale packets from the buffer
        and returns only the newest packet for real-time inference.
        """
        adapter = RTSPAdapter(
            camera_id="CAM-LATEST-TEST",
            rtsp_url="rtsp://dummy/test",
            config={"buffer_size": 10},
        )

        # Push 5 packets (fid 10 to 14)
        for fid in range(10, 15):
            pkt = FramePacket(
                camera_id="CAM-LATEST-TEST",
                frame_id=fid,
                source_type=SourceType.RTSP,
                timestamp=time.time(),
                raw_bgr=synthetic_frame,
                width=640,
                height=480,
            )
            adapter._push_packet(pkt)

        assert adapter._packet_buffer_size == 5

        # Call get_latest_packet -> should return frame 14 directly
        latest = adapter.get_latest_packet()
        assert latest is not None
        assert latest.frame_id == 14

        # Queue should now be completely empty
        assert adapter._packet_buffer_size == 0
        assert adapter.get_next_packet() is None


class TestLatencyAndStatsTelemetry:
    """Verifies capture latency tracking, measured FPS, and downstream pipeline telemetry."""

    def test_camera_stats_telemetry(self, synthetic_frame: np.ndarray):
        """Verify CameraStats captures latency, queue depth, health, and frame counts."""
        adapter = MediaMTXAdapter(
            camera_id="CAM-STATS-TEST",
            mediamtx_rtsp_url="rtsp://127.0.0.1:8554/cam_stats",
            config={"buffer_size": 20},
        )
        adapter._health = CameraHealth.CONNECTED
        adapter._last_capture_latency_ms = 4.25
        adapter._total_packets = 50

        # Simulate 5 frame arrivals for FPS calculation
        t_base = time.time()
        for i in range(5):
            adapter._update_fps(t_base + i * 0.033)

        stats = adapter.get_stats()
        assert stats.camera_id == "CAM-STATS-TEST"
        assert stats.health == CameraHealth.CONNECTED
        assert stats.total_frames == 50
        assert stats.capture_latency_ms == 4.25
        assert stats.fps_measured > 0.0
        assert stats.queue_depth == 0

    def test_end_to_end_latency_telemetry(
        self,
        synthetic_frame: np.ndarray,
        preprocessor: SharedPreprocessor,
        orchestrator: AutonomousAIOrchestrator,
    ):
        """Verify end-to-end total latency and per-level latencies are recorded."""
        packet = FramePacket(
            camera_id="CAM-LAT",
            frame_id=1,
            source_type=SourceType.WEBCAM,
            timestamp=time.time(),
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
        )

        preprocessor.preprocess(packet)
        result = orchestrator.process_packet(packet)

        assert result.total_latency_ms > 0.0
        assert packet.inference_metadata["total_latency_ms"] == result.total_latency_ms

        for level in result.levels_executed:
            assert level.latency_ms >= 0.0
            assert level.level_name is not None


class TestBackwardCompatibility:
    """Verifies BaseSourceAdapter backward compatibility with CameraFrame and CameraSource."""

    def test_get_frame_returns_camera_frame(self, synthetic_frame: np.ndarray):
        """Verify get_frame() converts internal FramePacket into legacy CameraFrame."""
        adapter = WebcamAdapter(camera_id="CAM-LEGACY", device_index=0)
        pkt = FramePacket(
            camera_id="CAM-LEGACY",
            frame_id=7,
            source_type=SourceType.WEBCAM,
            timestamp=time.time(),
            raw_bgr=synthetic_frame,
            width=640,
            height=480,
        )
        adapter._push_packet(pkt)

        frame = adapter.get_frame()
        assert isinstance(frame, CameraFrame)
        assert frame.camera_id == "CAM-LEGACY"
        assert frame.frame_id == 7
        assert frame.width == 640
        assert frame.height == 480
        assert isinstance(frame.timestamp, datetime)

    def test_get_latest_frame_returns_newest_camera_frame(self, synthetic_frame: np.ndarray):
        """Verify get_latest_frame() drops older frames and returns newest CameraFrame."""
        adapter = RTSPAdapter(camera_id="CAM-LEGACY-LATEST", rtsp_url="rtsp://dummy")
        for fid in [10, 11, 12]:
            pkt = FramePacket(
                camera_id="CAM-LEGACY-LATEST",
                frame_id=fid,
                source_type=SourceType.RTSP,
                timestamp=time.time(),
                raw_bgr=synthetic_frame,
                width=640,
                height=480,
            )
            adapter._push_packet(pkt)

        frame = adapter.get_latest_frame()
        assert isinstance(frame, CameraFrame)
        assert frame.frame_id == 12
        assert adapter.get_frame() is None


class TestBoundingBoxUnletterboxRescaling:
    """Tests SharedPreprocessor scale_boxes_to_original coordinate reversal."""

    def test_coordinate_unletterboxing(self, synthetic_frame: np.ndarray, preprocessor: SharedPreprocessor):
        """
        Verify letterboxed coordinates map back accurately to original frame resolution.
        """
        packet = FramePacket(
            camera_id="CAM-SCALE",
            frame_id=1,
            source_type=SourceType.VIDEO_FILE,
            timestamp=time.time(),
            raw_bgr=synthetic_frame,  # 480x640
            width=640,
            height=480,
        )
        preprocessor.preprocess(packet, target_size=(640, 640))

        # Letterboxed coordinates on 640x640 canvas
        # 480x640 scaled to 640x640 with ratio=1.0, pad_w=0.0, pad_h=80.0
        pad_h = packet.preprocessing_metadata["pad_h"]
        pad_w = packet.preprocessing_metadata["pad_w"]

        boxes = np.array([
            [pad_w + 100, pad_h + 50, pad_w + 200, pad_h + 150]
        ], dtype=np.float32)

        rescaled = preprocessor.scale_boxes_to_original(boxes, packet)
        assert rescaled.shape == (1, 4)
        assert np.isclose(rescaled[0, 0], 100.0, atol=1.0)
        assert np.isclose(rescaled[0, 1], 50.0, atol=1.0)
        assert np.isclose(rescaled[0, 2], 200.0, atol=1.0)
        assert np.isclose(rescaled[0, 3], 150.0, atol=1.0)
