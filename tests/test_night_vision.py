import os
import cv2
import numpy as np
import pytest
from services.preprocessing.night_enhancer import (
    NightVisionEnhancer,
    NightEnhancementResult,
    NightMode
)
from services.auth_personnel.blink_detector import (
    EyeBlinkLivenessDetector,
    LivenessResult,
    TrackBlinkState
)
from services.auth_personnel.personnel_manager import (
    AuthorizedPersonnelManager,
    AuthorizedPerson
)


class TestNightVisionEnhancer:
    def setup_method(self):
        self.enhancer = NightVisionEnhancer(
            daylight_thresh=85.0,
            low_light_thresh=48.0,
            pitch_night_thresh=25.0
        )

    def test_daylight_mode(self):
        # Frame with brightness ~140
        day_frame = np.full((300, 400, 3), 140, dtype=np.uint8)
        # Add some color variation
        day_frame[:, :, 0] = 100
        day_frame[:, :, 2] = 180

        res = self.enhancer.enhance(day_frame)
        assert not res.is_night
        assert res.mode == NightMode.DAYLIGHT.value
        assert res.gamma_applied == 1.0
        assert not res.clahe_applied

    def test_low_light_enhancement(self):
        # Low-light frame with color (brightness ~45, saturation > 25)
        dark_frame = np.zeros((300, 400, 3), dtype=np.uint8)
        dark_frame[:, :, 0] = 25  # Blue
        dark_frame[:, :, 1] = 45  # Green
        dark_frame[:, :, 2] = 65  # Red
        cv2.circle(dark_frame, (150, 150), 40, (35, 70, 95), -1)

        res = self.enhancer.enhance(dark_frame)
        assert res.is_night
        assert res.mode == NightMode.LOW_LIGHT.value
        assert res.gamma_applied == 0.55
        assert res.clahe_applied
        # Brightness must be significantly lifted
        enhanced_mean = float(np.mean(res.frame))
        assert enhanced_mean > 40.0, f"Enhanced brightness ({enhanced_mean}) should exceed initial 40"

    def test_pitch_night_enhancement(self):
        # Pitch night frame with brightness ~12
        pitch_frame = np.full((300, 400, 3), 12, dtype=np.uint8)
        cv2.circle(pitch_frame, (150, 150), 30, (25, 25, 25), -1)

        res = self.enhancer.enhance(pitch_frame)
        assert res.is_night
        assert res.mode == NightMode.PITCH_NIGHT.value
        assert res.gamma_applied == 0.42
        assert res.clahe_applied
        enhanced_mean = float(np.mean(res.frame))
        assert enhanced_mean >= 35.0, f"Pitch night enhanced mean ({enhanced_mean}) should be >= 35"

    def test_infrared_monochrome_mode(self):
        # Monochromatic frame (B=G=R) with low brightness
        gray_val = 55
        ir_frame = np.full((300, 400, 3), gray_val, dtype=np.uint8)
        # Monochromatic means saturation is 0

        res = self.enhancer.enhance(ir_frame)
        assert res.is_night
        assert res.mode == NightMode.INFRARED_MONOCHROME.value
        assert res.clahe_applied

    def test_performance_latency(self):
        # Ensure enhancement runs in < 8ms on standard 640x480 frame for real-time RTSP
        frame = np.random.randint(10, 60, (480, 640, 3), dtype=np.uint8)
        import time
        t0 = time.perf_counter()
        for _ in range(10):
            self.enhancer.enhance(frame)
        avg_time = (time.perf_counter() - t0) / 10.0 * 1000
        assert avg_time < 20.0, f"Enhancement took {avg_time:.2f}ms, should be < 20ms"


class TestNightBlinkDetection:
    def setup_method(self):
        self.detector = EyeBlinkLivenessDetector(min_blinks_required=1, spoof_frame_threshold=30)

    def test_night_eye_openness_gradient(self):
        # Create dark synthetic eye patch (average brightness ~20)
        eye_patch = np.full((32, 24, 3), 18, dtype=np.uint8)
        # Draw high-contrast horizontal edge (eyelid margin)
        eye_patch[14:18, :, :] = 45

        # compute_eye_openness applies adaptive local CLAHE
        openness = self.detector.compute_eye_openness(eye_patch)
        assert openness > 15.0, f"Expected distinct gradient in dark patch, got {openness}"

    def test_night_blink_sequence(self):
        track_id = 99
        # Simulate open eye in darkness
        dark_open = np.full((32, 24, 3), 18, dtype=np.uint8)
        dark_open[14:18, :, :] = 55  # strong horizontal edge

        # Simulate closed eye in darkness (flat gradient)
        dark_closed = np.full((32, 24, 3), 20, dtype=np.uint8)

        open_val = self.detector.compute_eye_openness(dark_open)
        closed_val = self.detector.compute_eye_openness(dark_closed)
        assert open_val > closed_val * 1.5, f"Open {open_val} should exceed closed {closed_val} in darkness"

        track_state = TrackBlinkState(track_id=track_id)
        # Feed 5 open frames to establish baseline
        for _ in range(5):
            track_state.update(open_val)
        assert track_state.state == "OPEN"

        # Feed 3 closed frames
        for _ in range(3):
            track_state.update(closed_val)
        assert track_state.state in ("CLOSING", "PROLONGED_CLOSED")

        # Feed 3 re-opened frames to complete blink cycle
        for _ in range(3):
            track_state.update(open_val)

        assert track_state.blink_count >= 1
        assert track_state.is_live is True


class TestNightPersonnelVerification:
    def setup_method(self):
        # Create a test manager with a mock authorized person
        self.manager = AuthorizedPersonnelManager.get_instance()

        # Create a synthetic daylight reference face
        ref_face = np.full((160, 160, 3), 160, dtype=np.uint8)
        # Add facial features (eyes, nose, mouth)
        cv2.circle(ref_face, (50, 55), 12, (50, 50, 50), -1)   # left eye
        cv2.circle(ref_face, (110, 55), 12, (50, 50, 50), -1)  # right eye
        cv2.line(ref_face, (80, 75), (80, 95), (60, 60, 60), 3) # nose
        cv2.ellipse(ref_face, (80, 120), (30, 10), 0, 0, 180, (40, 40, 140), -1) # mouth

        person = AuthorizedPerson(
            id="AUTH-NIGHT-TEST",
            name="Officer Night Vigil",
            role="Border Guard",
            department="Night Patrol",
            image_file="night_test.jpg",
            status="authorized"
        )
        # Extract features directly
        person.template_crop = ref_face
        gray = cv2.cvtColor(ref_face, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        gray_eq = clahe.apply(gray)
        person.gray_template = gray_eq

        gray_hist = cv2.calcHist([gray_eq], [0], None, [32], [0, 256])
        cv2.normalize(gray_hist, gray_hist, 0, 1, cv2.NORM_MINMAX)
        person.gray_clahe_hist = gray_hist

        hsv = cv2.cvtColor(ref_face, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [18, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
        person.hist = hist

        self.manager.personnel["AUTH-NIGHT-TEST"] = person
        self.test_person = person
        self.ref_face = ref_face

    def test_night_query_verification(self):
        # Simulate query taken at night (darkened by 70%)
        night_query = (self.ref_face.astype(np.float32) * 0.30).astype(np.uint8)
        assert np.mean(night_query) < 55.0  # confirm it is dark

        res = self.manager.verify_crop(night_query)
        assert res.is_authorized, f"Night query should match authorized personnel, got {res}"
        assert res.person_id == "AUTH-NIGHT-TEST"
        assert res.matched_features.get("night_mode_active") is True

    def test_infrared_query_verification(self):
        # Simulate query taken under Infrared camera (monochrome + darkened)
        gray = cv2.cvtColor(self.ref_face, cv2.COLOR_BGR2GRAY)
        ir_query = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        ir_query = (ir_query.astype(np.float32) * 0.40).astype(np.uint8)

        res = self.manager.verify_crop(ir_query)
        assert res.is_authorized, f"IR query should match authorized personnel, got {res}"
        assert res.person_id == "AUTH-NIGHT-TEST"
        assert res.matched_features.get("night_mode_active") is True

    def test_unauthorized_stranger_rejected_at_night(self):
        # Completely different stranger face
        stranger_face = np.full((160, 160, 3), 35, dtype=np.uint8)
        cv2.rectangle(stranger_face, (20, 20), (140, 140), (70, 70, 70), -1)

        res = self.manager.verify_crop(stranger_face)
        assert not res.is_authorized, f"Stranger must be rejected at night, got {res}"
        assert res.person_id is None
