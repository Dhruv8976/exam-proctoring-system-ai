"""
Exam Proctoring System — Minimalist AI Monitor
Built with Tkinter + PIL + OpenCV + YOLOv8
"""

import tkinter as tk
from tkinter import font as tkfont, messagebox
import threading
import time
import datetime
import csv
import os
import sys
import subprocess
import platform

# ── Enable High-DPI Awareness on Windows (Razor-Sharp UI) ─────────────────────
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

try:
    import cv2
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2

from PIL import Image, ImageTk, ImageDraw

from detection import ObjectDetector
from tracker   import HeadMovementTracker
from intruder  import IntruderDetector
from config    import load_config

# ── Minimalist Theme Palette ──────────────────────────────────────────────────
BG          = "#0d1117"   # Minimalist deep matte neutral dark
PANEL       = "#161b22"   # Elevated card surface
PANEL_ALT   = "#21262d"   # Secondary container / badge background
BORDER      = "#30363d"   # Crisp hairline 1px border
BORDER_LGT  = "#484f58"   # Subtle hover / active border
ACCENT      = "#3b82f6"   # Clean primary blue
CYAN        = "#60a5fa"   # Soft slate-blue secondary
DANGER      = "#f85149"   # Muted clean red
SUCCESS     = "#3fb950"   # Clean muted emerald green
WARNING     = "#d29922"   # Muted amber gold
INTRUDER    = "#a371f7"   # Clean muted violet
TEXT        = "#f0f6fc"   # Crisp readable white
TEXT_MUTED  = "#8b949e"   # Calm neutral secondary slate
MUTED       = "#6e7681"   # Neutral tertiary / disabled

# OpenCV BGR Color Equivalents
BGR_BLUE     = (246, 130, 59)
BGR_EMERALD  = (80, 185, 63)
BGR_CRIMSON  = (73, 81, 248)
BGR_AMBER    = (34, 153, 210)
BGR_VIOLET   = (247, 113, 163)
BGR_DARK     = (23, 17, 13)
BGR_WHITE    = (252, 246, 240)


# ── Audio Feedback System ─────────────────────────────────────────────────────
class SoundFX:
    """Non-blocking audio feedback with rate limiting and admin override."""
    def __init__(self):
        self.enabled = True
        self._last_alert = 0.0

    def play(self, sound_type: str, force: bool = False):
        if platform.system() != "Windows":
            return
        if not self.enabled and not force:
            return
        now = time.time()
        if not force and sound_type in ("warning", "danger", "siren") and (now - self._last_alert < 2.5):
            return
        if sound_type in ("warning", "danger", "siren"):
            self._last_alert = now

        def _worker():
            try:
                import winsound
                if sound_type == "start":
                    winsound.Beep(880, 70)
                    winsound.Beep(1174, 100)
                elif sound_type == "stop":
                    winsound.Beep(987, 70)
                    winsound.Beep(659, 100)
                elif sound_type == "warning":
                    winsound.Beep(750, 120)
                elif sound_type == "danger":
                    winsound.Beep(500, 90)
                    winsound.Beep(380, 150)
                elif sound_type == "siren":
                    for _ in range(3):
                        winsound.Beep(950, 100)
                        winsound.Beep(620, 100)
                elif sound_type == "snapshot":
                    winsound.Beep(1400, 50)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()


# ── Clean Minimalist Computer Vision Render Helpers ───────────────────────────
def draw_clean_bbox(frame, pt1, pt2, label, color):
    """Draw a clean, crisp bounding box with an elegant minimalist label."""
    x1, y1 = int(pt1[0]), int(pt1[1])
    x2, y2 = int(pt2[0]), int(pt2[1])
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    tag_y = max(y1, h + 8)
    cv2.rectangle(frame, (x1, tag_y - h - 6), (x1 + w + 10, tag_y + 2), color, -1)
    cv2.putText(frame, label, (x1 + 5, tag_y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)


def draw_clean_alerts(frame, alerts):
    """Draw a clean, subtle status indicator at top-left of feed when infractions occur."""
    if not alerts:
        return
    text, color = alerts[0]
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
    x = 14
    y = 14
    cv2.rectangle(frame, (x, y), (x + w + 30, y + h + 10), (22, 27, 34), -1)
    cv2.rectangle(frame, (x, y), (x + w + 30, y + h + 10), (48, 54, 61), 1)
    cv2.circle(frame, (x + 10, y + h // 2 + 5), 4, color, -1)
    cv2.putText(frame, text, (x + 22, y + h + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 246, 252), 1, cv2.LINE_AA)


# ── Main Application Window ───────────────────────────────────────────────────
class ProctoringApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ProctorAI — Exam Proctoring System")
        self.configure(bg=BG)
        self.geometry("1180x800")
        self.minsize(1040, 700)
        self.resizable(True, True)

        # State Variables
        self.running                = False
        self.session_start          = None
        self.violation_count        = 0
        self.intruder_count         = 0
        self.integrity_score        = 100
        self.is_fullscreen          = False
        self.latest_snapshot_path   = None
        self.fps                    = 0.0
        self.frame_count            = 0
        self.last_fps_time          = time.time()
        self.cap                    = None
        self.thread                 = None
        self._intruder_detector     = None

        self.sound = SoundFX()
        self.last_audio_trigger     = time.time()
        self.last_snapshot_trigger  = time.time()

        self._build_fonts()
        self._build_layout()
        self._init_log_file()
        self._bind_shortcuts()
        self.after(500, self._sync_admin_commands)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    def _build_fonts(self):
        self.font_brand   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_title   = tkfont.Font(family="Segoe UI", size=12, weight="bold")
        self.font_heading = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_subhead = tkfont.Font(family="Segoe UI", size=9,  weight="bold")
        self.font_body    = tkfont.Font(family="Segoe UI", size=9)
        self.font_small   = tkfont.Font(family="Segoe UI", size=8)
        self.font_mono    = tkfont.Font(family="Consolas", size=9)
        self.font_stat    = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.font_badge   = tkfont.Font(family="Segoe UI", size=8,  weight="bold")

    # ── Keyboard Shortcuts ────────────────────────────────────────────────────
    def _bind_shortcuts(self):
        self.bind("<space>",  lambda e: self._toggle_session())
        self.bind("<F11>",    lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.bind("<F10>",    lambda e: self._open_admin_panel())
        self.bind("<c>",      lambda e: self._clear_log())
        self.bind("<C>",      lambda e: self._clear_log())

    # ── UI Builder ────────────────────────────────────────────────────
    def _build_layout(self):
        # 1. Top Header Bar
        header = tk.Frame(self, bg=PANEL, height=54, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Header Left: Clean Minimalist Brand
        hdr_left = tk.Frame(header, bg=PANEL)
        hdr_left.pack(side="left", padx=16, pady=6)

        title_box = tk.Frame(hdr_left, bg=PANEL)
        title_box.pack(side="left")
        tk.Label(title_box, text="ProctorAI", bg=PANEL, fg=TEXT, font=self.font_brand).pack(anchor="w")
        tk.Label(title_box, text="Automated Session Integrity System", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w")

        # Header Center: Clean Session Status Pill
        hdr_mid = tk.Frame(header, bg=PANEL)
        hdr_mid.pack(side="left", expand=True)
        self.lbl_threat = tk.Label(
            hdr_mid, text="● Session: Ready",
            bg=PANEL_ALT, fg=SUCCESS, font=self.font_badge,
            padx=12, pady=4, highlightbackground=BORDER, highlightthickness=1
        )
        self.lbl_threat.pack()

        # Header Right: Utility Controls & Status Badge
        hdr_right = tk.Frame(header, bg=PANEL)
        hdr_right.pack(side="right", padx=16, pady=6)

        self.btn_admin = self._make_btn(
            hdr_right, "Admin Panel", self._open_admin_panel,
            bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_admin.pack(side="left", padx=4)

        self.btn_fs = self._make_btn(
            hdr_right, "Fullscreen", self._toggle_fullscreen,
            bg=PANEL_ALT, fg=TEXT_MUTED, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_fs.pack(side="left", padx=4)

        self.lbl_clock = tk.Label(hdr_right, text="", bg=PANEL, fg=TEXT_MUTED, font=self.font_small)
        self.lbl_clock.pack(side="left", padx=10)
        self._tick_clock()

        self.lbl_badge = tk.Label(hdr_right, text="Standby", bg=PANEL_ALT, fg=TEXT_MUTED,
                                  font=self.font_badge, padx=8, pady=3,
                                  highlightbackground=BORDER, highlightthickness=1)
        self.lbl_badge.pack(side="left", padx=(4, 0))

        # 2. Main Body Container
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left Column: Camera Feed & Action Controls
        left_col = tk.Frame(body, bg=BG)
        left_col.pack(side="left", fill="both", expand=True)
        self._build_camera_section(left_col)

        # Right Column: Intelligence & Telemetry Console
        right_col = tk.Frame(body, bg=BG, width=400)
        right_col.pack(side="right", fill="both", padx=(14, 0))
        right_col.pack_propagate(False)
        self._build_telemetry_section(right_col)

        # 3. Bottom Status Bar
        footer = tk.Frame(self, bg=PANEL, height=32, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        shortcuts_hint = "Shortcuts: [Space] Start/Stop Session   •   [F11] Fullscreen   •   [F10] Admin Panel"
        tk.Label(footer, text=shortcuts_hint, bg=PANEL, fg=MUTED, font=self.font_small).pack(side="left", padx=16)

        self.lbl_session = tk.Label(footer, text="Elapsed: --:--:--", bg=PANEL, fg=TEXT_MUTED, font=self.font_small)
        self.lbl_session.pack(side="right", padx=16)

    # ── Camera Feed Section ───────────────────────────────────────────────────
    def _build_camera_section(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        # Camera Card Header
        cam_hdr = tk.Frame(card, bg=PANEL, height=34)
        cam_hdr.pack(fill="x", padx=12, pady=(8, 4))
        cam_hdr.pack_propagate(False)

        tk.Label(cam_hdr, text="Camera Feed", bg=PANEL, fg=TEXT,
                 font=self.font_heading).pack(side="left")

        self.lbl_feed_status = tk.Label(
            cam_hdr, text="Inactive", bg=PANEL_ALT, fg=TEXT_MUTED,
            font=self.font_small, padx=8, pady=2,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.lbl_feed_status.pack(side="right")

        # Camera Display Canvas/Label
        feed_container = tk.Frame(card, bg="#000000", highlightbackground=BORDER, highlightthickness=1)
        feed_container.pack(fill="both", expand=True, padx=12, pady=4)

        self.lbl_feed = tk.Label(feed_container, bg="#0d1117")
        self.lbl_feed.pack(fill="both", expand=True)
        self._show_placeholder()

        # Action Toolbar below camera
        toolbar = tk.Frame(card, bg=PANEL, height=48)
        toolbar.pack(fill="x", padx=12, pady=8)
        toolbar.pack_propagate(False)

        self.btn_toggle = self._make_btn(
            toolbar, "▶   Start Session", self._toggle_session,
            bg=SUCCESS, fg="#ffffff", hover="#2ea043", px=18, py=6, font=self.font_heading
        )
        self.btn_toggle.pack(side="left", padx=(0, 10))

        lbl_notice = tk.Label(
            toolbar, text="Proctoring active session",
            bg=PANEL, fg=TEXT_MUTED, font=self.font_small
        )
        lbl_notice.pack(side="left")

    # ── Telemetry Section (Right Column) ──────────────────────────────────────
    def _build_telemetry_section(self, parent):
        # 1. Exam Integrity Meter Card
        card_integrity = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card_integrity.pack(fill="x", pady=(0, 8))

        int_hdr = tk.Frame(card_integrity, bg=PANEL)
        int_hdr.pack(fill="x", padx=12, pady=(8, 2))
        tk.Label(int_hdr, text="SESSION INTEGRITY", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(side="left")
        self.lbl_integrity_badge = tk.Label(int_hdr, text="100% Compliant", bg=PANEL_ALT, fg=SUCCESS,
                                            font=self.font_badge, padx=8, pady=2,
                                            highlightbackground=BORDER, highlightthickness=1)
        self.lbl_integrity_badge.pack(side="right")

        int_body = tk.Frame(card_integrity, bg=PANEL)
        int_body.pack(fill="x", padx=12, pady=(2, 6))

        self.lbl_integrity_val = tk.Label(int_body, text="100%", bg=PANEL, fg=SUCCESS, font=self.font_stat)
        self.lbl_integrity_val.pack(side="left")
        tk.Label(int_body, text="Real-time compliance rating\nAutomated anomaly assessment",
                 bg=PANEL, fg=TEXT_MUTED, font=self.font_small, justify="left").pack(side="left", padx=12)

        # Dynamic Canvas Integrity Bar
        self.canvas_integrity = tk.Canvas(card_integrity, height=6, bg="#21262d", highlightthickness=0)
        self.canvas_integrity.pack(fill="x", padx=12, pady=(0, 10))
        self.canvas_integrity.bind("<Configure>", lambda e: self._draw_integrity_bar(self.integrity_score, SUCCESS))

        # 2. Metric Tiles Row (Violations, Intruders, Duration)
        card_stats = tk.Frame(parent, bg=BG)
        card_stats.pack(fill="x", pady=(0, 8))

        self.box_violations = self._create_metric_tile(card_stats, "VIOLATIONS", "0", DANGER, "Objects / Gaze")
        self.box_violations.pack(side="left", fill="both", expand=True, padx=(0, 4))

        self.box_intruders = self._create_metric_tile(card_stats, "EXTRA PERSONS", "0", INTRUDER, "Multi-Person")
        self.box_intruders.pack(side="left", fill="both", expand=True, padx=2)

        self.box_uptime = self._create_metric_tile(card_stats, "DURATION", "00:00", TEXT, "Session Time")
        self.box_uptime.pack(side="right", fill="both", expand=True, padx=(4, 0))

        # 3. Detection Sensors
        card_sensors = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card_sensors.pack(fill="x", pady=(0, 8))

        tk.Label(card_sensors, text="DETECTION SENSORS", bg=PANEL, fg=TEXT_MUTED,
                 font=self.font_small).pack(anchor="w", padx=12, pady=(8, 4))

        self.status_head     = self._create_sensor_row(card_sensors, "Head Orientation", "Looking Forward", SUCCESS)
        self.status_obj      = self._create_sensor_row(card_sensors, "Prohibited Items", "None Detected", SUCCESS)
        self.status_people   = self._create_sensor_row(card_sensors, "Candidate Count", "1 Detected", SUCCESS)
        self.status_intruder = self._create_sensor_row(card_sensors, "Secondary Persons", "Clear", SUCCESS)
        tk.Frame(card_sensors, bg=PANEL, height=6).pack()

        # 4. Activity Log Stream
        card_log = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card_log.pack(fill="both", expand=True)

        log_hdr = tk.Frame(card_log, bg=PANEL)
        log_hdr.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(log_hdr, text="ACTIVITY LOG", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(side="left")
        self._make_btn(
            log_hdr, "Clear", self._clear_log,
            bg=PANEL_ALT, fg=MUTED, hover=BORDER_LGT, px=8, py=2, font=self.font_small
        ).pack(side="right")

        self.log_text = tk.Text(
            card_log, bg="#0d1117", fg=TEXT, insertbackground=TEXT,
            font=self.font_mono, relief="flat", wrap="word",
            state="disabled", padx=10, pady=6, highlightbackground=BORDER, highlightthickness=1
        )
        self.log_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self.log_text.tag_config("danger",   foreground=DANGER)
        self.log_text.tag_config("intruder", foreground=INTRUDER)
        self.log_text.tag_config("warning",  foreground=WARNING)
        self.log_text.tag_config("ok",       foreground=SUCCESS)
        self.log_text.tag_config("info",     foreground=CYAN)
        self.log_text.tag_config("muted",    foreground=MUTED)

    # ── Custom Component Helpers ──────────────────────────────────────────────
    def _make_btn(self, parent, text, command, bg, fg, hover, px=10, py=4, font=None):
        if font is None:
            font = self.font_subhead
        btn = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=hover, activeforeground="white",
            font=font, relief="flat", padx=px, pady=py, cursor="hand2", bd=0,
            highlightbackground=BORDER, highlightthickness=1
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    def _create_metric_tile(self, parent, label, val, color, sub):
        box = tk.Frame(parent, bg=PANEL, padx=10, pady=8, highlightbackground=BORDER, highlightthickness=1)
        tk.Label(box, text=label, bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w")
        lbl_val = tk.Label(box, text=val, bg=PANEL, fg=color, font=self.font_stat)
        lbl_val.pack(anchor="w", pady=(1, 2))
        tk.Label(box, text=sub, bg=PANEL, fg=MUTED, font=self.font_small).pack(anchor="w")
        box._val_label = lbl_val
        return box

    def _create_sensor_row(self, parent, label, default_status, default_color):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=12, pady=3)
        tk.Label(row, text=label, bg=PANEL, fg=TEXT, font=self.font_body, width=18, anchor="w").pack(side="left")

        dot = tk.Label(row, text="●", bg=PANEL, fg=default_color, font=self.font_body)
        dot.pack(side="left", padx=(0, 4))

        pill = tk.Label(
            row, text=f" {default_status} ", bg=PANEL_ALT, fg=default_color,
            font=self.font_small, padx=6, pady=2,
            highlightbackground=BORDER, highlightthickness=1
        )
        pill.pack(side="left")
        return {"dot": dot, "pill": pill}

    # ── Minimalist Standby Graphic ────────────────────────────────────────────
    def _show_placeholder(self):
        w, h = 640, 480
        ph = Image.new("RGB", (w, h), color=(13, 17, 23))
        draw = ImageDraw.Draw(ph)
        cx, cy = w // 2, h // 2 - 20

        # Minimalist camera line glyph
        bw, bh = 76, 50
        bx1, by1 = cx - bw // 2, cy - bh // 2
        bx2, by2 = cx + bw // 2, cy + bh // 2
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, outline=(48, 54, 61), width=2, fill=(22, 27, 34))

        # Top bump
        tw, th = 22, 7
        draw.rounded_rectangle([cx - tw // 2, by1 - th + 2, cx + tw // 2, by1 + 2], radius=3, outline=(48, 54, 61), width=2, fill=(22, 27, 34))

        # Center Lens
        lr = 16
        draw.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], outline=(48, 54, 61), width=2, fill=(16, 20, 27))
        # Subtle lens dot
        ilr = 6
        draw.ellipse([cx - ilr, cy - ilr, cx + ilr, cy + ilr], fill=(59, 130, 246))

        # Clean minimalist typography
        draw.text((cx - 56, cy + 44), "Camera Inactive", fill=(240, 246, 252))
        draw.text((cx - 108, cy + 68), "Click Start Session to begin monitoring", fill=(139, 148, 158))

        imgtk = ImageTk.PhotoImage(ph)
        self.lbl_feed.configure(image=imgtk)
        self.lbl_feed.imgtk = imgtk

    # ── Status & Integrity Bar Updates ────────────────────────────────────────
    def _draw_integrity_bar(self, score, color):
        self.canvas_integrity.delete("all")
        w = self.canvas_integrity.winfo_width()
        if w <= 1:
            w = 340
        h = 6
        fill_w = max(0, min(w, int(w * (score / 100.0))))

        self.canvas_integrity.create_rectangle(0, 0, w, h, fill="#21262d", width=0)
        if fill_w > 0:
            self.canvas_integrity.create_rectangle(0, 0, fill_w, h, fill=color, width=0)

    def _update_integrity(self):
        penalty = (self.violation_count * 2) + (self.intruder_count * 10)
        self.integrity_score = max(0, 100 - penalty)
        self.lbl_integrity_val.configure(text=f"{self.integrity_score}%")

        if self.integrity_score >= 90:
            color = SUCCESS
            status = "100% Compliant" if self.integrity_score == 100 else f"{self.integrity_score}% Compliant"
        elif self.integrity_score >= 70:
            color = WARNING
            status = f"{self.integrity_score}% Attention"
        else:
            color = DANGER
            status = f"{self.integrity_score}% Review"

        self.lbl_integrity_val.configure(fg=color)
        self.lbl_integrity_badge.configure(text=status, fg=color)
        self._draw_integrity_bar(self.integrity_score, color)

    def _update_threat_ui(self, threat_title, color):
        self.lbl_threat.configure(text=f"● Session: {threat_title}", fg=color)

    def _set_status(self, widget_dict, text, color):
        widget_dict["dot"].configure(fg=color)
        widget_dict["pill"].configure(text=f" {text} ", fg=color)

    def _tick_clock(self):
        self.lbl_clock.configure(
            text=datetime.datetime.now().strftime("%a, %d %b %Y  •  %H:%M:%S")
        )
        self.after(1000, self._tick_clock)

    def _append_log(self, msg, tag="muted"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {msg}\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        self._append_log("Log cleared by operator.", "info")

    def _init_log_file(self):
        os.makedirs("logs", exist_ok=True)
        self._log_path = os.path.join(
            "logs",
            datetime.datetime.now().strftime("session_%Y%m%d_%H%M%S.csv"),
        )

    def _write_log_csv(self, event_type, detail):
        ts = datetime.datetime.now().isoformat()
        with open(self._log_path, "a", newline="") as f:
            csv.writer(f).writerow([ts, event_type, detail])

    def _update_snapshot_preview(self, path, title):
        self.latest_snapshot_path = path

    def _open_latest_snapshot(self):
        messagebox.showinfo("Access Restricted", "Evidence inspection is restricted exclusively to the Proctor Admin Console.")

    def _sync_admin_commands(self):
        """Poll config.json to synchronize audio state, alarms, and remote snapshot requests."""
        try:
            cfg = load_config()
            admin_audio_enabled = cfg.get("sound_alerts", True)

            if self.sound.enabled != admin_audio_enabled:
                self.sound.enabled = admin_audio_enabled

            # Check for real-time remote audio directive
            remote_trigger = float(cfg.get("remote_audio_trigger", 0.0))
            if remote_trigger > self.last_audio_trigger:
                self.last_audio_trigger = remote_trigger
                snd_type = cfg.get("remote_audio_type", "warning")
                self.sound.play(snd_type, force=True)
                tag = "danger" if snd_type in ("siren", "danger") else "warning"
                self._append_log("⚠ Proctor Alert: Compliance check requested.", tag)

            # Check for real-time remote snapshot capture directive
            remote_snap = float(cfg.get("remote_snapshot_trigger", 0.0))
            if remote_snap > self.last_snapshot_trigger:
                self.last_snapshot_trigger = remote_snap
                self._silent_capture_frame()

        except Exception:
            pass
        finally:
            self.after(600, self._sync_admin_commands)

    def _silent_capture_frame(self):
        """Silently capture candidate frame for evidence archival."""
        if not self.running or self.cap is None:
            return
        ret, frame = self.cap.read()
        if not ret:
            return
        os.makedirs("snapshots", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("snapshots", f"evidence_{ts}.jpg")
        cv2.imwrite(path, frame)
        self._write_log_csv("ADMIN_REMOTE_SNAPSHOT", path)

    def _toggle_sound(self):
        messagebox.showinfo("Audio Control Restricted", "Audio alarms are managed exclusively by the Exam Administrator.")

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.attributes("-fullscreen", self.is_fullscreen)
        if self.is_fullscreen:
            self.btn_fs.configure(text="Windowed")
        else:
            self.btn_fs.configure(text="Fullscreen")

    def _exit_fullscreen(self):
        if self.is_fullscreen:
            self.is_fullscreen = False
            self.attributes("-fullscreen", False)
            self.btn_fs.configure(text="Fullscreen")

    def _take_manual_snapshot(self):
        messagebox.showinfo("Access Restricted", "Evidence snapshots are managed exclusively by the Exam Administrator.")

    def _open_snapshots_folder(self):
        messagebox.showinfo("Access Restricted", "Evidence Vault is restricted exclusively to the Proctor Admin Console.")

    def _open_admin_panel(self):
        """Launch the Admin Control Console."""
        try:
            admin_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.py")
            subprocess.Popen([sys.executable, admin_script])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch Admin Console: {e}")

    # ── Session Lifecycle ─────────────────────────────────────────────────────
    def _toggle_session(self):
        if self.running:
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._append_log("Failed to open camera. Check device connection.", "danger")
            self.sound.play("danger")
            return

        self.running             = True
        self.session_start       = time.time()
        self.violation_count     = 0
        self.intruder_count      = 0
        self.integrity_score     = 100
        self._intruder_detector  = IntruderDetector()

        self.box_violations._val_label.configure(text="0")
        self.box_intruders._val_label.configure(text="0")
        self._update_integrity()

        # Update button visuals
        self.btn_toggle.configure(text="⏹   Stop Session", bg=DANGER, activebackground="#da3633")
        self.lbl_badge.configure(text="Active", bg=PANEL_ALT, fg=SUCCESS)
        self.lbl_feed_status.configure(text="Live Feed", fg=SUCCESS)

        self._append_log("Exam proctoring session started.", "ok")
        self.sound.play("start")

        self.thread = threading.Thread(target=self._video_loop, daemon=True)
        self.thread.start()
        self._tick_uptime()

    def _stop_session(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

        self.btn_toggle.configure(text="▶   Start Session", bg=SUCCESS, activebackground="#2ea043")
        self.lbl_badge.configure(text="Standby", bg=PANEL_ALT, fg=TEXT_MUTED)
        self.lbl_feed_status.configure(text="Inactive", fg=TEXT_MUTED)
        self.lbl_threat.configure(text="● Session: Ready", fg=SUCCESS)

        for s in (self.status_head, self.status_obj, self.status_people, self.status_intruder):
            self._set_status(s, "—", MUTED)

        self._append_log(
            f"Session ended. Violations: {self.violation_count}  |  "
            f"Extra person events: {self.intruder_count}  |  "
            f"Integrity Score: {self.integrity_score}%", "muted"
        )
        self.sound.play("stop")
        self._show_placeholder()

    def _on_close(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.destroy()

    def _tick_uptime(self):
        if not self.running:
            self.lbl_session.configure(text="Elapsed: --:--:--")
            return
        elapsed = int(time.time() - self.session_start)
        h, rem  = divmod(elapsed, 3600)
        m, s    = divmod(rem, 60)
        time_str = f"{h:02d}:{m:02d}:{s:02d}"
        self.lbl_session.configure(text=f"Elapsed: {time_str}")
        self.box_uptime._val_label.configure(text=f"{h:02d}:{m:02d}")
        self.after(1000, self._tick_uptime)

    # ── Camera Pipeline Loop ──────────────────────────────────────────────────
    def _video_loop(self):
        detector = ObjectDetector()
        tracker  = HeadMovementTracker()
        intruder = self._intruder_detector

        while self.running:
            if not self.cap or not self.cap.isOpened():
                break

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue

            self.frame_count += 1
            now = time.time()
            if now - self.last_fps_time >= 1.0:
                self.fps = self.frame_count / (now - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = now

            hud_alerts           = []
            alert_this_frame     = False
            intruder_this_frame  = False

            # 1. Prohibited Object Detection
            detections, multiple_people = detector.detect(frame)

            if detections:
                alert_this_frame = True
                names = ", ".join(d[5] for d in detections)
                for x1, y1, x2, y2, conf, cls in detections:
                    draw_clean_bbox(frame, (x1, y1), (x2, y2), f"{cls.title()} {conf:.0%}", BGR_CRIMSON)

                hud_alerts.append((f"Item: {names.title()}", BGR_CRIMSON))
                self.after(0, self._append_log, f"Prohibited item detected: {names}", "danger")
                self.after(0, self._set_status, self.status_obj, names, DANGER)
                self._write_log_csv("OBJECT_DETECTED", names)
            else:
                self.after(0, self._set_status, self.status_obj, "None Detected", SUCCESS)

            # 2. Multiple Persons Check
            if multiple_people:
                alert_this_frame = True
                hud_alerts.append(("Multiple People", BGR_CRIMSON))
                self.after(0, self._set_status, self.status_people, "Multiple People", DANGER)
                self.after(0, self._append_log, "Multiple people visible in camera frame", "danger")
                self._write_log_csv("MULTIPLE_PEOPLE", "")
            else:
                self.after(0, self._set_status, self.status_people, "1 Person", SUCCESS)

            # 3. Head Orientation Tracking
            head_status = tracker.process(frame)

            if head_status == "away":
                alert_this_frame = True
                hud_alerts.append(("Looking Away", BGR_AMBER))
                self.after(0, self._set_status, self.status_head, "Looking Away", DANGER)
                self.after(0, self._append_log, "Candidate turned head away from screen", "warning")
                self._write_log_csv("HEAD_AWAY", "")
            elif head_status == "no_face":
                alert_this_frame = True
                hud_alerts.append(("No Face in Frame", BGR_AMBER))
                self.after(0, self._set_status, self.status_head, "No Face Detected", WARNING)
                self.after(0, self._append_log, "No candidate face visible in frame", "warning")
                self._write_log_csv("NO_FACE", "")
            else:
                self.after(0, self._set_status, self.status_head, "Facing Screen", SUCCESS)

            # 4. Intrusion Detection (Extra Person)
            intruder_result = intruder.detect(frame)

            if intruder_result.extra_person:
                intruder_this_frame = True
                hud_alerts.append(("Extra Person Detected", BGR_VIOLET))
                self.after(0, self._set_status, self.status_intruder, "Extra Person", INTRUDER)
                self.after(0, self._append_log, "Extra person detected in camera frame", "intruder")
                self._write_log_csv("INTRUDER_EXTRA_PERSON", intruder_result.snapshot_path or "")
            else:
                self.after(0, self._set_status, self.status_intruder, "Clear", SUCCESS)

            # Status resolution
            if intruder_this_frame:
                self.intruder_count += 1
                self.sound.play("danger")
                threat_title = "Multiple Persons"
                threat_hex   = INTRUDER
            elif alert_this_frame:
                self.violation_count += 1
                self.sound.play("warning")
                threat_title = "Flagged Anomaly"
                threat_hex   = WARNING
            else:
                threat_title = "Compliant"
                threat_hex   = SUCCESS

            # Update stats and integrity
            self.after(0, lambda v=self.violation_count: self.box_violations._val_label.configure(text=str(v)))
            self.after(0, lambda i=self.intruder_count: self.box_intruders._val_label.configure(text=str(i)))
            self.after(0, self._update_integrity)
            self.after(0, lambda t=threat_title, c=threat_hex: self._update_threat_ui(t, c))

            # 5. Render Minimalist Status Pill on Frame
            draw_clean_alerts(frame, hud_alerts)

            # Push frame to Tkinter
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb).resize((640, 480))
            imgtk = ImageTk.PhotoImage(img)

            def _update_feed(i=imgtk):
                if self.running:
                    self.lbl_feed.configure(image=i)
                    self.lbl_feed.imgtk = i

            self.after(0, _update_feed)

        self.after(0, self._stop_session)


if __name__ == "__main__":
    app = ProctoringApp()
    app.mainloop()
