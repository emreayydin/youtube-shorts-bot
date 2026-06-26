"""Persistent history of posted videos so the bot never repeats a topic.

Stored as history.json in the repo root and committed back after each run by the
GitHub Actions workflow, so every run sees what previous runs already produced.
"""
import json
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path(__file__).resolve().parent.parent / "history.json"


def _load() -> list[dict]:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []


def recent_titles(n: int = 40, kind: str = None) -> list[str]:
    """Returns the titles of the last `n` entries (optionally filtered by kind)."""
    items = _load()
    if kind:
        items = [x for x in items if x.get("kind") == kind]
    return [x["title"] for x in items[-n:] if x.get("title")]


def add_entry(kind: str, title: str, category: str = "") -> None:
    """Appends a posted item (kind = 'short' or 'long'). Keeps the last 500."""
    items = _load()
    items.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "kind": kind,
        "category": category,
        "title": title,
    })
    HISTORY_FILE.write_text(json.dumps(items[-500:], ensure_ascii=False, indent=2))


def avoid_block(titles: list[str]) -> str:
    """Builds a prompt snippet telling the model which topics to avoid."""
    if not titles:
        return ""
    joined = "\n".join(f"- {t}" for t in titles[-30:])
    return ("\n\nDIESE THEMEN GAB ES SCHON — wähle etwas KOMPLETT anderes "
            f"(kein ähnliches Thema, keine Umformulierung):\n{joined}\n")
