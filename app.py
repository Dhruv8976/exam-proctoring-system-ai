"""
Exam Proctoring System — GUI
Built with tkinter (stdlib, no extra deps) + OpenCV for webcam.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
import datetime
import csv
import os

try:
    import cv2
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python"])
    import cv2

from PIL import Image, ImageTk

from detection import ObjectDetector
from tracker import HeadMovementTracker

# ─── Palette ──────────────────────────────────────────────────────────────────
BG         = "#0f1117"   # dark background
PANEL      = "#1a1d27"   # card background
ACCENT     = "#4f8ef7"   # blue accent
DANGER     = "#e74c3c"   # red alert
SUCCESS    = "#2ecc71"   # green OK
WARNING    = "#f39c12"   # yellow warning
TEXT       = "#e8eaf6"   # primary text
MUTED      = "#6c7a8d"   # secondary text
BORDER     = "#2a2d3e"   # card border


class ProctoringApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Proctoring System")
        self.configure(bg=BG)
        self.resizable(False, False)

        # ── state ──
        self.running        = False
        self.session_start  = None
        self.violation_count= 0
        self.cap            = None
        self.thread         = None

        self._build_fonts()
        self._build_layout()
        self._init_log_file()

        # Graceful close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── fonts ────────────────────────────────────────────────────────────────
    def _build_fonts(self):
        self.font_title   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_heading = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_body    = tkfont.Font(family="Segoe UI", size=9)
        self.font_mono    = tkfont.Font(family="Consolas",  size=8)
        self.font_stat    = tkfont.Font(family="Segoe UI",  size=22, weight="bold")
        self.font_label   = tkfont.Font(family="Segoe UI",  size=8)
        self.font_badge   = tkfont.Font(family="Segoe UI",  size=9, weight="bold")

    # ─── layout ───────────────────────────────────────────────────────────────
    def _build_layout(self):
        # ── top header ──
        header = tk.Frame(self, bg=PANEL, height=54)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        tk.Label(header, text="🎓", bg=PANEL, fg=ACCENT,
                 font=tkfont.Font(size=20)).pack(side="left", padx=14, pady=8)
        tk.Label(header, text="Exam Proctoring System", bg=PANEL, fg=TEXT,
                 font=self.font_title).pack(side="left", pady=8)

        self.lbl_clock = tk.Label(header, text="", bg=PANEL, fg=MUTED,
                                  font=self.font_body)
        self.lbl_clock.pack(side="right", padx=18)
        self._tick_clock()

        # Status badge
        self.badge_var = tk.StringVar(value="  STOPPED  ")
        self.badge_bg  = tk.StringVar(value=MUTED)
        self.lbl_badge = tk.Label(header, textvariable=self.badge_var,
                                  bg=MUTED, fg="white",
                                  font=self.font_badge, padx=8, pady=3)
        self.lbl_badge.pack(side="right", padx=10)

        # ── main body ──
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        # Left: camera feed
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        self._build_camera_panel(left)

        # Right: stats + alerts
        right = tk.Frame(body, bg=BG, width=300)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)
        self._build_stats_panel(right)
        self._build_status_panel(right)
        self._build_log_panel(right)

        # ── bottom bar ──
        bar = tk.Frame(self, bg=PANEL, height=52)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.btn_toggle = tk.Button(
            bar, text="▶  Start Session",
            bg=ACCENT, fg="white", activebackground="#3a6bd6",
            font=self.font_heading, relief="flat",
            padx=24, pady=6, cursor="hand2",
            command=self._toggle_session,
        )
        self.btn_toggle.pack(side="left", padx=14, pady=9)

        tk.Button(
            bar, text="🗑  Clear Log",
            bg=PANEL, fg=MUTED, activebackground=BORDER,
            font=self.font_body, relief="flat",
            padx=14, pady=6, cursor="hand2",
            command=self._clear_log,
        ).pack(side="left", padx=4, pady=9)

        self.lbl_session = tk.Label(bar, text="Session: --:--:--",
                                    bg=PANEL, fg=MUTED, font=self.font_body)
        self.lbl_session.pack(side="right", padx=18)

    def _build_camera_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="📷  Live Feed", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 0))

        self.lbl_feed = tk.Label(card, bg="#000000",
                                 width=640, height=480)
        self.lbl_feed.pack(padx=10, pady=(4, 10))

        # Placeholder text shown when stopped
        self._show_placeholder()

    def _build_stats_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="SESSION STATS", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 2))

        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_violations = self._stat_box(row, "VIOLATIONS", "0", DANGER)
        self.lbl_violations.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.lbl_uptime = self._stat_box(row, "UPTIME", "00:00", ACCENT)
        self.lbl_uptime.pack(side="right", expand=True, fill="x", padx=(4, 0))

    def _stat_box(self, parent, label, value, color):
        box = tk.Frame(parent, bg=BORDER, padx=10, pady=8)
        tk.Label(box, text=label, bg=BORDER, fg=MUTED,
                 font=self.font_label).pack(anchor="w")
        lbl = tk.Label(box, text=value, bg=BORDER, fg=color,
                       font=self.font_stat)
        lbl.pack(anchor="w")
        # Store reference so we can update later
        box._value_label = lbl
        return box

    def _build_status_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))

        tk.Label(card, text="DETECTION STATUS", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 4))

        self.status_head = self._status_row(card, "Head Position", "—")
        self.status_obj  = self._status_row(card, "Foreign Object", "—")

        tk.Frame(card, bg=PANEL, height=6).pack()

    def _status_row(self, parent, label, value):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                 font=self.font_body, width=16, anchor="w").pack(side="left")
        dot = tk.Label(row, text="●", bg=PANEL, fg=MUTED,
                       font=self.font_body)
        dot.pack(side="left", padx=4)
        lbl = tk.Label(row, text=value, bg=PANEL, fg=MUTED,
                       font=self.font_body, anchor="w")
        lbl.pack(side="left")
        return {"dot": dot, "label": lbl}

    def _build_log_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="ALERT LOG", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 4))

        self.log_text = tk.Text(
            card, bg=BG, fg=TEXT, insertbackground=TEXT,
            font=self.font_mono, relief="flat",
            wrap="word", state="disabled",
            padx=8, pady=4,
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Tag colours
        self.log_text.tag_config("danger",  foreground=DANGER)
        self.log_text.tag_config("warning", foreground=WARNING)
        self.log_text.tag_config("ok",      foreground=SUCCESS)
        self.log_text.tag_config("muted",   foreground=MUTED)

    # ─── helpers ──────────────────────────────────────────────────────────────
    def _show_placeholder(self):
        placeholder = Image.new("RGB", (640, 480), color=(15, 17, 23))
        # Draw simple centred text with PIL
        from PIL import ImageDraw
        draw = ImageDraw.Draw(placeholder)
        msg = "Camera feed will appear here\nPress  ▶ Start Session  to begin"
        draw.text((200, 220), msg, fill=(70, 80, 100))
        imgtk = ImageTk.PhotoImage(placeholder)
        self.lbl_feed.configure(image=imgtk)
        self.lbl_feed.imgtk = imgtk

    def _tick_clock(self):
        now = datetime.datetime.now().strftime("%A, %d %b %Y   %H:%M:%S")
        self.lbl_clock.configure(text=now)
        self.after(1000, self._tick_clock)

    def _set_badge(self, text, color):
        self.lbl_badge.configure(text=f"  {text}  ", bg=color)

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

    def _set_status(self, widget_dict, text, color):
        widget_dict["dot"].configure(fg=color)
        widget_dict["label"].configure(text=text, fg=color)

    def _update_violations(self):
        self.lbl_violations._value_label.configure(
            text=str(self.violation_count)
        )

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

    # ─── session control ──────────────────────────────────────────────────────
    def _toggle_session(self):
        if self.running:
            self._stop_session()
        else:
            self._start_session()

    def _start_session(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self._append_log("Could not open webcam.", "danger")
            return

        self.running       = True
        self.session_start = time.time()
        self.violation_count = 0
        self._update_violations()

        self.btn_toggle.configure(text="⏹  Stop Session", bg=DANGER,
                                  activebackground="#c0392b")
        self._set_badge("MONITORING", SUCCESS)
        self._append_log("Session started.", "ok")

        self.thread = threading.Thread(target=self._video_loop, daemon=True)
        self.thread.start()

        self._tick_uptime()

    def _stop_session(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_toggle.configure(text="▶  Start Session", bg=ACCENT,
                                  activebackground="#3a6bd6")
        self._set_badge("STOPPED", MUTED)
        self._set_status(self.status_head, "—", MUTED)
        self._set_status(self.status_obj,  "—", MUTED)
        self._append_log(
            f"Session ended. Total violations: {self.violation_count}", "muted"
        )
        self._show_placeholder()

    def _on_close(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.destroy()

    # ─── uptime ticker ────────────────────────────────────────────────────────
    def _tick_uptime(self):
        if not self.running:
            self.lbl_session.configure(text="Session: --:--:--")
            return
        elapsed = int(time.time() - self.session_start)
        h, rem  = divmod(elapsed, 3600)
        m, s    = divmod(rem, 60)
        self.lbl_session.configure(text=f"Session: {h:02d}:{m:02d}:{s:02d}")
        self.lbl_uptime._value_label.configure(text=f"{h:02d}:{m:02d}")
        self.after(1000, self._tick_uptime)

    # ─── video loop (background thread) ──────────────────────────────────────
    def _video_loop(self):
        detector = ObjectDetector()
        tracker  = HeadMovementTracker()

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            alert_this_frame = False

            # ── object detection ──
            detections = detector.detect(frame)
            obj_names  = []
            for x1, y1, x2, y2, conf, cls in detections:
                obj_names.append(cls)
                color = (231, 76, 60)   # BGR red
                cv2.rectangle(frame,
                              (int(x1), int(y1)), (int(x2), int(y2)),
                              color, 2)
                cv2.putText(frame, f"{cls}  {conf:.0%}",
                            (int(x1), max(int(y1) - 10, 0)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)

            if obj_names:
                alert_this_frame = True
                names = ", ".join(obj_names)
                self.after(0, self._append_log,
                           f"⚠  Prohibited object: {names}", "danger")
                self.after(0, self._set_status, self.status_obj,
                           names, DANGER)
                for n in obj_names:
                    self._write_log_csv("OBJECT_DETECTED", n)
            else:
                self.after(0, self._set_status, self.status_obj,
                           "None detected", SUCCESS)

            # ── head tracking ──
            head_status = tracker.process(frame)

            if head_status == "away":
                alert_this_frame = True
                self.after(0, self._set_status, self.status_head,
                           "Looking away ↩", DANGER)
                self.after(0, self._append_log,
                           "⚠  Head turned away from screen", "warning")
                self._write_log_csv("HEAD_AWAY", "")
                cv2.putText(frame, "HEAD AWAY", (12, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1,
                            (231, 76, 60), 3)
            elif head_status == "no_face":
                alert_this_frame = True
                self.after(0, self._set_status, self.status_head,
                           "No face detected", WARNING)
                cv2.putText(frame, "NO FACE DETECTED", (12, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0,
                            (243, 156, 18), 2)
            else:
                self.after(0, self._set_status, self.status_head,
                           "Facing screen ✔", SUCCESS)

            if alert_this_frame:
                self.violation_count += 1
                self.after(0, self._update_violations)

            # ── push frame to GUI ──
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb).resize((640, 480))
            imgtk = ImageTk.PhotoImage(img)

            def _update_feed(i=imgtk):
                self.lbl_feed.configure(image=i)
                self.lbl_feed.imgtk = i

            self.after(0, _update_feed)

        self.after(0, self._stop_session)


# ─── entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = ProctoringApp()
    app.mainloop()
