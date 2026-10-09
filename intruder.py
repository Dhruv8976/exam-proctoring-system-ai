"""
Intruder Detection Module
─────────────────────────
Detects two kinds of intrusion events:

1. EXTRA PERSON  — a second (or more) body appears in the frame.
2. FACE MISMATCH — the face visible on camera no longer matches the
                   candidate registered at session start (someone swapped seats).

How face comparison works (no heavy ML libs required):
  - At registration we extract the face region from the frame and compute
    an ORB (Oriented FAST and Rotated BRIEF) descriptor set.
  - Each frame we extract the current face and match its descriptors against
    the stored reference using a Brute-Force matcher.
  - A low match ratio → the face has changed → FACE MISMATCH alert.

Snapshots are saved to  snapshots/<timestamp>_<event>.jpg  automatically.
"""

import os
import datetime
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    from ultralytics import YOLO


# ── tuneable knobs ────────────────────────────────────────────────────────────

# How many of the last N frames must show an intruder before we alert
INTRUDER_HISTORY   = 10
INTRUDER_MIN_HITS  = 6

# Minimum ORB-match ratio to consider the face "the same person" (0–1)
# Lower → stricter (more face-mismatch alerts)
FACE_MATCH_RATIO   = 0.35

# Top fraction of a person bounding box used as the "face region"
FACE_CROP_FRACTION = 0.32

SNAPSHOTS_DIR = "snapshots"


@dataclass
class IntruderResult:
    extra_person:   bool = False    # a second+ body detected
    face_mismatch:  bool = False    # registered face doesn't match current face
    snapshot_path:  Optional[str] = None  # path to saved snapshot (if any)
    person_count:   int = 0         # total persons detected this frame


class IntruderDetector:
    """
    Detects intruders and face substitution.

    Usage
    -----
    >>> detector = IntruderDetector()
    >>> detector.register_candidate(frame)   # call once at session start
    >>> result = detector.detect(frame)      # call every frame
    """

    def __init__(self, device: str = "cpu"):
        self.device = device
        # Use the object-detection model for person counting
        self._model = YOLO("yolov8n.pt")

        # ORB for face-descriptor matching
        self._orb = cv2.ORB_create(nfeatures=500)
        self._bf  = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

        # Candidate reference
        self._ref_descriptors: Optional[np.ndarray] = None
        self._ref_face_region: Optional[np.ndarray] = None  # stored for display

        # Temporal smoothing for extra-person detection
        self._extra_history: deque = deque(maxlen=INTRUDER_HISTORY)

        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

    # ── public API ────────────────────────────────────────────────────────────

    def register_candidate(self, frame: np.ndarray) -> bool:
        """Extract and store the candidate's face from *frame*.

        Returns True on success, False if no person is detected in the frame.
        Should be called once right after the session starts (give the candidate
        2–3 seconds to sit in front of the camera first).
        """
        boxes = self._detect_persons(frame)
        if not boxes:
            return False

        # Use the largest (closest) person as the candidate
        largest = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
        face    = self._crop_face(frame, largest)
        if face is None:
            return False

        _, desc = self._orb.detectAndCompute(face, None)
        if desc is None or len(desc) < 10:
            return False

        self._ref_descriptors = desc
        self._ref_face_region = face.copy()
        return True

    @property
    def is_registered(self) -> bool:
        return self._ref_descriptors is not None

    def detect(self, frame: np.ndarray, auto_save: bool = False) -> IntruderResult:
        """Analyse *frame* and return an IntruderResult."""
        result     = IntruderResult()
        boxes      = self._detect_persons(frame)
        result.person_count = len(boxes)

        # ── extra person check ────────────────────────────────────────────────
        self._extra_history.append(len(boxes) >= 2)
        if sum(self._extra_history) >= INTRUDER_MIN_HITS:
            result.extra_person = True

        # ── face mismatch check ───────────────────────────────────────────────
        if self._ref_descriptors is not None and boxes:
            largest  = max(boxes, key=lambda b: (b[2] - b[0]) * (b[3] - b[1]))
            cur_face = self._crop_face(frame, largest)
            if cur_face is not None:
                _, cur_desc = self._orb.detectAndCompute(cur_face, None)
                if cur_desc is not None and len(cur_desc) >= 10:
                    ratio = self._match_ratio(self._ref_descriptors, cur_desc)
                    if ratio < FACE_MATCH_RATIO:
                        result.face_mismatch = True

        # ── save snapshot on any alert (if auto_save requested) ───────────────
        if auto_save and (result.extra_person or result.face_mismatch):
            result.snapshot_path = self._save_snapshot(frame, result)

        return result

    # ── internal helpers ──────────────────────────────────────────────────────

    def _detect_persons(self, frame: np.ndarray):
        """Return list of (x1, y1, x2, y2) bounding boxes for all persons."""
        results = self._model(frame, device=self.device, verbose=False,
                              conf=0.45, classes=[0])   # class 0 = person
        boxes = []
        for result in results:
            for box in result.boxes:
                boxes.append(tuple(map(int, box.xyxy[0].tolist())))
        return boxes

    def _crop_face(
        self, frame: np.ndarray, box: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        """Return the face region (top portion) of a person bounding box."""
        x1, y1, x2, y2 = box
        face_h = int((y2 - y1) * FACE_CROP_FRACTION)
        if face_h < 20:
            return None
        face = frame[y1: y1 + face_h, x1: x2]
        if face.size == 0:
            return None
        gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
        return cv2.resize(gray, (128, 64))

    def _match_ratio(
        self,
        desc1: np.ndarray,
        desc2: np.ndarray,
        k: int = 2,
    ) -> float:
        """Return fraction of good ORB matches (Lowe's ratio test)."""
        if len(desc1) < k or len(desc2) < k:
            return 0.0
        try:
            matches = self._bf.knnMatch(desc1, desc2, k=k)
        except cv2.error:
            return 0.0
        good = [m for m, n in matches if m.distance < 0.75 * n.distance]
        return len(good) / max(len(desc1), len(desc2))

    def _save_snapshot(self, frame: np.ndarray, result: IntruderResult) -> str:
        ts    = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        tag   = "extra_person" if result.extra_person else "face_mismatch"
        path  = os.path.join(SNAPSHOTS_DIR, f"{ts}_{tag}.jpg")
        # Draw a red border on the snapshot so it's clearly marked
        bordered = frame.copy()
        cv2.rectangle(bordered, (0, 0),
                      (bordered.shape[1] - 1, bordered.shape[0] - 1),
                      (0, 0, 220), 8)
        cv2.putText(bordered, f"INTRUDER ALERT — {tag.upper().replace('_', ' ')}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 220), 2)
        cv2.imwrite(path, bordered)
        return path
