try:
    import cv2
except ImportError:
    import subprocess, sys
    print("OpenCV (cv2) not found. Attempting to install via pip...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2
import numpy as np
from detection import ObjectDetector
from tracker import HeadMovementTracker

def main():
    # Initialize video capture (webcam)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # Initialize detectors
    object_detector = ObjectDetector()
    head_tracker = HeadMovementTracker()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Detect foreign objects (e.g., phone) using YOLOv5 model
        detections = object_detector.detect(frame)
        for det in detections:
            # det: (x1, y1, x2, y2, confidence, class_name)
            x1, y1, x2, y2, conf, cls = det
            if cls in object_detector.target_classes:
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)
                cv2.putText(frame, f"{cls} {conf:.2f}", (int(x1), int(y1)-10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                print(f"Alert: Detected prohibited object '{cls}' with confidence {conf:.2f}")

        # Track head pose / movement using MediaPipe
        head_status = head_tracker.process(frame)
        if head_status == "away":
            cv2.putText(frame, "Head away from screen!", (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            print("Alert: Candidate looked away from screen")

        cv2.imshow('Proctoring', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
