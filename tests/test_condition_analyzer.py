"""
Tests for ConditionAnalyzer and EnhancementManager (Phase 3)
Verifies adaptive condition-aware perception and telemetry.
"""

import cv2
import numpy as np
import pytest

from services.preprocessing.condition_analyzer import (
    ConditionAnalyzer,
    EnhancementManager,
    EnvironmentalCondition,
)


class TestConditionAwarePerception:
    def setup_method(self):
        self.analyzer = ConditionAnalyzer(
            low_light_thresh=75.0,
            pitch_dark_thresh=38.0,
            blur_thresh=40.0,
            shake_thresh=18.0,
            haze_min_dark_channel=0.35,
        )
        self.enhancer = EnhancementManager()

    def test_clear_normal_scene_fast_path(self):
        # Create a sharp, high-contrast daylight image with real dark shadows
        frame = np.full((320, 480, 3), 130, dtype=np.uint8)
        frame[0:50, :] = [10, 10, 10]  # Dark shadows guarantee low dark-channel
        frame[250:320, :] = [230, 230, 230]  # Bright sky
        # Add high-contrast geometric features for edge variance
        for i in range(10, 450, 40):
            cv2.rectangle(frame, (i, 50), (i + 20, 250), (20, 220, 30), -1)
            cv2.circle(frame, (i + 10, 150), 15, (220, 30, 20), -1)

        analysis = self.analyzer.analyze(frame)
        assert analysis.condition in (EnvironmentalCondition.CLEAR, EnvironmentalCondition.NORMAL)
        assert not analysis.is_degraded

        result = self.enhancer.enhance(frame, analysis)
        assert result.transformation_applied == "NONE"
        assert "Fast path" in result.decision_reason
        assert result.processing_latency_ms >= 0.0
        assert result.input_quality > 0.0

    def test_low_light_adaptive_enhancement(self):
        # Create a low-light frame (brightness ~ 50)
        frame = np.full((320, 480, 3), 50, dtype=np.uint8)
        cv2.circle(frame, (200, 160), 50, (70, 70, 70), -1)

        analysis = self.analyzer.analyze(frame)
        assert analysis.condition == EnvironmentalCondition.LOW_LIGHT

        result = self.enhancer.enhance(frame, analysis)
        assert result.transformation_applied == "ADAPTIVE_CLAHE_GAMMA"
        assert "Adaptive illumination recovery" in result.decision_reason
        assert result.processing_latency_ms > 0.0

    def test_pitch_night_adaptive_enhancement(self):
        # Create a near-black frame (brightness ~ 15)
        frame = np.full((320, 480, 3), 15, dtype=np.uint8)
        cv2.circle(frame, (200, 160), 40, (28, 28, 28), -1)

        analysis = self.analyzer.analyze(frame)
        assert analysis.condition == EnvironmentalCondition.NIGHT

        result = self.enhancer.enhance(frame, analysis)
        assert result.transformation_applied == "ADAPTIVE_CLAHE_GAMMA"
        # Brightness should be increased
        assert float(np.mean(result.frame)) > float(np.mean(frame))

    def test_severe_blur_marked_degraded_no_hallucination(self):
        # Create a blurred frame with real scene contrast but blurred edges
        sharp = np.zeros((320, 480, 3), dtype=np.uint8)
        sharp[0:160, :] = 240
        sharp[160:320, :] = 15
        blurred = cv2.GaussianBlur(sharp, (61, 61), 0)

        analysis = self.analyzer.analyze(blurred)
        assert analysis.condition == EnvironmentalCondition.BLUR
        assert analysis.is_degraded
        assert "blur" in analysis.reason.lower()

        result = self.enhancer.enhance(blurred, analysis)
        assert result.transformation_applied == "MARK_DEGRADED"
        assert "Blur detected" in result.decision_reason

    def test_fog_haze_contrast_restoration(self):
        # Simulate fog by adding a high ambient gray offset and low contrast
        frame = np.full((320, 480, 3), 160, dtype=np.uint8)
        # Small faint variations
        cv2.circle(frame, (150, 150), 60, (175, 175, 175), -1)
        cv2.rectangle(frame, (300, 100), (400, 250), (145, 145, 145), -1)

        analysis = self.analyzer.analyze(frame)
        assert analysis.condition == EnvironmentalCondition.FOG_HAZE

        result = self.enhancer.enhance(frame, analysis)
        assert result.transformation_applied == "HAZE_CONTRAST_RESTORE"
        assert "Haze restoration" in result.decision_reason
        # Enhanced frame contrast should exceed or equal input
        assert float(np.std(result.frame)) >= float(np.std(frame))
