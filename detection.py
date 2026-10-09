"""
Object detector using YOLOv8 (ultralytics).

Improvements over the basic version
────────────────────────────────────
* Per-class confidence thresholds (higher = fewer false positives).
* Temporal smoothing: a class must appear in at least MIN_HITS of the last
  HISTORY_LEN frames before we report it. This kills single-frame ghosts.
* Larger prohibited-object list (COCO classes + multi-person alert).
* NMS already handled by YOLOv8; we just post-filter.
"""

import subprocess
import sys
from collections import deque
from typing import Dict, List, Tuple

try:
    from ultralytics import YOLO
except ImportError:
    print("ultralytics not found – installing…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    from ultralytics import YOLO

import numpy as np


# ── Prohibited object classes (COCO labels) ───────────────────────────────────
# Each entry: class_name → minimum confidence to even consider the detection.
PROHIBITED: Dict[str, float] = {
    "cell phone":   0.55,   # phones — moderate threshold, common false positives
    "book":         0.65,   # books
    "laptop":       0.65,   # laptops / open screens
    "remote":       0.65,   # TV remotes (look like phones)
    "keyboard":     0.70,   # external keyboards
    "tv":           0.70,   # second screens / projectors
    "mouse":        0.72,   # computer mice (less common, raise threshold)
    "tablet":       0.60,   # tablets (not in COCO but future-proofs)
    "earphones":    0.60,   # earphones (not standard COCO – keep low)
    "headphones":   0.60,   # headphones
}

try:
    from config import load_config
    _cfg = load_config()
    PROHIBITED["cell phone"] = _cfg.get("threshold_phone", 0.55)
    PROHIBITED["book"]       = _cfg.get("threshold_book", 0.65)
    PROHIBITED["laptop"]     = _cfg.get("threshold_laptop", 0.65)
except Exception:
    pass

# Temporal-smoothing parameters
HISTORY_LEN = 10   # remember the last N frames per class
MIN_HITS    = 6    # class must appear in >= this many of the last N frames


class ObjectDetector:
    """YOLOv8-based detector with per-class confidence thresholds and
    temporal smoothing to minimise false positives."""

    def __init__(self, model_name: str = "yolov8s.pt", device: str = "cpu"):
        # yolov8s (small) is noticeably more accurate than nano for small objects
        self.model  = YOLO(model_name)
        self.device = device

        # Per-class sliding window of booleans (seen / not seen each frame)
        self._history: Dict[str, deque] = {
            cls: deque(maxlen=HISTORY_LEN) for cls in PROHIBITED
        }
        # Also track total person count for multi-person alert
        self._person_history: deque = deque(maxlen=HISTORY_LEN)

    @property
    def target_classes(self):
        return set(PROHIBITED.keys())

    def detect(
        self, frame: np.ndarray
    ) -> Tuple[List[Tuple[float, float, float, float, float, str]], bool]:
        """Run detection on one BGR frame.

        Returns
        -------
        detections : list of (x1, y1, x2, y2, confidence, class_name)
            Only *smoothed* detections (passed temporal filter).
        multiple_people : bool
            True if ≥2 people visible for several consecutive frames.
        """
        results = self.model(
            frame,
            device=self.device,
            verbose=False,
            conf=0.40,   # low raw threshold; per-class filtering below
            iou=0.45,    # NMS IoU threshold
        )

        # ── raw detections ────────────────────────────────────────────────────
        raw_seen: Dict[str, List[Tuple]] = {cls: [] for cls in PROHIBITED}
        person_count = 0

        for result in results:
            for box in result.boxes:
                cls_id     = int(box.cls[0])
                class_name = self.model.names[cls_id]
                conf       = float(box.conf[0])

                if class_name == "person":
                    person_count += 1
                    continue

                min_conf = PROHIBITED.get(class_name)
                if min_conf is None or conf < min_conf:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                raw_seen[class_name].append((x1, y1, x2, y2, conf, class_name))

        # ── update per-class history ──────────────────────────────────────────
        for cls, hits in raw_seen.items():
            self._history[cls].append(len(hits) > 0)

        self._person_history.append(person_count)

        # ── apply temporal filter ─────────────────────────────────────────────
        confirmed: List[Tuple] = []
        for cls, window in self._history.items():
            if sum(window) >= MIN_HITS:
                # Emit the best-confidence detection for this class this frame
                if raw_seen[cls]:
                    best = max(raw_seen[cls], key=lambda d: d[4])
                    confirmed.append(best)

        # Multi-person: flag if ≥2 people appear in most recent frames
        multiple_people = (
            len(self._person_history) >= MIN_HITS
            and sum(p >= 2 for p in self._person_history) >= MIN_HITS
        )

        return confirmed, multiple_people
