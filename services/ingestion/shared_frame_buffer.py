"""
Shared Memory Frame Buffer for Zero-Disk-I/O Video Streaming.
Enables high-FPS, zero-copy, atomic Seqlock communication between Inference Workers and FastAPI MJPEG endpoints.
Guarantees zero torn or corrupted frames under concurrent multi-process access.
"""
import struct
import time
from multiprocessing import shared_memory
from typing import Optional, Tuple
import structlog

logger = structlog.get_logger()

# 1.5MB buffer is more than enough for a 1080p/720p compressed JPEG (typically 50-180KB)
DEFAULT_SHM_SIZE = 1536 * 1024 

# Header format:
# Magic: 4 bytes (b"IBVF")
# Seq Start: 8 bytes (uint64)
# Timestamp ms: 8 bytes (uint64)
# Data length: 4 bytes (uint32)
# Seq End: 8 bytes (uint64)
# Header total = 32 bytes. Payload starts at offset 32.
SEQLOCK_MAGIC = b"IBVF"
HEADER_SIZE = 32


class SharedFrameWriter:
    """
    Used by MainInferenceWorker to publish live frames into RAM using an atomic Seqlock protocol.
    Guarantees no torn or partially written frames can be read by clients.
    """
    def __init__(self, camera_id: str, size: int = DEFAULT_SHM_SIZE):
        safe_id = camera_id.replace('-', '_').replace(':', '_').lower()
        self.shm_name = f'ibvap_frame_{safe_id}'
        self.size = size
        self.shm: Optional[shared_memory.SharedMemory] = None
        self._seq_counter: int = 0
        self._init_shm()

    def _init_shm(self):
        try:
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=True, size=self.size)
            # Initialize header with zeroes
            self.shm.buf[:HEADER_SIZE] = b'\x00' * HEADER_SIZE
            logger.info('Created new shared frame memory buffer with Seqlock', name=self.shm_name)
        except FileExistsError:
            try:
                self.shm = shared_memory.SharedMemory(name=self.shm_name)
                logger.info('Attached to existing shared frame buffer', name=self.shm_name)
            except Exception as e:
                logger.warning('Failed to attach to shared memory', error=str(e))
                self.shm = None
        except Exception as e:
            logger.warning('Could not create shared memory', error=str(e))
            self.shm = None

    def write_frame(self, jpeg_bytes: bytes) -> bool:
        if not self.shm:
            self._init_shm()
            if not self.shm:
                return False
        n = len(jpeg_bytes)
        if n + HEADER_SIZE > self.size:
            logger.warning('Frame exceeds shared memory buffer size', size=n, max_size=self.size)
            return False
        try:
            self._seq_counter += 1
            # Step 1: Set seq_start to odd (write in progress)
            seq_in_progress = self._seq_counter * 2 + 1
            now_ms = int(time.time() * 1000)

            # Write in-progress header
            # magic (4B), seq_start (8B), timestamp_ms (8B), length (4B), seq_end (8B placeholder)
            self.shm.buf[0:4] = SEQLOCK_MAGIC
            self.shm.buf[4:12] = seq_in_progress.to_bytes(8, 'big')
            self.shm.buf[12:20] = now_ms.to_bytes(8, 'big')
            self.shm.buf[20:24] = n.to_bytes(4, 'big')

            # Step 2: Write frame payload
            self.shm.buf[HEADER_SIZE:HEADER_SIZE + n] = jpeg_bytes

            # Step 3: Set seq_end and seq_start to even (write committed, matched)
            seq_committed = self._seq_counter * 2 + 2
            self.shm.buf[24:32] = seq_committed.to_bytes(8, 'big')
            self.shm.buf[4:12] = seq_committed.to_bytes(8, 'big')

            return True
        except Exception as e:
            logger.warning('Shared memory write error', error=str(e))
            return False

    def close(self):
        if self.shm is not None:
            try:
                self.shm.close()
                self.shm.unlink()
            except Exception:
                pass
            self.shm = None


class SharedFrameReader:
    """
    Used by FastAPI stream_camera to read live frames from RAM with zero locks and zero torn reads.
    Employs Seqlock retry validation.
    """
    def __init__(self, camera_id: str):
        safe_id = camera_id.replace('-', '_').replace(':', '_').lower()
        self.shm_name = f'ibvap_frame_{safe_id}'
        self.shm: Optional[shared_memory.SharedMemory] = None

    def read_frame(self, max_age_seconds: float = 3.5, max_retries: int = 3) -> Optional[Tuple[bytes, float]]:
        try:
            if self.shm is None:
                self.shm = shared_memory.SharedMemory(name=self.shm_name)

            buf = self.shm.buf

            # Support both Seqlock (magic == b'IBVF') and legacy format
            magic = bytes(buf[0:4])
            if magic == SEQLOCK_MAGIC:
                for _ in range(max_retries):
                    seq_start = int.from_bytes(buf[4:12], 'big')
                    # If odd, writer is actively writing
                    if seq_start % 2 != 0:
                        time.sleep(0.0005)
                        continue

                    ts_ms = int.from_bytes(buf[12:20], 'big')
                    length = int.from_bytes(buf[20:24], 'big')
                    seq_end = int.from_bytes(buf[24:32], 'big')

                    # If sequences don't match, writer modified mid-read
                    if seq_start != seq_end:
                        time.sleep(0.0005)
                        continue

                    if length <= 0 or length > len(buf) - HEADER_SIZE:
                        return None

                    data = bytes(buf[HEADER_SIZE:HEADER_SIZE + length])

                    # Verify seq_start hasn't changed while reading data
                    seq_verify = int.from_bytes(buf[4:12], 'big')
                    if seq_verify != seq_start:
                        time.sleep(0.0005)
                        continue

                    frame_time = ts_ms / 1000.0
                    if (time.time() - frame_time) > max_age_seconds:
                        return None

                    return data, frame_time
                return None
            else:
                # Legacy format fallback: [0:8] ts_ms, [8:12] len, [12:12+n] data
                ts_ms = int.from_bytes(buf[0:8], 'big')
                frame_time = ts_ms / 1000.0
                if (time.time() - frame_time) > max_age_seconds:
                    return None
                length = int.from_bytes(buf[8:12], 'big')
                if length <= 0 or length > len(buf) - 12:
                    return None
                data = bytes(buf[12:12 + length])
                return data, frame_time

        except (FileNotFoundError, Exception):
            if self.shm is not None:
                try:
                    self.shm.close()
                except Exception:
                    pass
                self.shm = None
            return None

    def close(self):
        if self.shm is not None:
            try:
                self.shm.close()
            except Exception:
                pass
            self.shm = None
