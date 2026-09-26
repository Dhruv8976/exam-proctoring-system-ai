import subprocess
import sys
from collections import deque
from typing import Tuple

try:
    from ultralytics import YOLO
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    from ultralytics import YOLO

import numpy as np

# COCO 17-point skeleton indices
_NOSE      = 0
_LEFT_EYE  = 1
_RIGHT_EYE = 2
_LEFT_EAR  = 3
_RIGHT_EAR = 4

# Minimum keypoint confidence to trust a landmark
KP_CONF_MIN = 0.40

# Debounce: require this many consecutive "away" frames before alerting
AWAY_FRAMES = 8

# Thresholds
YAW_THRESHOLD   = 0.30   # ear-nose-ear ratio deviation from 0.5
PITCH_THRESHOLD = 0.28   # eye-nose vertical ratio threshold


class HeadMovementTracker:
    """Tracks head orientation using YOLOv8 Pose keypoints with debouncing
    and keypoint confidence filtering to minimise false alerts."""

    def __init__(
        self,
        model_name: str = "yolov8n-pose.pt",
        device: str = "cpu",
    ):
        self.model  = YOLO(model_name)
        self.device = device

        # Sliding window of recent head-status values
        self._away_counter   = 0      # consecutive "away" frames
        self._center_counter = 0      # consecutive "center" frames

    # ── public API ────────────────────────────────────────────────────────────

    def process(self, frame: np.ndarray) -> str:
        """Analyse *frame* and return:
            "center"   – head facing screen (OK)
            "away"     – confirmed head turn (after debounce)
            "no_face"  – no person detected (after debounce)
        """
        results = self.model(frame, device=self.device, verbose=False)
        raw = self._raw_status(results)
        return self._debounce(raw)

    # ── internal ──────────────────────────────────────────────────────────────

    def _raw_status(self, results) -> str:
        """Single-frame status before debouncing."""
        for result in results:
            if result.keypoints is None or len(result.keypoints.xy) == 0:
                continue
            for i, kp_xy in enumerate(result.keypoints.xy):
                # Get per-keypoint confidence if available
                if result.keypoints.conf is not None:
                    kp_conf = result.keypoints.conf[i].tolist()
                else:
                    kp_conf = [1.0] * len(kp_xy)

                status = self._estimate(kp_xy, kp_conf)
                return status   # evaluate first (most prominent) person only

        return "no_face"

    def _debounce(self, raw: str) -> str:
        """Only escalate to "away" / "no_face" after AWAY_FRAMES consecutive
        raw "away" frames. Resets the counter as soon as we see "center"."""
        if raw in ("away", "no_face"):
            self._away_counter   += 1
            self._center_counter  = 0
        else:
            self._center_counter += 1
            self._away_counter    = 0

        if self._away_counter >= AWAY_FRAMES:
            return raw
        return "center"

    def _estimate(self, kp_xy, kp_conf) -> str:
        """Compute head direction from facial keypoints."""

        def pt(idx):
            """Return (x, y) if confidence is high enough, else None."""
            if idx >= len(kp_xy):
                return None
            if kp_conf[idx] < KP_CONF_MIN:
                return None
            x, y = float(kp_xy[idx][0]), float(kp_xy[idx][1])
            if x == 0.0 and y == 0.0:
                return None
            return x, y

        nose      = pt(_NOSE)
        left_eye  = pt(_LEFT_EYE)
        right_eye = pt(_RIGHT_EYE)
        left_ear  = pt(_LEFT_EAR)
        right_ear = pt(_RIGHT_EAR)

        if nose is None:
            return "no_face"

        # ── Yaw (left / right turn) ──────────────────────────────────────────
        if left_ear and right_ear:
            lx, rx, nx = left_ear[0], right_ear[0], nose[0]
            span = rx - lx
            if span > 10:
                ratio = (nx - lx) / span          # ~0.5 when facing forward
                if ratio < (0.5 - YAW_THRESHOLD) or ratio > (0.5 + YAW_THRESHOLD):
                    return "away"

        elif left_eye and right_eye:
            # Fallback: eye-centre symmetry when ears aren't visible
            eye_mid = (left_eye[0] + right_eye[0]) / 2
            eye_span = abs(right_eye[0] - left_eye[0])
            if eye_span > 10 and abs(nose[0] - eye_mid) / eye_span > YAW_THRESHOLD:
                return "away"

        # ── Pitch (looking up / down) ────────────────────────────────────────
        if left_eye and right_eye:
            eye_y   = (left_eye[1] + right_eye[1]) / 2
            eye_span = abs(right_eye[0] - left_eye[0])
            if eye_span > 10:
                vertical_ratio = (nose[1] - eye_y) / eye_span
                # Normal frontal: nose is ~0.7–1.2 × eye-span below the eyes
                if vertical_ratio < 0.20 or vertical_ratio > 1.8:
                    return "away"

        return "center"
