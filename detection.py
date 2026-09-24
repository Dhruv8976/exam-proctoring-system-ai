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
from typing import List, Tuple


class ObjectDetector:
    """YOLOv8 based object detector for prohibited items.

    Uses the `ultralytics` package which bundles YOLOv8 and handles model
    download automatically. Filters detections to a whitelist of COCO classes
    that are considered prohibited in an exam setting.
    """

    # COCO class names that are prohibited in an exam.
    target_classes = {"cell phone", "book", "laptop"}

    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        """Load a YOLOv8 model.

        Parameters
        ----------
        model_name:
            YOLOv8 model variant. "yolov8n.pt" is the nano (fastest) model.
            Use "yolov8s.pt" or "yolov8m.pt" for better accuracy.
        device:
            "cpu" or "cuda" (if GPU is available).
        """
        self.model = YOLO(model_name)
        self.device = device

    def detect(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float, str]]:
        """Run detection on a single BGR frame.

        Returns
        -------
        List of (x1, y1, x2, y2, confidence, class_name) tuples.
        Coordinates are in pixel space.
        """
        results = self.model(frame, device=self.device, verbose=False)
        detections = []
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                class_name = self.model.names[cls_id]
                if class_name in self.target_classes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    conf = float(box.conf[0])
                    detections.append((x1, y1, x2, y2, conf, class_name))
        return detections
