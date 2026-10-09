# Note:  I have also used ai to write some part of code.


# Exam Proctoring System AI

An AI-powered exam proctoring tool that uses your webcam to:

- 🔍 **Detect prohibited objects** — cell phones, books, laptops (via YOLOv8)
- 👤 **Track head movement** — alerts when the candidate looks away from the screen (via YOLOv8 Pose)

---

## Requirements

- **Python 3.10 – 3.14** (⚠️ Python 3.14 is NOT fully supported by all dependencies — use 3.11 or 3.12 for best compatibility)
- A working webcam

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

A clean, modern **AI Exam Proctoring System** window will open.

### System Features:
- 👁️ **Minimalist Monitoring Feed**: Clean webcam display with crisp, non-intrusive bounding boxes and status pills without distracting clutter or radar effects.
- 📊 **Session Integrity Meter**: Real-time compliance score dynamically weighted against detected anomalies.
- 👤 **Multiple Persons & Intruder Detection**: Flags multiple individuals or unauthorized persons present in the camera frame.
- 📱 **Prohibited Object Detection**: Detects cell phones, books, and laptops using YOLOv8 deep learning vision models.
- 👁️ **Head Pose & Gaze Tracking**: Tracks candidate face landmarks to identify when the user looks away from the screen.
- 📸 **Proctor-Exclusive Evidence Archival**: Silent frame captures on infractions and remote snapshot requests saved exclusively into the Admin Evidence Vault.
- 🔊 **Admin-Controlled Audio**: Audio alarms and chimes are managed exclusively by exam administrators from the Admin Panel; candidates cannot disable or tamper with alerts.
- ⛶ **Fullscreen Mode**: Press `F11` for focused proctoring.

### Hotkeys:
| Key | Action |
|-----|--------|
| **`Space`** | Start / Stop Monitoring Session |
| **`F10`** | Open Admin Control Panel |
| **`F11`** | Toggle Fullscreen Mode |
| **`C`** | Clear Activity Log |
| **`Esc`** | Exit Fullscreen Mode |

---

## 🔐 Admin Control Console

The system includes a dedicated **Admin Control Panel** with administrator authentication:

- **Default Username:** `admin`
- **Default Password:** `admin`

### Launching the Admin Panel:
- **From within the app:** Click the **`Admin Panel`** button in the top header or press **`F10`**.
- **Standalone launch:** Run directly from terminal:
  ```powershell
  python admin.py
  ```

### Admin Console Capabilities:
1. **Candidate Audio & Directives**: Master audio enable/silence switch and real-time remote audio directives (`Warning Chime`, `Danger Beep`, `Emergency Siren`).
2. **Evidence Vault & Remote Capture**: Inspect breach evidence snapshots, review metadata, open full images, delete records, and capture live candidate frames on demand.
3. **Session Audit Logs**: Browse historical session CSVs, calculate violation metrics, and view detailed tabular event streams.
4. **AI Sensitivity & Rules Tuning**: Adjust model confidence thresholds for cell phones, books, and laptops, customize head yaw gaze sensitivity, debounce frames, and penalty weights.
5. **Security & Diagnostics**: Update administrator credentials and inspect real-time system diagnostics.

---

## Quick start (after first-time setup)

Every time you want to run the proctoring system:

**Command Prompt:**
```cmd
cd {filepath}\activate.bat
python app.py
```
{filepath} represents your actual file path. replace it with your own.
example: C:\Users\Dhruv Yadev\Desktop\Projects\exam-proctoring-system-ai
.venv\Scripts\activate.bat

**PowerShell:**
```powershell
cd "{filepath}"
.\.venv\Scripts\Activate.ps1
python app.py
```
{filepath} = Your actual filepath. Example C:\Users\Dhruv Yadev\Desktop\Projects\exam-proctoring-system-ai

Or double-click **`run.bat`** — it activates the venv and launches the app automatically.

---

## Project structure

```
exam-proctoring-system-ai/
│   app.py              # Main Entry point — Command Center, webcam loop, alerts
│   admin.py            # Admin Control Console (ID: admin, Pass: admin)
│   config.py           # Configuration manager & persistence (config.json)
│   detection.py        # YOLOv8 object detector (cell phone, book, laptop)
│   tracker.py          # YOLOv8 Pose head-movement tracker
│   requirements.txt    # Python dependencies
│   setup.bat           # One-time setup script (creates venv + installs deps)
│   run.bat             # Launch script (activates venv + runs app)
│   README.md           # Documentation
│   LICENSE             # MIT License
```

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
