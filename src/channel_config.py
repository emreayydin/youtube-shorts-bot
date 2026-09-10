"""Explicit channel profiles used to prevent silent cross-channel uploads."""

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHANNELS_FILE = ROOT / "config" / "channels.json"


def _load_channels() -> dict:
    with CHANNELS_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def active_channel() -> dict:
    """Return the selected channel profile; default keeps the old Faktisch bot."""
    mode = os.environ.get("CHANNEL_MODE", "faktisch").strip().lower()
    channels = _load_channels()
    try:
        channel = dict(channels[mode])
    except KeyError as exc:
        choices = ", ".join(sorted(channels))
        raise ValueError(f"Unbekannter CHANNEL_MODE {mode!r}; erwartet: {choices}") from exc
    channel["mode"] = mode
    return channel


def channel_verification_enabled() -> bool:
    """Guard is mandatory for the finance channel and opt-in for legacy runs."""
    value = os.environ.get("VERIFY_CHANNEL_ID", "").strip().lower()
    return active_channel()["mode"] == "difference_money" or value in {"1", "true", "yes", "on"}
