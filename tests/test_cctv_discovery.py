"""
Unit & Integration Tests for Physical CCTV Discovery Engine (SIH26187)
====================================================================
"""

import pytest
import os
import sys

from services.ingestion.cctv_discovery import (
    get_arp_ips,
    get_local_adapter_ips,
    get_subnet_sweep_ips,
    collect_target_candidates,
    check_tcp_port,
    scan_cctv_ports,
    discover_active_cctv,
    COMMON_CAMERA_FACTORY_IPS
)


def test_collect_target_candidates_returns_list():
    candidates = collect_target_candidates()
    assert isinstance(candidates, list)
    # Should include common factory defaults
    for default_ip in COMMON_CAMERA_FACTORY_IPS[:3]:
        assert default_ip in candidates


@pytest.fixture
def local_tcp_listener():
    """Provides a guaranteed listening loopback TCP socket for deterministic unit testing."""
    import socket
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    yield port
    srv.close()


def test_check_tcp_port_local(local_tcp_listener):
    ip, port, is_open = check_tcp_port("127.0.0.1", local_tcp_listener, timeout=0.3)
    assert ip == "127.0.0.1"
    assert port == local_tcp_listener
    assert is_open is True


def test_check_tcp_port_closed():
    ip, port, is_open = check_tcp_port("127.0.0.1", 59999, timeout=0.2)
    assert is_open is False


def test_scan_cctv_ports(local_tcp_listener):
    targets = scan_cctv_ports(["127.0.0.1"], ports=[local_tcp_listener, 59999], max_workers=2)
    assert ("127.0.0.1", local_tcp_listener) in targets
    assert ("127.0.0.1", 59999) not in targets


def test_mediamtx_port_live_integration():
    """Integration check for live MediaMTX daemon (gracefully skipped if daemon is offline)."""
    ip, port, is_open = check_tcp_port("127.0.0.1", 8554, timeout=0.2)
    if not is_open:
        pytest.skip("Optional MediaMTX RTSP server offline on port 8554 (run scripts/start_mediamtx.bat for live streaming)")
    assert is_open is True


def test_discover_active_cctv_fallback():
    # With no physical camera plugged in, should gracefully fallback to CAM-01 simulator
    res = discover_active_cctv(auto_register=False)
    assert isinstance(res, dict)
    assert res["status"] in ("connected", "fallback_simulator")
    assert "camera_id" in res
    assert "masked_url" in res
