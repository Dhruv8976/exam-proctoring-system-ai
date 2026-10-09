"""
Configuration Manager for Exam Proctoring System & Admin Console.
Persists settings, thresholds, admin authentication, and remote audio control.
"""

import json
import os
import time

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "admin_id": "admin",
    "admin_pass": "admin",
    "threshold_phone": 0.55,
    "threshold_book": 0.65,
    "threshold_laptop": 0.65,
    "yaw_threshold": 0.30,
    "away_frames": 8,
    "violation_penalty": 2,
    "intruder_penalty": 10,
    "sound_alerts": True,
    "remote_audio_trigger": 0.0,
    "remote_audio_type": "",
    "remote_snapshot_trigger": 0.0,
}


def load_config() -> dict:
    """Load configuration from config.json, or create with defaults if missing."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> bool:
    """Save configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)
        return True
    except Exception:
        return False


def trigger_remote_audio(sound_type: str = "warning") -> bool:
    """Invoked by Admin to sound an audio alert on the candidate station at any time."""
    try:
        cfg = load_config()
        cfg["remote_audio_trigger"] = time.time()
        cfg["remote_audio_type"] = sound_type
        return save_config(cfg)
    except Exception:
        return False


def set_admin_audio_state(enabled: bool) -> bool:
    """Invoked by Admin to enable or disable audio alerts across candidate stations."""
    try:
        cfg = load_config()
        cfg["sound_alerts"] = enabled
        return save_config(cfg)
    except Exception:
        return False


def trigger_remote_snapshot() -> bool:
    """Invoked by Admin to capture an on-demand evidence snapshot on candidate station."""
    try:
        cfg = load_config()
        cfg["remote_snapshot_trigger"] = time.time()
        return save_config(cfg)
    except Exception:
        return False

