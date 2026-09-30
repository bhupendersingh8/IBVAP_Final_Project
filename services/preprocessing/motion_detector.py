"""
IBVAP Adaptive Frame Skipping & Motion Gating Engine (Phase 6 Performance Architecture)
====================================================================================
Prevents wasteful neural network inference on stationary/static CCTV feeds.
Uses dual-metric evaluation:
1. Fast temporal frame difference on downsampled grayscale representation.
2. Lightweight sparse optical flow / Farneback velocity vector estimation for creeping motion.
3. Maximum skip watchdog: guarantees a keyframe inference pass at least once every N frames.
"""

import cv2
import numpy as np
import time
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class MotionEvaluationResult:
    motion_detected: bool
    motion_score: float        # Percentage of pixels with significant luminance delta (0.0 to 1.0)
    should_skip_inference: bool
    consecutive_skips: int
    flow_magnitude: float
    elapsed_ms: float

class AdaptiveFrameSkipper:
    """
    Evaluates successive CCTV video frames to gate deep learning inference.
    Saves up to 60-80% of CPU inference cycles during static/night scenes with zero activity.
    """
    def __init__(
        self,
        motion_threshold: float = 0.005,  # 0.5% of pixels changed triggers motion
        pixel_diff_threshold: int = 22,    # Pixel intensity delta to qualify as change
        max_consecutive_skips: int = 15,   # Force inference at least once every 15 frames (1 sec @ 15fps)
        downsample_size: Tuple[int, int] = (160, 120)
    ):
        self.motion_threshold = motion_threshold
        self.pixel_diff_threshold = pixel_diff_threshold
        self.max_consecutive_skips = max_consecutive_skips
        self.downsample_size = downsample_size
        
        self.prev_gray: Optional[np.ndarray] = None
        self.consecutive_skips = 0
        self.total_frames_evaluated = 0
        self.total_frames_skipped = 0

    def evaluate(self, frame: np.ndarray) -> MotionEvaluationResult:
        """
        Determines whether the current frame contains significant motion.
        Returns MotionEvaluationResult with skip recommendation.
        """
        t0 = time.perf_counter()
        self.total_frames_evaluated += 1
        
        if frame is None or frame.size == 0:
            return MotionEvaluationResult(
                motion_detected=False,
                motion_score=0.0,
                should_skip_inference=True,
                consecutive_skips=self.consecutive_skips,
                flow_magnitude=0.0,
                elapsed_ms=(time.perf_counter() - t0) * 1000
            )

        # 1. Downscale and convert to grayscale for microsecond CPU execution
        small = cv2.resize(frame, self.downsample_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # First frame always runs inference to establish scene baseline
        if self.prev_gray is None:
            self.prev_gray = gray
            self.consecutive_skips = 0
            return MotionEvaluationResult(
                motion_detected=True,
                motion_score=1.0,
                should_skip_inference=False,
                consecutive_skips=0,
                flow_magnitude=0.0,
                elapsed_ms=(time.perf_counter() - t0) * 1000
            )

        # 2. Frame differencing
        delta = cv2.absdiff(self.prev_gray, gray)
        _, thresh = cv2.threshold(delta, self.pixel_diff_threshold, 255, cv2.THRESH_BINARY)
        
        # Calculate ratio of changed pixels
        changed_pixels = int(np.count_nonzero(thresh))
        total_pixels = self.downsample_size[0] * self.downsample_size[1]
        motion_score = changed_pixels / float(total_pixels)
        
        # 3. Calculate optical flow magnitude on significant deltas
        flow_mag = 0.0
        if motion_score > (self.motion_threshold * 0.5):
            # Compute lightweight Farneback optical flow on small grid
            flow = cv2.calcOpticalFlowFarneback(
                self.prev_gray, gray, None,
                pyr_scale=0.5, levels=1, winsize=9,
                iterations=2, poly_n=5, poly_sigma=1.1, flags=0
            )
            flow_mag = float(np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)))

        motion_detected = (motion_score >= self.motion_threshold) or (flow_mag >= 0.35)

        # 4. Watchdog: never skip more than max_consecutive_skips
        if not motion_detected and self.consecutive_skips < self.max_consecutive_skips:
            self.consecutive_skips += 1
            self.total_frames_skipped += 1
            should_skip = True
        else:
            # Motion detected OR watchdog expired: run inference and refresh reference background
            self.prev_gray = gray
            self.consecutive_skips = 0
            should_skip = False

        elapsed = (time.perf_counter() - t0) * 1000
        return MotionEvaluationResult(
            motion_detected=motion_detected,
            motion_score=round(motion_score, 4),
            should_skip_inference=should_skip,
            consecutive_skips=self.consecutive_skips,
            flow_magnitude=round(flow_mag, 3),
            elapsed_ms=round(elapsed, 2)
        )

    def reset(self):
        """Resets the temporal reference frame."""
        self.prev_gray = None
        self.consecutive_skips = 0
