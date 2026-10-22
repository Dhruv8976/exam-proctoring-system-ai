# Note:  I have also used AI to boost Project and its efficiency.


# Exam Proctoring System AI

An AI-powered exam proctoring tool that uses your webcam to:

- 🔍 **Detect prohibited objects** - cell phones, books, laptops, cheats (via YOLOv8)
- 👤 **Track head movement** - alerts when the candidate looks away from the screen (via YOLOv8 Pose)

---

## Requirements

- **Python 3.10 OR Higher** 
- A working webcam / camera device.

---



## Setup (first time only)

### Step 1 - Clone or download the project

 ```clone project```

### Step 2 - Create a virtual environment

Open **Command Prompt** or **PowerShell** in the project folder and run:
```cmd
python -m venv .venv
```

### Step 3 - Activate the virtual environment

**Command Prompt:**
```cmd
.venv\Scripts\activate.bat
```

**PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

You should see `(.venv)` appear at the start of your prompt. ✅


### Step 4 - Install all dependencies

```cmd
pip install -r requirements.txt
```

This installs:
- `opencv-python` - webcam capture and image processing
- `ultralytics` - YOLOv8 object detection and pose estimation
- `numpy`, `pillow` - supporting libraries

> **Note:** On first run, two small models will be auto-downloaded:
> - `yolov8n.pt` (~6 MB) - object detection
> - `yolov8n-pose.pt` (~6 MB) - head pose / landmark detection

---

## Running the app

Make sure the virtual environment is **active** (`(.venv)` shows in prompt), then:

```cmd
python app.py
```

A modern **AI Exam Proctoring Command Center** window will open.

### Command Center Features:
- 🖥️ **Sci-Fi HUD Overlays**: Live telemetry bar, tactical corner brackets, and perimeter hazard flash alerts.
- 📊 **Exam Integrity Index**: Real-time 0–100% compliance trust meter dynamically weighted against anomalies.
- 🚨 **Multi-Level Threat Radar**: Real-time threat classification (`NOMINAL`, `CAUTION`, `ELEVATED`, `CRITICAL`).
- 📸 **Proctor-Exclusive Evidence Archival**: Evidence snapshots are captured silently on security infractions or on-demand by proctors, and are archived exclusively into the Admin Evidence Vault.
- 🔊 **Admin Audio Dispatch & Alert System**: Audio controls are strictly managed by proctors via the Admin Panel; candidates cannot mute warnings. Admin can sound real-time sirens and chimes across candidate sessions on demand.
- ⛶ **Fullscreen Kiosk Mode**: Press `F11` for complete monitoring immersion.

### Hotkeys:
| Key | Action |
|-----|--------|
| **`Space`** | Start / Stop Monitoring Session |
| **`F10`** | Open Admin Control Panel |
| **`F11`** | Toggle Fullscreen Command Center Mode |
| **`C`** | Clear Security Event Stream |
| **`Esc`** | Exit Fullscreen Mode |

---

## 🔐 Admin Control Console

The system includes a dedicated **Admin Control Panel** with restricted proctor authentication:

- **Default ID:** `admin`
- **Default Password:** `admin`
- You can change it from [`config.json`](config.json) or from admin panel.


### Launching the Admin Panel:
- **From within the app:** Click the **`🔐 Admin Panel`** button in the top header or press **`F10`**.
- **Standalone launch:** Run directly from terminal:
  ```powershell
  python admin.py
  ```

### Admin Console Capabilities:
1. **📢 Candidate Audio & Directives Dispatch**: Master audio enable/silence switch, live sound directives (`Warning Chime`, `Danger Beep`, `Breach Siren`), and on-demand **`📸 Snap Candidate`** button transmitted instantly to active sessions.
2. **📸 Evidence Vault & Remote Capture**: Inspect breach evidence snapshots, review metadata, open full images, delete records, and capture live candidate frames on demand.
3. **📊 Session Audit Logs**: Browse all historical session CSVs, calculate violation metrics, view detailed tabular event streams, and open/delete logs.
4. **⚙️ AI Sensitivity & Rules Tuning**: Adjust model confidence thresholds for cell phones, books, and laptops, customize head yaw gaze sensitivity, debounce frames, and penalty point weights.
5. **🛡️ Security & Account Settings**: Update administrator password and view system diagnostics and storage health.

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

Or double-click **`run.bat`** - it activates the venv and launches the app automatically.

---

## Project structure

```
exam-proctoring-system-ai/
│   app.py              # Main Entry point - Command Center, webcam loop, alerts
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
| `ValueError: Unrecognized response` (YOLOv5 hub) | Fixed - the project now uses YOLOv8 via `ultralytics` directly |
| Webcam not opening | Check that no other app is using the camera; change `cv2.VideoCapture(0)` index in `app.py` if you have multiple cameras |

---

### NOTE: THIS README FILE IS ALSO ENHANCED WITH AI SO THAT I CAN MAKE MY WORK MORE CLEAR.


## License

MIT - see [`LICENSE`](LICENSE)
