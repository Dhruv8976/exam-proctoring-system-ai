"""
Admin Control Panel — Exam Proctoring System
Secure administrative dashboard for reviewing session audit logs,
inspecting captured evidence snapshots, and configuring AI thresholds.

Default Credentials:
  ID: admin
  Password: admin
"""

import tkinter as tk
from tkinter import ttk, font as tkfont, messagebox
import os
import csv
import sys
import platform
import datetime
import shutil

# Enable High-DPI Awareness on Windows
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PIL import Image, ImageTk

from config import (
    load_config, save_config, DEFAULT_CONFIG,
    trigger_remote_audio, set_admin_audio_state,
    trigger_remote_snapshot
)

# ── Minimalist Theme Palette ──────────────────────────────────────────────────
BG         = "#0d1117"   # Minimalist deep matte neutral dark
PANEL      = "#161b22"   # Elevated card surface
PANEL_ALT  = "#21262d"   # Secondary container / badge background
BORDER     = "#30363d"   # Crisp hairline 1px border
BORDER_LGT = "#484f58"   # Subtle hover / active border
ACCENT     = "#3b82f6"   # Clean primary blue
CYAN       = "#60a5fa"   # Soft slate-blue secondary
DANGER     = "#f85149"   # Muted clean red
SUCCESS    = "#3fb950"   # Clean muted emerald green
WARNING    = "#d29922"   # Muted amber gold
INTRUDER   = "#a371f7"   # Clean muted violet
TEXT       = "#f0f6fc"   # Crisp readable white
TEXT_MUTED = "#8b949e"   # Calm neutral secondary slate
MUTED      = "#6e7681"   # Neutral tertiary / disabled


class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ProctorAI — Admin Console")
        self.configure(bg=BG)
        self.geometry("1100x740")
        self.minsize(980, 640)

        self.cfg = load_config()
        self.is_authenticated = False

        self._build_fonts()
        self._build_styles()

        self.container = tk.Frame(self, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.show_login_screen()

    # ── Fonts & TTK Styles ────────────────────────────────────────────────────
    def _build_fonts(self):
        self.font_title   = tkfont.Font(family="Segoe UI", size=13, weight="bold")
        self.font_heading = tkfont.Font(family="Segoe UI", size=10, weight="bold")
        self.font_subhead = tkfont.Font(family="Segoe UI", size=9,  weight="bold")
        self.font_body    = tkfont.Font(family="Segoe UI", size=9)
        self.font_small   = tkfont.Font(family="Segoe UI", size=8)
        self.font_mono    = tkfont.Font(family="Consolas", size=9)
        self.font_stat    = tkfont.Font(family="Segoe UI", size=20, weight="bold")
        self.font_badge   = tkfont.Font(family="Segoe UI", size=8,  weight="bold")

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Configure Dark Notebook
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=TEXT_MUTED,
                        padding=[14, 7], font=("Segoe UI", 9), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", PANEL_ALT)],
                  foreground=[("selected", TEXT)])

        # Configure Dark Treeview
        style.configure("Treeview", background="#0d1117", foreground=TEXT,
                        fieldbackground="#0d1117", borderwidth=0, font=("Segoe UI", 9), rowheight=26)
        style.configure("Treeview.Heading", background=PANEL_ALT, foreground=TEXT_MUTED,
                        font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Treeview",
                  background=[("selected", "#1f2937")],
                  foreground=[("selected", "#ffffff")])

        # Configure Scrollbar
        style.configure("Vertical.TScrollbar", background=PANEL, troughcolor=BG, borderwidth=0)

    # ── Helper Button Creator ─────────────────────────────────────────────────
    def _make_btn(self, parent, text, command, bg, fg, hover, px=12, py=6, font=None):
        if font is None:
            font = self.font_subhead
        btn = tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=hover, activeforeground="white",
            font=font, relief="flat", padx=px, pady=py, cursor="hand2", bd=0
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
        return btn

    # ── Screen 1: Login Gate ──────────────────────────────────────────────────
    def show_login_screen(self):
        for w in self.container.winfo_children():
            w.destroy()

        login_outer = tk.Frame(self.container, bg=BG)
        login_outer.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(login_outer, bg=PANEL, padx=36, pady=32,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack()

        # Header Title
        tk.Label(card, text="ProctorAI Admin", bg=PANEL, fg=TEXT,
                 font=self.font_title).pack()
        tk.Label(card, text="Administrator Authentication", bg=PANEL, fg=TEXT_MUTED,
                 font=self.font_small).pack(pady=(2, 20))

        # Admin ID Field
        tk.Label(card, text="Username", bg=PANEL, fg=TEXT_MUTED,
                 font=self.font_small).pack(anchor="w")
        self.entry_id = tk.Entry(
            card, bg="#0d1117", fg=TEXT, insertbackground=TEXT,
            font=self.font_body, relief="flat", width=28,
            highlightbackground=BORDER, highlightthickness=1
        )
        self.entry_id.pack(fill="x", pady=(4, 12), ipady=5)
        self.entry_id.insert(0, "admin")
        self.entry_id.focus()

        # Password Field
        tk.Label(card, text="Password", bg=PANEL, fg=TEXT_MUTED,
                 font=self.font_small).pack(anchor="w")
        self.entry_pass = tk.Entry(
            card, bg="#0d1117", fg=TEXT, insertbackground=TEXT,
            font=self.font_body, relief="flat", width=28, show="●",
            highlightbackground=BORDER, highlightthickness=1
        )
        self.entry_pass.pack(fill="x", pady=(4, 16), ipady=5)
        self.entry_pass.bind("<Return>", lambda e: self._attempt_login())

        # Error Message Label
        self.lbl_login_err = tk.Label(card, text="", bg=PANEL, fg=DANGER, font=self.font_small)
        self.lbl_login_err.pack(pady=(0, 10))

        # Login Action Button
        btn_login = self._make_btn(
            card, "Sign In", self._attempt_login,
            bg=SUCCESS, fg="#ffffff", hover="#2ea043", px=16, py=7, font=self.font_heading
        )
        btn_login.pack(fill="x", pady=(0, 12))

        # Default Credentials Hint
        hint_box = tk.Frame(card, bg=PANEL_ALT, padx=10, pady=6,
                            highlightbackground=BORDER, highlightthickness=1)
        hint_box.pack(fill="x")
        tk.Label(hint_box, text="Default Credentials:\nUsername: admin   •   Password: admin",
                 bg=PANEL_ALT, fg=MUTED, font=self.font_small, justify="center").pack()

    def _attempt_login(self):
        input_id   = self.entry_id.get().strip()
        input_pass = self.entry_pass.get().strip()

        stored_id   = self.cfg.get("admin_id", "admin")
        stored_pass = self.cfg.get("admin_pass", "admin")

        if input_id == stored_id and input_pass == stored_pass:
            self.is_authenticated = True
            self.show_dashboard()
        else:
            self.lbl_login_err.configure(text="Invalid Username or Password.")
            self.entry_pass.delete(0, "end")
            self.entry_pass.focus()

    # ── Screen 2: Admin Dashboard ─────────────────────────────────────────────
    def show_dashboard(self):
        for w in self.container.winfo_children():
            w.destroy()

        # Top Command Bar
        top_bar = tk.Frame(self.container, bg=PANEL, height=52,
                           highlightbackground=BORDER, highlightthickness=1)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        top_left = tk.Frame(top_bar, bg=PANEL)
        top_left.pack(side="left", padx=16, pady=6)
        tk.Label(top_left, text="ProctorAI Admin Console", bg=PANEL, fg=TEXT,
                 font=self.font_title).pack(side="left")
        tk.Label(top_left, text="Signed in: admin", bg=PANEL_ALT, fg=TEXT_MUTED,
                 font=self.font_small, padx=8, pady=2,
                 highlightbackground=BORDER, highlightthickness=1).pack(side="left", padx=12)

        top_right = tk.Frame(top_bar, bg=PANEL)
        top_right.pack(side="right", padx=16, pady=6)

        self._make_btn(
            top_right, "Logout", self._logout,
            bg=PANEL_ALT, fg=TEXT_MUTED, hover=DANGER, px=10, py=3
        ).pack(side="right")

        # ── Remote Candidate Audio Command Bar ────────────────────────────────
        audio_bar = tk.Frame(self.container, bg=PANEL_ALT, height=48,
                             highlightbackground=BORDER, highlightthickness=1)
        audio_bar.pack(fill="x", padx=16, pady=(10, 0))
        audio_bar.pack_propagate(False)

        bar_left = tk.Frame(audio_bar, bg=PANEL_ALT)
        bar_left.pack(side="left", padx=12, pady=6)

        tk.Label(bar_left, text="Candidate Audio:", bg=PANEL_ALT, fg=TEXT,
                 font=self.font_subhead).pack(side="left", padx=(0, 8))

        current_audio = self.cfg.get("sound_alerts", True)
        self.btn_audio_master = self._make_btn(
            bar_left,
            "Audio: Enabled" if current_audio else "Audio: Silenced",
            self._toggle_admin_audio,
            bg=SUCCESS if current_audio else PANEL,
            fg="#ffffff" if current_audio else TEXT_MUTED,
            hover="#2ea043" if current_audio else BORDER_LGT,
            px=10, py=3
        )
        self.btn_audio_master.pack(side="left", padx=4)

        tk.Label(bar_left, text="Directives:", bg=PANEL_ALT, fg=TEXT_MUTED,
                 font=self.font_small).pack(side="left", padx=(10, 6))

        self.btn_beep = self._make_btn(
            bar_left, "Warning Chime",
            lambda: self._dispatch_remote_audio("warning"),
            bg=PANEL, fg=WARNING, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_beep.pack(side="left", padx=3)

        self.btn_urgent = self._make_btn(
            bar_left, "Danger Beep",
            lambda: self._dispatch_remote_audio("danger"),
            bg=PANEL, fg=DANGER, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_urgent.pack(side="left", padx=3)

        self.btn_siren = self._make_btn(
            bar_left, "Emergency Siren",
            lambda: self._dispatch_remote_audio("siren"),
            bg=PANEL, fg=INTRUDER, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_siren.pack(side="left", padx=3)

        self.btn_remote_snap = self._make_btn(
            bar_left, "Capture Snapshot",
            self._request_candidate_snapshot,
            bg=PANEL, fg=CYAN, hover=BORDER_LGT, px=10, py=3
        )
        self.btn_remote_snap.pack(side="left", padx=3)

        bar_right = tk.Frame(audio_bar, bg=PANEL_ALT)
        bar_right.pack(side="right", padx=12, pady=6)

        self.lbl_dispatch_status = tk.Label(
            bar_right, text="● Audio & Evidence Dispatch Online (Candidates Synchronized)",
            bg=PANEL_ALT, fg=SUCCESS, font=self.font_small
        )
        self.lbl_dispatch_status.pack(side="right")

        # Main Notebook Tabs
        self.notebook = ttk.Notebook(self.container)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=12)

        # Tab 1: Session Audit Logs
        tab_logs = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab_logs, text="Audit Logs")
        self._build_logs_tab(tab_logs)

        # Tab 2: Evidence Vault
        tab_evidence = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab_evidence, text="Evidence Vault")
        self._build_evidence_tab(tab_evidence)

        # Tab 3: AI Rules & Sensitivity Tuning
        tab_rules = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab_rules, text="Detection Settings")
        self._build_rules_tab(tab_rules)

        # Tab 4: System Diagnostics & Security
        tab_diag = tk.Frame(self.notebook, bg=BG)
        self.notebook.add(tab_diag, text="System & Security")
        self._build_security_tab(tab_diag)

    def _toggle_admin_audio(self):
        self.cfg = load_config()
        current = self.cfg.get("sound_alerts", True)
        new_state = not current
        if set_admin_audio_state(new_state):
            self.cfg["sound_alerts"] = new_state
            if new_state:
                self.btn_audio_master.configure(
                    text="🔊 Audio: ACTIVE [Enabled]",
                    bg=SUCCESS, fg="#ffffff"
                )
                self.lbl_dispatch_status.configure(
                    text=f"● Candidate audio enabled across stations [{datetime.datetime.now().strftime('%H:%M:%S')}]",
                    fg=SUCCESS
                )
            else:
                self.btn_audio_master.configure(
                    text="🔇 Audio: SILENCED [Disabled]",
                    bg=PANEL, fg=TEXT_MUTED
                )
                self.lbl_dispatch_status.configure(
                    text=f"● Candidate audio silenced across stations [{datetime.datetime.now().strftime('%H:%M:%S')}]",
                    fg=MUTED
                )
        else:
            messagebox.showerror("Error", "Failed to update audio state in config.")

    def _dispatch_remote_audio(self, sound_type: str):
        if trigger_remote_audio(sound_type):
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            color = INTRUDER if sound_type == "siren" else (DANGER if sound_type == "danger" else WARNING)
            self.lbl_dispatch_status.configure(
                text=f"📢 Transmitted [{sound_type.upper()}] directive to candidate stations at {ts}!",
                fg=color
            )
        else:
            messagebox.showerror("Error", f"Failed to dispatch {sound_type} directive.")

    def _request_candidate_snapshot(self):
        """Dispatches an on-demand snapshot capture directive to candidate station."""
        if trigger_remote_snapshot():
            ts = datetime.datetime.now().strftime('%H:%M:%S')
            if hasattr(self, 'lbl_dispatch_status'):
                self.lbl_dispatch_status.configure(
                    text=f"📸 Transmitted [CAPTURE SNAPSHOT] directive to candidate at {ts}!",
                    fg=CYAN
                )
            # Reload Evidence Vault after brief delay so file is saved on disk
            self.after(900, self._load_snapshots)
        else:
            messagebox.showerror("Error", "Failed to dispatch snapshot request.")

    def _logout(self):
        self.is_authenticated = False
        self.show_login_screen()

    # ── Tab 1: Session Audit Logs ─────────────────────────────────────────────
    def _build_logs_tab(self, parent):
        body = tk.Frame(parent, bg=BG)
        body.pack(fill="both", expand=True, pady=8)

        # Left Column: Sessions List
        left = tk.Frame(body, bg=PANEL, width=280, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        hdr_left = tk.Frame(left, bg=PANEL)
        hdr_left.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(hdr_left, text="SAVED SESSIONS", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(side="left")
        self._make_btn(
            hdr_left, "Refresh", self._load_session_files,
            bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=8, py=2, font=self.font_small
        ).pack(side="right")

        self.list_sessions = tk.Listbox(
            left, bg="#0d1117", fg=TEXT, selectbackground=ACCENT,
            selectforeground="#ffffff", font=self.font_mono, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, activestyle="none"
        )
        self.list_sessions.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.list_sessions.bind("<<ListboxSelect>>", self._on_session_selected)

        # Right Column: Session Details & Event Table
        right = tk.Frame(body, bg=BG)
        right.pack(side="right", fill="both", expand=True)

        # Metrics Card for selected session
        card_summary = tk.Frame(right, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card_summary.pack(fill="x", pady=(0, 10))

        sum_hdr = tk.Frame(card_summary, bg=PANEL)
        sum_hdr.pack(fill="x", padx=14, pady=(8, 4))
        self.lbl_selected_session = tk.Label(
            sum_hdr, text="Select a session to inspect audit trail",
            bg=PANEL, fg=TEXT, font=self.font_heading
        )
        self.lbl_selected_session.pack(side="left")

        # Stats tiles
        tiles_row = tk.Frame(card_summary, bg=PANEL)
        tiles_row.pack(fill="x", padx=14, pady=(4, 10))

        self.box_log_total   = self._create_mini_stat(tiles_row, "TOTAL EVENTS", "—", TEXT)
        self.box_log_objects = self._create_mini_stat(tiles_row, "OBJECT FLAGS", "—", DANGER)
        self.box_log_gaze    = self._create_mini_stat(tiles_row, "GAZE VIOLATIONS", "—", WARNING)
        self.box_log_extra   = self._create_mini_stat(tiles_row, "EXTRA PERSONS", "—", INTRUDER)
        self.box_log_score   = self._create_mini_stat(tiles_row, "EST. INTEGRITY", "—", SUCCESS)

        # Table of Events
        card_table = tk.Frame(right, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card_table.pack(fill="both", expand=True)

        tbl_hdr = tk.Frame(card_table, bg=PANEL)
        tbl_hdr.pack(fill="x", padx=14, pady=(8, 4))
        tk.Label(tbl_hdr, text="EVENT STREAM TABLE", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(side="left")

        tbl_actions = tk.Frame(tbl_hdr, bg=PANEL)
        tbl_actions.pack(side="right")

        self.btn_open_csv = self._make_btn(
            tbl_actions, "Open CSV", self._open_selected_csv,
            bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=10, py=2, font=self.font_small
        )
        self.btn_open_csv.pack(side="left", padx=4)

        self.btn_del_log = self._make_btn(
            tbl_actions, "Delete", self._delete_selected_csv,
            bg=PANEL_ALT, fg=DANGER, hover=BORDER_LGT, px=10, py=2, font=self.font_small
        )
        self.btn_del_log.pack(side="left", padx=4)

        # Treeview
        tree_frame = tk.Frame(card_table, bg=PANEL)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        columns = ("time", "type", "severity", "detail")
        self.tree_events = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self.tree_events.heading("time",     text="TIMESTAMP")
        self.tree_events.heading("type",     text="EVENT TYPE")
        self.tree_events.heading("severity", text="SEVERITY")
        self.tree_events.heading("detail",   text="DETECTION DETAILS")

        self.tree_events.column("time",     width=160, anchor="w")
        self.tree_events.column("type",     width=180, anchor="w")
        self.tree_events.column("severity", width=110, anchor="center")
        self.tree_events.column("detail",   width=260, anchor="w")

        scroll_tree = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_events.yview)
        self.tree_events.configure(yscrollcommand=scroll_tree.set)

        self.tree_events.pack(side="left", fill="both", expand=True)
        scroll_tree.pack(side="right", fill="y")

        self.current_csv_path = None
        self._load_session_files()

    def _create_mini_stat(self, parent, label, val, color):
        box = tk.Frame(parent, bg=PANEL_ALT, padx=10, pady=6,
                       highlightbackground=BORDER, highlightthickness=1)
        box.pack(side="left", fill="both", expand=True, padx=2)
        tk.Label(box, text=label, bg=PANEL_ALT, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w")
        lbl_v = tk.Label(box, text=val, bg=PANEL_ALT, fg=color, font=self.font_heading)
        lbl_v.pack(anchor="w")
        box._val = lbl_v
        return box

    def _load_session_files(self):
        self.list_sessions.delete(0, "end")
        os.makedirs("logs", exist_ok=True)
        files = sorted([f for f in os.listdir("logs") if f.endswith(".csv")], reverse=True)
        for f in files:
            self.list_sessions.insert("end", f)
        if files:
            self.list_sessions.select_set(0)
            self._on_session_selected(None)

    def _on_session_selected(self, event):
        sel = self.list_sessions.curselection()
        if not sel:
            return
        filename = self.list_sessions.get(sel[0])
        csv_path = os.path.join("logs", filename)
        self.current_csv_path = csv_path
        self.lbl_selected_session.configure(text=f"AUDIT TRAIL: {filename}")

        # Parse CSV
        self.tree_events.delete(*self.tree_events.get_children())
        total_events = 0
        obj_count    = 0
        gaze_count   = 0
        extra_count  = 0

        try:
            with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        ts, ev_type = row[0], row[1]
                        detail = row[2] if len(row) > 2 else ""
                        total_events += 1

                        if ev_type == "OBJECT_DETECTED":
                            sev = "HIGH"
                            obj_count += 1
                        elif ev_type in ("HEAD_AWAY", "NO_FACE"):
                            sev = "MEDIUM"
                            gaze_count += 1
                        elif "INTRUDER" in ev_type:
                            sev = "CRITICAL"
                            extra_count += 1
                        else:
                            sev = "INFO"

                        # Format timestamp display
                        time_part = ts.split("T")[-1] if "T" in ts else ts
                        self.tree_events.insert("", "end", values=(time_part, ev_type, sev, detail))

            # Update metrics
            self.box_log_total._val.configure(text=str(total_events))
            self.box_log_objects._val.configure(text=str(obj_count))
            self.box_log_gaze._val.configure(text=str(gaze_count))
            self.box_log_extra._val.configure(text=str(extra_count))

            est_penalty = (obj_count + gaze_count) * self.cfg.get("violation_penalty", 2) + extra_count * self.cfg.get("intruder_penalty", 10)
            score = max(0, 100 - est_penalty)
            score_color = SUCCESS if score >= 90 else (WARNING if score >= 70 else DANGER)
            self.box_log_score._val.configure(text=f"{score}%", fg=score_color)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read CSV: {e}")

    def _open_selected_csv(self):
        if self.current_csv_path and os.path.exists(self.current_csv_path):
            if platform.system() == "Windows":
                os.startfile(self.current_csv_path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self.current_csv_path])

    def _delete_selected_csv(self):
        if not self.current_csv_path or not os.path.exists(self.current_csv_path):
            return
        if messagebox.askyesno("Confirm Delete", f"Delete log file '{os.path.basename(self.current_csv_path)}'?"):
            try:
                os.remove(self.current_csv_path)
                self._load_session_files()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")

    # ── Tab 2: Evidence Vault ─────────────────────────────────────────────────
    def _build_evidence_tab(self, parent):
        body = tk.Frame(parent, bg=BG)
        body.pack(fill="both", expand=True, pady=8)

        # Left Column: Snapshots List
        left = tk.Frame(body, bg=PANEL, width=320, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        hdr_left = tk.Frame(left, bg=PANEL)
        hdr_left.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(hdr_left, text="EVIDENCE ARCHIVE", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(side="left")
        self._make_btn(
            hdr_left, "Refresh", self._load_snapshots,
            bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=8, py=2, font=self.font_small
        ).pack(side="right")

        self.list_snaps = tk.Listbox(
            left, bg="#0d1117", fg=TEXT, selectbackground=ACCENT,
            selectforeground="#ffffff", font=self.font_mono, relief="flat",
            highlightbackground=BORDER, highlightthickness=1, activestyle="none"
        )
        self.list_snaps.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.list_snaps.bind("<<ListboxSelect>>", self._on_snapshot_selected)

        # Right Column: Snapshot Viewer & Meta
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="both", expand=True)

        hdr_view = tk.Frame(right, bg=PANEL)
        hdr_view.pack(fill="x", padx=16, pady=(10, 6))
        self.lbl_snap_title = tk.Label(hdr_view, text="Evidence Preview", bg=PANEL, fg=TEXT, font=self.font_heading)
        self.lbl_snap_title.pack(side="left")

        actions = tk.Frame(hdr_view, bg=PANEL)
        actions.pack(side="right")
        self._make_btn(actions, "Capture Snapshot", self._request_candidate_snapshot,
                       bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=10, py=3, font=self.font_small).pack(side="left", padx=4)
        self._make_btn(actions, "View Full Size", self._open_full_snapshot,
                       bg=PANEL_ALT, fg=TEXT, hover=BORDER_LGT, px=10, py=3, font=self.font_small).pack(side="left", padx=4)
        self._make_btn(actions, "Open Folder", self._open_snaps_dir,
                       bg=PANEL_ALT, fg=TEXT_MUTED, hover=BORDER_LGT, px=10, py=3, font=self.font_small).pack(side="left", padx=4)
        self._make_btn(actions, "Delete", self._delete_snapshot,
                       bg=PANEL_ALT, fg=DANGER, hover=BORDER_LGT, px=10, py=3, font=self.font_small).pack(side="left", padx=4)

        # Image Canvas / Label
        img_container = tk.Frame(right, bg="#0d1117", highlightbackground=BORDER, highlightthickness=1)
        img_container.pack(fill="both", expand=True, padx=16, pady=8)

        self.lbl_snap_display = tk.Label(img_container, bg="#0d1117", fg=TEXT_MUTED, text="Select a snapshot to preview evidence")
        self.lbl_snap_display.pack(fill="both", expand=True)

        # Meta bar
        self.lbl_snap_meta = tk.Label(
            right, text="File: None  |  Timestamp: —  |  Dimensions: —",
            bg=PANEL, fg=TEXT_MUTED, font=self.font_small
        )
        self.lbl_snap_meta.pack(anchor="w", padx=16, pady=(0, 10))

        self.current_snap_path = None
        self._load_snapshots()

    def _load_snapshots(self):
        self.list_snaps.delete(0, "end")
        os.makedirs("snapshots", exist_ok=True)
        snaps = sorted([f for f in os.listdir("snapshots") if f.lower().endswith((".jpg", ".png", ".jpeg"))], reverse=True)
        for s in snaps:
            self.list_snaps.insert("end", s)
        if snaps:
            self.list_snaps.select_set(0)
            self._on_snapshot_selected(None)

    def _on_snapshot_selected(self, event):
        sel = self.list_snaps.curselection()
        if not sel:
            return
        filename = self.list_snaps.get(sel[0])
        snap_path = os.path.join("snapshots", filename)
        self.current_snap_path = snap_path
        self.lbl_snap_title.configure(text=f"EVIDENCE: {filename}")

        try:
            img = Image.open(snap_path)
            orig_w, orig_h = img.size
            # Fit inside preview area
            img.thumbnail((620, 420))
            photo = ImageTk.PhotoImage(img)
            self.lbl_snap_display.configure(image=photo, text="")
            self.lbl_snap_display.image = photo

            size_kb = os.path.getsize(snap_path) / 1024.0
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(snap_path)).strftime("%Y-%m-%d %H:%M:%S")
            self.lbl_snap_meta.configure(
                text=f"File: {filename}   •   Time: {mtime}   •   Resolution: {orig_w}x{orig_h}   •   Size: {size_kb:.1f} KB"
            )
        except Exception as e:
            self.lbl_snap_display.configure(image="", text=f"Error previewing: {e}")

    def _open_full_snapshot(self):
        if self.current_snap_path and os.path.exists(self.current_snap_path):
            if platform.system() == "Windows":
                os.startfile(self.current_snap_path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", self.current_snap_path])

    def _open_snaps_dir(self):
        os.makedirs("snapshots", exist_ok=True)
        if platform.system() == "Windows":
            os.startfile("snapshots")
        else:
            import subprocess
            subprocess.Popen(["xdg-open", "snapshots"])

    def _delete_snapshot(self):
        if not self.current_snap_path or not os.path.exists(self.current_snap_path):
            return
        if messagebox.askyesno("Confirm Delete", f"Delete evidence photo '{os.path.basename(self.current_snap_path)}'?"):
            try:
                os.remove(self.current_snap_path)
                self._load_snapshots()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    # ── Tab 3: AI Sensitivity & Rules ─────────────────────────────────────────
    def _build_rules_tab(self, parent):
        body = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, pady=8, padx=4)

        hdr = tk.Frame(body, bg=PANEL)
        hdr.pack(fill="x", padx=20, pady=(14, 6))
        tk.Label(hdr, text="Detection Thresholds & Penalty Rules",
                 bg=PANEL, fg=TEXT, font=self.font_heading).pack(side="left")

        tk.Label(body, text="Tune model confidence thresholds and gaze sensitivity to adjust strictness.",
                 bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=20, pady=(0, 16))

        # Settings Form Grid
        grid_frame = tk.Frame(body, bg=PANEL)
        grid_frame.pack(fill="x", padx=20)

        # 1. Phone threshold
        self.scale_phone = self._create_slider_row(
            grid_frame, 0, "Cell Phone Minimum Confidence:",
            self.cfg.get("threshold_phone", 0.55), 0.30, 0.90, 0.05
        )

        # 2. Book threshold
        self.scale_book = self._create_slider_row(
            grid_frame, 1, "Book Minimum Confidence:",
            self.cfg.get("threshold_book", 0.65), 0.30, 0.90, 0.05
        )

        # 3. Laptop threshold
        self.scale_laptop = self._create_slider_row(
            grid_frame, 2, "Laptop / Screen Minimum Confidence:",
            self.cfg.get("threshold_laptop", 0.65), 0.30, 0.90, 0.05
        )

        # 4. Head Yaw threshold
        self.scale_yaw = self._create_slider_row(
            grid_frame, 3, "Head Yaw (Gaze Angle Deviation):",
            self.cfg.get("yaw_threshold", 0.30), 0.15, 0.50, 0.01
        )

        # 5. Debounce frames
        self.scale_debounce = self._create_slider_row(
            grid_frame, 4, "Debounce Frames (Consecutive away frames):",
            self.cfg.get("away_frames", 8), 3, 20, 1, is_int=True
        )

        # 6. Violation Penalty
        self.scale_pen_v = self._create_slider_row(
            grid_frame, 5, "Penalty Points per Object / Gaze Flag:",
            self.cfg.get("violation_penalty", 2), 1, 10, 1, is_int=True
        )

        # 7. Intruder Penalty
        self.scale_pen_i = self._create_slider_row(
            grid_frame, 6, "Penalty Points per Extra Person Intrusion:",
            self.cfg.get("intruder_penalty", 10), 5, 30, 1, is_int=True
        )

        # Buttons
        btn_bar = tk.Frame(body, bg=PANEL)
        btn_bar.pack(fill="x", padx=20, pady=24)

        self._make_btn(
            btn_bar, "Save Changes", self._save_rules,
            bg=SUCCESS, fg="#ffffff", hover="#2ea043", px=16, py=6, font=self.font_heading
        ).pack(side="left", padx=(0, 10))

        self._make_btn(
            btn_bar, "Reset to Defaults", self._reset_rules,
            bg=PANEL_ALT, fg=TEXT_MUTED, hover=BORDER_LGT, px=14, py=6
        ).pack(side="left")

    def _create_slider_row(self, parent, row_idx, label_text, current_val, min_v, max_v, step, is_int=False):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill="x", pady=6)

        tk.Label(row, text=label_text, bg=PANEL, fg=TEXT, font=self.font_body, width=44, anchor="w").pack(side="left")

        val_var = tk.DoubleVar(value=current_val)
        lbl_display = tk.Label(row, text=f"{int(current_val) if is_int else current_val:.2f}",
                               bg=PANEL_ALT, fg=TEXT, font=self.font_mono, width=7,
                               highlightbackground=BORDER, highlightthickness=1)

        def _on_scroll(v):
            f = float(v)
            lbl_display.configure(text=f"{int(round(f)) if is_int else f:.2f}")

        scale = tk.Scale(
            row, from_=min_v, to=max_v, resolution=step, orient="horizontal",
            variable=val_var, command=_on_scroll, bg=PANEL, fg=TEXT,
            troughcolor="#0d1117", activebackground=ACCENT, highlightthickness=0,
            showvalue=0, length=240, relief="flat", cursor="hand2"
        )
        scale.pack(side="left", padx=10)
        lbl_display.pack(side="left", padx=6)
        scale._is_int = is_int
        scale._var = val_var
        return scale

    def _save_rules(self):
        self.cfg["threshold_phone"]   = round(float(self.scale_phone._var.get()), 2)
        self.cfg["threshold_book"]    = round(float(self.scale_book._var.get()), 2)
        self.cfg["threshold_laptop"]  = round(float(self.scale_laptop._var.get()), 2)
        self.cfg["yaw_threshold"]     = round(float(self.scale_yaw._var.get()), 2)
        self.cfg["away_frames"]       = int(round(float(self.scale_debounce._var.get())))
        self.cfg["violation_penalty"] = int(round(float(self.scale_pen_v._var.get())))
        self.cfg["intruder_penalty"]  = int(round(float(self.scale_pen_i._var.get())))

        if save_config(self.cfg):
            messagebox.showinfo("Configuration Saved", "AI detection thresholds and proctoring rules updated successfully!")
        else:
            messagebox.showerror("Error", "Could not save settings to config.json.")

    def _reset_rules(self):
        if messagebox.askyesno("Reset", "Reset all thresholds to factory defaults?"):
            for k in DEFAULT_CONFIG:
                if k not in ("admin_id", "admin_pass"):
                    self.cfg[k] = DEFAULT_CONFIG[k]
            save_config(self.cfg)
            self.show_dashboard()

    # ── Tab 4: Security & System Diagnostics ──────────────────────────────────
    def _build_security_tab(self, parent):
        body = tk.Frame(parent, bg=BG)
        body.pack(fill="both", expand=True, pady=8)

        # Left Column: Change Credentials
        left = tk.Frame(body, bg=PANEL, width=420, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", padx=(0, 10))

        tk.Label(left, text="Admin Credentials", bg=PANEL, fg=TEXT,
                 font=self.font_heading).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(left, text="Update username and access password for the admin console.",
                 bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=16, pady=(0, 14))

        tk.Label(left, text="Admin Username", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=16)
        self.entry_new_id = tk.Entry(
            left, bg="#0d1117", fg=TEXT, insertbackground=TEXT, font=self.font_body,
            relief="flat", highlightbackground=BORDER, highlightthickness=1
        )
        self.entry_new_id.pack(fill="x", padx=16, pady=(4, 12), ipady=4)
        self.entry_new_id.insert(0, self.cfg.get("admin_id", "admin"))

        tk.Label(left, text="New Password", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=16)
        self.entry_new_pass = tk.Entry(
            left, bg="#0d1117", fg=TEXT, insertbackground=TEXT, font=self.font_body,
            relief="flat", show="●", highlightbackground=BORDER, highlightthickness=1
        )
        self.entry_new_pass.pack(fill="x", padx=16, pady=(4, 12), ipady=4)

        tk.Label(left, text="Confirm New Password", bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=16)
        self.entry_new_pass2 = tk.Entry(
            left, bg="#0d1117", fg=TEXT, insertbackground=TEXT, font=self.font_body,
            relief="flat", show="●", highlightbackground=BORDER, highlightthickness=1
        )
        self.entry_new_pass2.pack(fill="x", padx=16, pady=(4, 16), ipady=4)

        self._make_btn(
            left, "Update Credentials", self._update_credentials,
            bg=ACCENT, fg="#ffffff", hover=BORDER_LGT, px=14, py=6
        ).pack(anchor="w", padx=16, pady=(0, 20))

        # Right Column: System Diagnostics
        right = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="right", fill="both", expand=True)

        tk.Label(right, text="System Diagnostics", bg=PANEL, fg=TEXT,
                 font=self.font_heading).pack(anchor="w", padx=16, pady=(16, 4))
        tk.Label(right, text="Operational state of AI models, runtime engines, and storage.",
                 bg=PANEL, fg=TEXT_MUTED, font=self.font_small).pack(anchor="w", padx=16, pady=(0, 14))

        diag_box = tk.Frame(right, bg="#0d1117", padx=14, pady=12,
                            highlightbackground=BORDER, highlightthickness=1)
        diag_box.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # Info rows
        self._add_diag_row(diag_box, "Operating System:", f"{platform.system()} {platform.release()} ({platform.architecture()[0]})")
        self._add_diag_row(diag_box, "Python Interpreter:", f"v{sys.version.split()[0]} ({sys.executable})")

        try:
            import cv2
            cv_ver = cv2.__version__
        except Exception:
            cv_ver = "Not Loaded"
        self._add_diag_row(diag_box, "OpenCV Engine:", f"v{cv_ver}")

        try:
            from ultralytics import YOLO
            yolo_status = "Available (YOLOv8 Active)"
        except Exception:
            yolo_status = "Not Installed"
        self._add_diag_row(diag_box, "YOLOv8 Neural Core:", yolo_status)

        # Storage info
        os.makedirs("logs", exist_ok=True)
        os.makedirs("snapshots", exist_ok=True)
        log_files = [f for f in os.listdir("logs") if f.endswith(".csv")]
        snap_files = [f for f in os.listdir("snapshots") if f.lower().endswith((".jpg", ".png", ".jpeg"))]

        self._add_diag_row(diag_box, "Session Logs Stored:", f"{len(log_files)} sessions in logs/")
        self._add_diag_row(diag_box, "Evidence Snapshots:", f"{len(snap_files)} files in snapshots/")
        self._add_diag_row(diag_box, "Config File Status:", f"Loaded ({CONFIG_FILE})")
        audio_mode = "Active (Admin Dispatched)" if self.cfg.get("sound_alerts", True) else "Silenced (Admin Controlled)"
        self._add_diag_row(diag_box, "Remote Audio Dispatch:", audio_mode)

    def _add_diag_row(self, parent, label, val):
        row = tk.Frame(parent, bg="#0d1117")
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, bg="#0d1117", fg=TEXT_MUTED, font=self.font_small, width=22, anchor="w").pack(side="left")
        tk.Label(row, text=val, bg="#0d1117", fg=TEXT, font=self.font_mono, anchor="w").pack(side="left")

    def _update_credentials(self):
        new_id = self.entry_new_id.get().strip()
        p1     = self.entry_new_pass.get().strip()
        p2     = self.entry_new_pass2.get().strip()

        if not new_id:
            messagebox.showerror("Error", "Admin ID cannot be empty.")
            return
        if not p1:
            messagebox.showerror("Error", "New Password cannot be empty.")
            return
        if p1 != p2:
            messagebox.showerror("Error", "Passwords do not match. Re-enter.")
            return

        self.cfg["admin_id"]   = new_id
        self.cfg["admin_pass"] = p1
        save_config(self.cfg)
        messagebox.showinfo("Success", f"Credentials updated!\nNew Admin ID: {new_id}")
        self.entry_new_pass.delete(0, "end")
        self.entry_new_pass2.delete(0, "end")


if __name__ == "__main__":
    app = AdminApp()
    app.mainloop()

