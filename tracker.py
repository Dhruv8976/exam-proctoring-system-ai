import subprocess
import sys

try:
    from ultralytics import YOLO
except ImportError:
    print("ultralytics not found. Installing via pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    from ultralytics import YOLO

import cv2
import numpy as np


# YOLOv8-Pose keypoint indices (COCO 17-point skeleton)
_NOSE       = 0
_LEFT_EYE   = 1
_RIGHT_EYE  = 2
_LEFT_EAR   = 3
_RIGHT_EAR  = 4


class HeadMovementTracker:
    """Head-pose tracker using YOLOv8 Pose keypoints.

    Detects facial landmarks (nose, eyes, ears) from the pose model and
    computes an approximate yaw (left/right) from the eye-to-ear symmetry.
    No mediapipe or Haar cascades required.

    Returns:
        "center"  – head oriented towards camera (OK)
        "away"    – head turned/tilted beyond threshold (alert)
        "no_face" – no person/face detected (treated as alert)
    """

    def __init__(
        self,
        model_name: str = "yolov8n-pose.pt",
        yaw_threshold: float = 0.35,
        device: str = "cpu",
    ):
        """
        Parameters
        ----------
        model_name:
            YOLOv8 pose model. "yolov8n-pose.pt" is the fastest nano variant.
        yaw_threshold:
            Symmetry ratio threshold [0, 1]. Lower = more sensitive.
            0.35 means the nose must be within 35% of centre between the ears.
        device:
            "cpu" or "cuda".
        """
        self.model = YOLO(model_name)
        self.yaw_threshold = yaw_threshold
        self.device = device

    def process(self, frame: np.ndarray) -> str:
        """Analyse *frame* and return head orientation status.

        Parameters
        ----------
        frame : np.ndarray
            BGR image from OpenCV.
        """
        results = self.model(frame, device=self.device, verbose=False)

        for result in results:
            if result.keypoints is None or len(result.keypoints.xy) == 0:
                continue

            for kp in result.keypoints.xy:
                # kp shape: (17, 2) — pixel (x, y) per keypoint
                nose      = kp[_NOSE]
                left_eye  = kp[_LEFT_EYE]
                right_eye = kp[_RIGHT_EYE]
                left_ear  = kp[_LEFT_EAR]
                right_ear = kp[_RIGHT_EAR]

                # Skip if key points are missing (zeros = not detected)
                if self._is_zero(nose):
                    continue

                # ---- Yaw estimation via ear-nose symmetry -----------------
                # Use whichever ears are visible for robustness.
                status = self._estimate_direction(
                    nose, left_eye, right_eye, left_ear, right_ear
                )
                return status  # use the first detected person only

        return "no_face"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_zero(pt: np.ndarray) -> bool:
        return float(pt[0]) == 0.0 and float(pt[1]) == 0.0

    def _estimate_direction(self, nose, left_eye, right_eye, left_ear, right_ear) -> str:
        """Estimate head direction from facial keypoints."""
        nx = float(nose[0])

        # ---- Yaw (left/right turn) ----------------------------------------
        # Compute the ratio of (nose_x - left_ear_x) / (right_ear_x - left_ear_x)
        # For a frontal face this should be ~0.5.
        lx = float(left_ear[0])
        rx = float(right_ear[0])

        if not self._is_zero(left_ear) and not self._is_zero(right_ear) and (rx - lx) > 1e-3:
            ratio = (nx - lx) / (rx - lx)
            # ratio ~ 0.5 means looking straight, <0.15 or >0.85 means turned hard
            if ratio < (0.5 - self.yaw_threshold) or ratio > (0.5 + self.yaw_threshold):
                return "away"

        elif not self._is_zero(left_eye) and not self._is_zero(right_eye):
            # Fallback: use eye centres to check horizontal symmetry
            lex = float(left_eye[0])
            rex = float(right_eye[0])
            mid_eye_x = (lex + rex) / 2.0
            span = abs(rex - lex)
            if span > 1e-3 and abs(nx - mid_eye_x) / span > self.yaw_threshold:
                return "away"

        return "center"
