# Exam Proctoring System AI

An AI-powered exam proctoring tool that uses your webcam to:

- 🔍 **Detect prohibited objects** — cell phones, books, laptops (via YOLOv8)
- 👤 **Track head movement** — alerts when the candidate looks away from the screen (via YOLOv8 Pose)

---

## Requirements

- **Python 3.10 – 3.12** (⚠️ Python 3.14 is NOT fully supported by all dependencies — use 3.11 or 3.12 for best compatibility)
- A working webcam
- Windows (instructions below use PowerShell / Command Prompt)

---

## Setup (first time only)

### Step 1 — Clone or download the project

 ```clone project```

### Step 2 — Create a virtual environment

Open **Command Prompt** or **PowerShell** in the project folder and run:
```cmd
python -m venv .venv
```

### Step 3 — Activate the virtual environment

**Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` appear at the start of your prompt. ✅

### Step 4 — Fix OpenCV conflicts

`ultralytics` may install `opencv-python-headless` automatically. Remove it and install the full version:

```cmd
pip uninstall opencv-python-headless -y
pip install opencv-python
```

### Step 5 — Install all dependencies

```cmd
pip install -r requirements.txt
```

This installs:
- `opencv-python` — webcam capture and image processing
- `ultralytics` — YOLOv8 object detection and pose estimation
- `numpy`, `pillow` — supporting libraries

> **Note:** On first run, two small models will be auto-downloaded:
> - `yolov8n.pt` (~6 MB) — object detection
> - `yolov8n-pose.pt` (~6 MB) — head pose / landmark detection

---

## Running the app

Make sure the virtual environment is **active** (`(.venv)` shows in prompt), then:

```cmd
python app.py
```

A window named **"Proctoring"** will open showing the live webcam feed.

- 🔴 **Red box** around an object = prohibited item detected (alert printed in terminal)
- 🔴 **"Head away from screen!"** text = candidate looked away (alert printed in terminal)
- Press **`q`** to quit the app.

---

## Quick start (after first-time setup)

Every time you want to run the proctoring system:

**Command Prompt:**
```cmd
cd C:\Users\Dhruv Yadev\Desktop\Projects\exam-proctoring-system-ai
.venv\Scripts\activate.bat
python app.py
```

**PowerShell:**
```powershell
cd "C:\Users\Dhruv Yadev\Desktop\Projects\exam-proctoring-system-ai"
.\.venv\Scripts\Activate.ps1
python app.py
```

Or double-click **`run.bat`** — it activates the venv and launches the app automatically.

---

## Project structure

```
exam-proctoring-system-ai/
│   app.py              # Entry point — webcam loop, alerts
│   detection.py        # YOLOv8 object detector (cell phone, book, laptop)
│   tracker.py          # YOLOv8 Pose head-movement tracker
│   requirements.txt    # Python dependencies
│   setup.bat           # One-time setup script (creates venv + installs deps)
│   run.bat             # Launch script (activates venv + runs app)
│   README.md           # This file
│   LICENSE             # MIT License
```

---

## Customization

| What to change | Where | How |
|----------------|-------|-----|
| Add/remove prohibited objects | `detection.py` | Edit the `target_classes` set |
| Change head-turn sensitivity | `tracker.py` | Adjust `yaw_threshold` (default `0.35`; lower = more sensitive) |
| Use a larger/more accurate model | `detection.py` | Change `"yolov8n.pt"` → `"yolov8s.pt"` or `"yolov8m.pt"` |
| Use GPU instead of CPU | Both files | Change `device="cpu"` → `device="cuda"` |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'cv2'` | Make sure the venv is active and run `pip install opencv-python` |
| `ModuleNotFoundError: No module named 'torch'` | Run `pip install ultralytics` inside the active venv |
| `AttributeError: module 'cv2' has no attribute 'CascadeClassifier'` | Run `pip uninstall opencv-python-headless -y && pip install opencv-python` |
| `ValueError: Unrecognized response` (YOLOv5 hub) | Fixed — the project now uses YOLOv8 via `ultralytics` directly |
| Webcam not opening | Check that no other app is using the camera; change `cv2.VideoCapture(0)` index in `app.py` if you have multiple cameras |

---

## License

MIT — see [`LICENSE`](LICENSE)
