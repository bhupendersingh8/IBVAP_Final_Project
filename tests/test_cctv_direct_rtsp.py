"""
Unit & Integration Tests: Direct RTSP CCTV Pipeline & Security Validation
========================================================================
Validates requirements for Real College IP Camera integration (SIH26187):
1. Runtime configurable direct RTSP URLs
2. SSRF prevention (cloud metadata, multicast)
3. Path traversal & shell injection blocking
4. Credential masking across logs, responses, and errors
5. Direct RTSP support without requiring MediaMTX
6. Dynamic resolution, FPS, and disconnect resilience
"""

import pytest
import os
import json
from services.ingestion.rtsp_security import (
    mask_rtsp_url,
    build_rtsp_url,
    validate_rtsp_url,
    RTSPCameraConfig,
    RTSPRuntimeRegistry,
    probe_rtsp_target,
    SecurityValidationError
)
from services.ingestion.source_adapters import SourceAdapterFactory, RTSPAdapter
from services.ingestion.rtsp_source import RTSPSource


# ─── 1. Credential Masking Tests ──────────────────────────────────────────────

def test_mask_rtsp_url_standard():
    raw = "rtsp://admin:SecretPass123@192.168.1.100:554/Streaming/Channels/101"
    masked = mask_rtsp_url(raw)
    assert "SecretPass123" not in masked
    assert masked == "rtsp://admin:***@192.168.1.100:554/Streaming/Channels/101"


def test_mask_rtsp_url_without_credentials():
    raw = "rtsp://192.168.1.100:554/live/ch0"
    masked = mask_rtsp_url(raw)
    assert masked == raw


def test_mask_rtsp_url_special_characters():
    raw = "rtsp://operator:p%40ssw0rd%21@10.0.0.55:554/ch0"
    masked = mask_rtsp_url(raw)
    assert "p%40ssw0rd%21" not in masked
    assert "***" in masked


def test_mask_rtsp_url_empty():
    assert mask_rtsp_url("") == ""
    assert mask_rtsp_url(None) == ""


# ─── 2. URL Builder Tests ─────────────────────────────────────────────────────

def test_build_rtsp_url_clean():
    url = build_rtsp_url(host="192.168.1.50", port=554, stream_path="/h264")
    assert url == "rtsp://192.168.1.50/h264"


def test_build_rtsp_url_with_credentials():
    url = build_rtsp_url(
        host="192.168.1.120",
        port=8554,
        stream_path="live/ch0",
        username="admin",
        password="CollegePassword123"
    )
    assert url == "rtsp://admin:CollegePassword123@192.168.1.120:8554/live/ch0"
    # Ensure masked version works
    assert mask_rtsp_url(url) == "rtsp://admin:***@192.168.1.120:8554/live/ch0"


# ─── 3. Security & SSRF Validation Tests ──────────────────────────────────────

def test_validate_rtsp_url_valid_private_ip():
    ok, err = validate_rtsp_url("rtsp://192.168.1.100:554/Streaming/Channels/101")
    assert ok is True
    assert err is None


def test_validate_rtsp_url_valid_campus_subnet():
    ok, err = validate_rtsp_url("rtsp://admin:pass@10.20.30.40:554/cam0")
    assert ok is True
    assert err is None


def test_validate_rtsp_url_valid_localhost_for_mediamtx():
    ok, err = validate_rtsp_url("rtsp://127.0.0.1:8554/CAM-01")
    assert ok is True
    assert err is None


def test_validate_rtsp_url_block_cloud_metadata_ip():
    ok, err = validate_rtsp_url("rtsp://169.254.169.254:554/latest/meta-data")
    assert ok is False
    assert "SSRF" in err or "metadata" in err.lower()


def test_validate_rtsp_url_block_google_metadata_host():
    ok, err = validate_rtsp_url("rtsp://metadata.google.internal:554/ch0")
    assert ok is False
    assert "SSRF" in err or "metadata" in err.lower()


def test_validate_rtsp_url_block_multicast():
    ok, err = validate_rtsp_url("rtsp://224.0.0.1:554/stream")
    assert ok is False
    assert "Multicast" in err


def test_validate_rtsp_url_block_path_traversal():
    ok, err = validate_rtsp_url("rtsp://192.168.1.50:554/../../etc/shadow")
    assert ok is False
    assert "Directory traversal" in err


def test_validate_rtsp_url_block_shell_metacharacters():
    ok, err = validate_rtsp_url("rtsp://192.168.1.50:554/ch0;cat /etc/passwd")
    assert ok is False
    assert "illegal" in err.lower() or "control" in err.lower()


def test_validate_rtsp_url_block_pipe_injection():
    ok, err = validate_rtsp_url("rtsp://192.168.1.50:554/ch0|reboot")
    assert ok is False
    assert "illegal" in err.lower()


def test_validate_rtsp_url_invalid_scheme():
    ok, err = validate_rtsp_url("ftp://192.168.1.50:554/ch0")
    assert ok is False
    assert "Invalid scheme" in err


def test_validate_rtsp_url_invalid_port():
    ok, err = validate_rtsp_url("rtsp://192.168.1.50:70000/ch0")
    assert ok is False
    assert "range" in err.lower()


# ─── 4. Pydantic Model & Credential Protection Tests ─────────────────────────

def test_rtsp_camera_config_masked_url():
    cfg = RTSPCameraConfig(
        camera_id="COLLEGE-CAM-01",
        name="Main College Gate",
        host="192.168.1.150",
        port=554,
        stream_path="/Streaming/Channels/101",
        username="admin",
        password="TopSecretPassword",
        scenario="vehicle_anpr"
    )
    raw_url = cfg.get_connection_url()
    assert "TopSecretPassword" in raw_url
    assert "rtsp://admin:TopSecretPassword@192.168.1.150/Streaming/Channels/101" == raw_url

    masked = cfg.get_masked_url()
    assert "TopSecretPassword" not in masked
    assert "rtsp://admin:***@192.168.1.150/Streaming/Channels/101" == masked

    runtime_dict = cfg.to_runtime_dict(include_secrets=False)
    assert "password" not in runtime_dict
    assert "connection_url" not in runtime_dict
    assert runtime_dict["masked_url"] == masked


def test_rtsp_camera_config_validation():
    with pytest.raises(Exception):
        # Invalid camera_id with special characters
        RTSPCameraConfig(
            camera_id="BAD CAMERA ID!!!",
            host="192.168.1.50"
        )


# ─── 5. Runtime Registry Tests ────────────────────────────────────────────────

def test_rtsp_runtime_registry_lifecycle(tmp_path):
    vault_file = str(tmp_path / "test_cameras_runtime.json")
    registry = RTSPRuntimeRegistry(config_path=vault_file)

    cfg = RTSPCameraConfig(
        camera_id="TEST-COLLEGE-01",
        name="Auditorium Gate",
        host="192.168.4.12",
        port=554,
        stream_path="/live/ch0",
        username="security",
        password="SuperPassword99"
    )

    # Register
    registry.register_camera(cfg)
    assert os.path.exists(vault_file)

    # Retrieve
    retrieved = registry.get_camera("TEST-COLLEGE-01")
    assert retrieved is not None
    assert retrieved.camera_id == "TEST-COLLEGE-01"
    assert retrieved.password == "SuperPassword99"
    assert "SuperPassword99" not in retrieved.get_masked_url()

    # List with masked credentials
    cam_list = registry.list_cameras(mask_credentials=True)
    assert len(cam_list) == 1
    assert "password" not in cam_list[0]
    assert "masked_url" in cam_list[0]

    # Delete
    deleted = registry.delete_camera("TEST-COLLEGE-01")
    assert deleted is True
    assert registry.get_camera("TEST-COLLEGE-01") is None


# ─── 6. Physical Probe Tests ──────────────────────────────────────────────────

def test_probe_rtsp_target_local():
    import socket
    # Spin up ephemeral listening socket to test local probe deterministically
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        res = probe_rtsp_target("127.0.0.1", port, timeout_seconds=1.0)
        assert res["host"] == "127.0.0.1"
        assert res["port"] == port
        assert res["tcp_reachable"] is True
        assert res["latency_ms"] >= 0
    finally:
        srv.close()


def test_probe_rtsp_target_unreachable():
    # Non-routable test address (RFC 5737 TEST-NET-1)
    res = probe_rtsp_target("192.0.2.1", 554, timeout_seconds=0.3)
    assert res["tcp_reachable"] is False
    assert res["error"] is not None


# ─── 7. Ingestion Direct RTSP Source Resilience Tests ─────────────────────────

def test_source_adapter_factory_direct_rtsp():
    url = "rtsp://admin:test@192.168.1.100:554/live"
    adapter = SourceAdapterFactory.create_adapter(
        camera_id="COLLEGE-CAM-TEST",
        source_uri=url
    )
    assert isinstance(adapter, RTSPAdapter)
    assert adapter.camera_id == "COLLEGE-CAM-TEST"
    assert "test" not in adapter.get_stats().error_message if adapter.get_stats().error_message else True


def test_rtsp_source_graceful_offline_handling():
    # Target an offline IP — RTSPSource must not crash the process
    source = RTSPSource(
        camera_id="OFFLINE-CCTV",
        config={
            "rtsp_url": "rtsp://admin:secret@127.0.0.1:55499/live",
            "fps_limit": 10,
            "reconnect_delay_seconds": 0.2,
            "max_reconnect_attempts": 1
        }
    )
    source.start()
    assert source.is_alive()
    source.stop()
    assert not source.is_alive()
    stats = source.get_stats()
    # Confirm credentials are not exposed in stats error message
    if stats.error_message:
        assert "secret" not in stats.error_message
