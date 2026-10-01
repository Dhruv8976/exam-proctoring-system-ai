"""
Exam Proctoring System — GUI
Built with tkinter (stdlib) + OpenCV for webcam.
"""

import tkinter as tk
from tkinter import font as tkfont, messagebox
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
from tracker   import HeadMovementTracker
from intruder  import IntruderDetector

# ─── Palette ──────────────────────────────────────────────────────────────────
BG       = "#0f1117"
PANEL    = "#1a1d27"
ACCENT   = "#4f8ef7"
DANGER   = "#e74c3c"
SUCCESS  = "#2ecc71"
WARNING  = "#f39c12"
INTRUDER = "#9b59b6"   # purple — distinct colour for intruder alerts
TEXT     = "#e8eaf6"
MUTED    = "#6c7a8d"
BORDER   = "#2a2d3e"


class ProctoringApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Exam Proctoring System")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.running            = False
        self.session_start      = None
        self.violation_count    = 0
        self.intruder_count     = 0
        self.cap                = None
        self.thread             = None
        self._intruder_detector = None   # created at session start

        self._build_fonts()
        self._build_layout()
        self._init_log_file()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── fonts ─────────────────────────────────────────────────────────────────
    def _build_fonts(self):
        self.font_title   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_heading = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_body    = tkfont.Font(family="Segoe UI", size=9)
        self.font_mono    = tkfont.Font(family="Consolas",  size=8)
        self.font_stat    = tkfont.Font(family="Segoe UI",  size=20, weight="bold")
        self.font_label   = tkfont.Font(family="Segoe UI",  size=8)
        self.font_badge   = tkfont.Font(family="Segoe UI",  size=9,  weight="bold")

    # ── layout ────────────────────────────────────────────────────────────────
    def _build_layout(self):
        # Header
        header = tk.Frame(self, bg=PANEL, height=54)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="🎓", bg=PANEL, fg=ACCENT,
                 font=tkfont.Font(size=20)).pack(side="left", padx=14, pady=8)
        tk.Label(header, text="Exam Proctoring System", bg=PANEL, fg=TEXT,
                 font=self.font_title).pack(side="left", pady=8)

        self.lbl_clock = tk.Label(header, text="", bg=PANEL, fg=MUTED,
                                  font=self.font_body)
        self.lbl_clock.pack(side="right", padx=18)
        self._tick_clock()

        self.lbl_badge = tk.Label(header, text="  STOPPED  ",
                                  bg=MUTED, fg="white",
                                  font=self.font_badge, padx=8, pady=3)
        self.lbl_badge.pack(side="right", padx=10)

        # Body
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=10)

        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)
        self._build_camera_panel(left)

        right = tk.Frame(body, bg=BG, width=310)
        right.pack(side="right", fill="y", padx=(10, 0))
        right.pack_propagate(False)
        self._build_stats_panel(right)
        self._build_status_panel(right)
        self._build_log_panel(right)

        # Footer
        bar = tk.Frame(self, bg=PANEL, height=52)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.btn_toggle = tk.Button(
            bar, text="▶  Start Session",
            bg=ACCENT, fg="white", activebackground="#3a6bd6",
            font=self.font_heading, relief="flat",
            padx=22, pady=6, cursor="hand2",
            command=self._toggle_session,
        )
        self.btn_toggle.pack(side="left", padx=14, pady=9)

        self.btn_register = tk.Button(
            bar, text="📸  Register Candidate",
            bg=PANEL, fg=MUTED, activebackground=BORDER,
            font=self.font_body, relief="flat",
            padx=12, pady=6, cursor="hand2",
            state="disabled",
            command=self._register_candidate,
        )
        self.btn_register.pack(side="left", padx=4, pady=9)

        tk.Button(
            bar, text="🗑  Clear Log",
            bg=PANEL, fg=MUTED, activebackground=BORDER,
            font=self.font_body, relief="flat",
            padx=12, pady=6, cursor="hand2",
            command=self._clear_log,
        ).pack(side="left", padx=4, pady=9)

        self.lbl_session = tk.Label(bar, text="Session: --:--:--",
                                    bg=PANEL, fg=MUTED, font=self.font_body)
        self.lbl_session.pack(side="right", padx=18)

    # ── camera panel ──────────────────────────────────────────────────────────
    def _build_camera_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="📷  Live Feed", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 0))
        self.lbl_feed = tk.Label(card, bg="#000000", width=640, height=480)
        self.lbl_feed.pack(padx=10, pady=(4, 10))
        self._show_placeholder()

    # ── stats panel ───────────────────────────────────────────────────────────
    def _build_stats_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))
        tk.Label(card, text="SESSION STATS", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 2))

        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", padx=10, pady=(0, 10))

        self.box_violations = self._stat_box(row, "VIOLATIONS", "0", DANGER)
        self.box_violations.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.box_intruders = self._stat_box(row, "INTRUDERS", "0", INTRUDER)
        self.box_intruders.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self.box_uptime = self._stat_box(row, "UPTIME", "00:00", ACCENT)
        self.box_uptime.pack(side="right", expand=True, fill="x")

    def _stat_box(self, parent, label, value, color):
        box = tk.Frame(parent, bg=BORDER, padx=8, pady=8)
        tk.Label(box, text=label, bg=BORDER, fg=MUTED,
                 font=self.font_label).pack(anchor="w")
        lbl = tk.Label(box, text=value, bg=BORDER, fg=color,
                       font=self.font_stat)
        lbl.pack(anchor="w")
        box._value_label = lbl
        return box

    # ── detection status panel ────────────────────────────────────────────────
    def _build_status_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", pady=(0, 8))
        tk.Label(card, text="DETECTION STATUS", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 4))

        self.status_head     = self._status_row(card, "Head Position")
        self.status_obj      = self._status_row(card, "Foreign Object")
        self.status_people   = self._status_row(card, "People in Frame")
        self.status_intruder = self._status_row(card, "Intruder Alert")
        self.status_face     = self._status_row(card, "Face Verification")

        tk.Frame(card, bg=PANEL, height=6).pack()

    def _status_row(self, parent, label):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", padx=10, pady=2)
        tk.Label(row, text=label, bg=PANEL, fg=TEXT,
                 font=self.font_body, width=17, anchor="w").pack(side="left")
        dot = tk.Label(row, text="●", bg=PANEL, fg=MUTED, font=self.font_body)
        dot.pack(side="left", padx=4)
        lbl = tk.Label(row, text="—", bg=PANEL, fg=MUTED,
                       font=self.font_body, anchor="w")
        lbl.pack(side="left")
        return {"dot": dot, "label": lbl}

    # ── alert log panel ───────────────────────────────────────────────────────
    def _build_log_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="ALERT LOG", bg=PANEL, fg=MUTED,
                 font=self.font_label).pack(anchor="w", padx=10, pady=(8, 4))
        self.log_text = tk.Text(
            card, bg=BG, fg=TEXT, insertbackground=TEXT,
            font=self.font_mono, relief="flat",
            wrap="word", state="disabled", padx=8, pady=4,
        )
        self.log_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log_text.tag_config("danger",   foreground=DANGER)
        self.log_text.tag_config("intruder", foreground=INTRUDER)
        self.log_text.tag_config("warning",  foreground=WARNING)
        self.log_text.tag_config("ok",       foreground=SUCCESS)
        self.log_text.tag_config("muted",    foreground=MUTED)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _show_placeholder(self):
        from PIL import ImageDraw
        ph   = Image.new("RGB", (640, 480), color=(15, 17, 23))
        draw = ImageDraw.Draw(ph)
        draw.text((145, 220),
                  "Camera feed will appear here\n   Press  ▶ Start Session  to begin",
                  fill=(70, 80, 100))
        imgtk = ImageTk.PhotoImage(ph)
        self.lbl_feed.configure(image=imgtk)
        self.lbl_feed.imgtk = imgtk

    def _tick_clock(self):
        self.lbl_clock.configure(
            text=datetime.datetime.now().strftime("%A, %d %b %Y   %H:%M:%S")
        )
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
        self.box_violations._value_label.configure(text=str(self.violation_count))

    def _update_intruders(self):
        self.box_intruders._value_label.configure(text=str(self.intruder_count))

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

    # ── session control ───────────────────────────────────────────────────────
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

        self.running            = True
        self.session_start      = time.time()
        self.violation_count    = 0
        self.intruder_count     = 0
        self._intruder_detector = IntruderDetector()
        self._update_violations()
        self._update_intruders()

        self.btn_toggle.configure(text="⏹  Stop Session", bg=DANGER,
                                  activebackground="#c0392b")
        self.btn_register.configure(state="normal", fg=TEXT)
        self._set_badge("MONITORING", SUCCESS)
        self._append_log("Session started.", "ok")
        self._append_log(
            "💡 Click '📸 Register Candidate' while the candidate faces the camera.", "muted"
        )

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
        self.btn_register.configure(state="disabled", fg=MUTED)
        self._set_badge("STOPPED", MUTED)
        for s in (self.status_head, self.status_obj, self.status_people,
                  self.status_intruder, self.status_face):
            self._set_status(s, "—", MUTED)
        self._append_log(
            f"Session ended. Violations: {self.violation_count}  |  "
            f"Intruder events: {self.intruder_count}", "muted"
        )
        self._show_placeholder()

    def _on_close(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.destroy()

    def _register_candidate(self):
        """Triggered by the 'Register Candidate' button."""
        if not self.running or self._intruder_detector is None:
            return
        # Grab the most recent frame
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Error", "Could not capture frame from webcam.")
            return
        ok = self._intruder_detector.register_candidate(frame)
        if ok:
            self._append_log("✅ Candidate face registered.", "ok")
            self.after(0, self._set_status, self.status_face,
                       "Registered ✔", SUCCESS)
            self.btn_register.configure(text="📸  Re-register", fg=SUCCESS)
        else:
            self._append_log(
                "⚠  Could not detect a face — ensure the candidate is visible.", "warning"
            )

    # ── uptime ────────────────────────────────────────────────────────────────
    def _tick_uptime(self):
        if not self.running:
            self.lbl_session.configure(text="Session: --:--:--")
            return
        elapsed = int(time.time() - self.session_start)
        h, rem  = divmod(elapsed, 3600)
        m, s    = divmod(rem, 60)
        self.lbl_session.configure(text=f"Session: {h:02d}:{m:02d}:{s:02d}")
        self.box_uptime._value_label.configure(text=f"{h:02d}:{m:02d}")
        self.after(1000, self._tick_uptime)

    # ── video loop (background thread) ───────────────────────────────────────
    def _video_loop(self):
        detector = ObjectDetector()
        tracker  = HeadMovementTracker()
        # IntruderDetector already created in _start_session
        intruder = self._intruder_detector

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            alert_this_frame    = False
            intruder_this_frame = False

            # ── 1. Object detection ───────────────────────────────────────────
            detections, multiple_people = detector.detect(frame)

            if detections:
                alert_this_frame = True
                names = ", ".join(d[5] for d in detections)
                for x1, y1, x2, y2, conf, cls in detections:
                    cv2.rectangle(frame,
                                  (int(x1), int(y1)), (int(x2), int(y2)),
                                  (231, 76, 60), 2)
                    cv2.putText(frame, f"{cls}  {conf:.0%}",
                                (int(x1), max(int(y1) - 10, 0)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (231, 76, 60), 2)
                self.after(0, self._append_log,
                           f"⚠  Prohibited object: {names}", "danger")
                self.after(0, self._set_status, self.status_obj, names, DANGER)
                self._write_log_csv("OBJECT_DETECTED", names)
            else:
                self.after(0, self._set_status, self.status_obj,
                           "None detected", SUCCESS)

            # ── 2. Multiple people (from object detector) ─────────────────────
            if multiple_people:
                alert_this_frame = True
                self.after(0, self._set_status, self.status_people,
                           "Multiple persons!", DANGER)
                self.after(0, self._append_log,
                           "⚠  Multiple people detected in frame", "danger")
                self._write_log_csv("MULTIPLE_PEOPLE", "")
                cv2.putText(frame, "MULTIPLE PEOPLE", (12, 68),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (231, 76, 60), 2)
            else:
                self.after(0, self._set_status, self.status_people,
                           "1 person", SUCCESS)

            # ── 3. Head tracking ──────────────────────────────────────────────
            head_status = tracker.process(frame)

            if head_status == "away":
                alert_this_frame = True
                self.after(0, self._set_status, self.status_head,
                           "Looking away ↩", DANGER)
                self.after(0, self._append_log,
                           "⚠  Head turned away from screen", "warning")
                self._write_log_csv("HEAD_AWAY", "")
                cv2.putText(frame, "HEAD AWAY", (12, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.1, (231, 76, 60), 3)
            elif head_status == "no_face":
                alert_this_frame = True
                self.after(0, self._set_status, self.status_head,
                           "No face detected", WARNING)
                self.after(0, self._append_log,
                           "⚠  No face detected", "warning")
                self._write_log_csv("NO_FACE", "")
                cv2.putText(frame, "NO FACE DETECTED", (12, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (243, 156, 18), 2)
            else:
                self.after(0, self._set_status, self.status_head,
                           "Facing screen ✔", SUCCESS)

            # ── 4. Intruder detection ─────────────────────────────────────────
            intruder_result = intruder.detect(frame)

            if intruder_result.extra_person:
                intruder_this_frame = True
                self.after(0, self._set_status, self.status_intruder,
                           "🚨 INTRUDER!", INTRUDER)
                self.after(0, self._append_log,
                           f"🚨 INTRUDER ALERT — extra person detected"
                           + (f"  [snapshot: {os.path.basename(intruder_result.snapshot_path)}]"
                              if intruder_result.snapshot_path else ""),
                           "intruder")
                self._write_log_csv("INTRUDER_EXTRA_PERSON",
                                    intruder_result.snapshot_path or "")
                cv2.putText(frame, "!!! INTRUDER DETECTED !!!", (12, 110),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (155, 89, 182), 3)
                cv2.rectangle(frame, (0, 0),
                              (frame.shape[1] - 1, frame.shape[0] - 1),
                              (155, 89, 182), 4)
            else:
                self.after(0, self._set_status, self.status_intruder,
                           "Clear", SUCCESS)

            if intruder_result.face_mismatch:
                intruder_this_frame = True
                self.after(0, self._set_status, self.status_face,
                           "⚠ FACE MISMATCH", DANGER)
                self.after(0, self._append_log,
                           f"🚨 FACE MISMATCH — candidate may have been substituted"
                           + (f"  [snapshot: {os.path.basename(intruder_result.snapshot_path)}]"
                              if intruder_result.snapshot_path else ""),
                           "intruder")
                self._write_log_csv("FACE_MISMATCH",
                                    intruder_result.snapshot_path or "")
                cv2.putText(frame, "FACE MISMATCH", (12, 148),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (231, 76, 60), 2)
            elif intruder.is_registered:
                self.after(0, self._set_status, self.status_face,
                           "Identity OK ✔", SUCCESS)

            if alert_this_frame:
                self.violation_count += 1
                self.after(0, self._update_violations)

            if intruder_this_frame:
                self.intruder_count += 1
                self.after(0, self._update_intruders)

            # ── push frame to GUI ─────────────────────────────────────────────
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img   = Image.fromarray(rgb).resize((640, 480))
            imgtk = ImageTk.PhotoImage(img)

            def _update_feed(i=imgtk):
                self.lbl_feed.configure(image=i)
                self.lbl_feed.imgtk = i

            self.after(0, _update_feed)

        self.after(0, self._stop_session)


if __name__ == "__main__":
    app = ProctoringApp()
    app.mainloop()
