import time
import pytest
from services.ingestion.shared_frame_buffer import SharedFrameWriter, SharedFrameReader, SEQLOCK_MAGIC, HEADER_SIZE

def test_shared_frame_writer_and_reader():
    cam_id = "test_cam_seqlock_01"
    writer = SharedFrameWriter(cam_id, size=1024 * 1024)
    reader = SharedFrameReader(cam_id)

    try:
        payload = b"\xff\xd8\xff\xe0" + b"X" * 1000 + b"\xff\xd9"
        written = writer.write_frame(payload)
        assert written is True

        res = reader.read_frame(max_age_seconds=5.0)
        assert res is not None
        data, ts = res
        assert data == payload
        assert (time.time() - ts) < 2.0
    finally:
        reader.close()
        writer.close()

def test_shared_frame_seqlock_in_progress_retry():
    cam_id = "test_cam_seqlock_02"
    writer = SharedFrameWriter(cam_id, size=1024 * 1024)
    reader = SharedFrameReader(cam_id)

    try:
        payload = b"TEST_PAYLOAD_DATA"
        writer.write_frame(payload)

        # Simulate in-progress write by manually modifying seq_start to odd
        writer.shm.buf[4:12] = (7).to_bytes(8, 'big') # odd = in progress
        # Read should detect in-progress and return None after max_retries
        res = reader.read_frame(max_age_seconds=5.0, max_retries=2)
        assert res is None

        # Reset to valid committed sequence
        writer.shm.buf[4:12] = (8).to_bytes(8, 'big')
        writer.shm.buf[24:32] = (8).to_bytes(8, 'big')
        res = reader.read_frame(max_age_seconds=5.0)
        assert res is not None
        assert res[0] == payload
    finally:
        reader.close()
        writer.close()

def test_shared_frame_legacy_fallback():
    cam_id = "test_cam_seqlock_legacy"
    writer = SharedFrameWriter(cam_id, size=1024 * 1024)
    reader = SharedFrameReader(cam_id)

    try:
        # Write legacy format directly without magic
        payload = b"LEGACY_JPEG_CONTENT"
        now_ms = int(time.time() * 1000)
        writer.shm.buf[0:8] = now_ms.to_bytes(8, 'big')
        writer.shm.buf[8:12] = len(payload).to_bytes(4, 'big')
        writer.shm.buf[12:12+len(payload)] = payload

        res = reader.read_frame(max_age_seconds=5.0)
        assert res is not None
        data, ts = res
        assert data == payload
    finally:
        reader.close()
        writer.close()
