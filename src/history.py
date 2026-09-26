"""Persistent history of posted videos so the bot never repeats a topic.

Stored as history.json in the repo root and committed back after each run by the
GitHub Actions workflow, so every run sees what previous runs already produced.
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

def _history_file() -> Path:
    """Eigene Historie je Kanal.

    Bis 20.09.2026 teilten sich Faktastisch und The Difference Money eine
    Datei. Das Tageslimit und der Mindestabstand rechneten damit ueber beide
    Kanaele: Ein Faktastisch-Upload eine Stunde zuvor liess den
    Vergleichs-Workflow "nur 1.0h seit letztem Upload" melden und aussetzen.
    Beide Kanaele haengen an verschiedenen Google-Projekten und haben
    deshalb auch getrennte Kontingente.
    """
    import os
    wurzel = Path(__file__).resolve().parent.parent
    mode = os.environ.get("CHANNEL_MODE", "faktisch").strip().lower()
    if mode and mode != "faktisch":
        return wurzel / f"history_{mode}.json"
    return wurzel / "history.json"



# YouTube's daily upload quota resets at midnight US Pacific. We approximate that
# boundary at 08:00 UTC (exact in winter PST; 1h off in summer PDT — harmless
# since each window still stays under quota). Used to count uploads per day.
QUOTA_RESET_UTC_HOUR = 8


def _load() -> list[dict]:
    datei = _history_file()
    if datei.exists():
        try:
            return json.loads(datei.read_text())
        except Exception:
            return []
    return []


def recent_titles(n: int = 40, kind: str = None) -> list[str]:
    """Returns the titles of the last `n` entries (optionally filtered by kind)."""
    items = _load()
    if kind:
        items = [x for x in items if x.get("kind") == kind]
    return [x["title"] for x in items[-n:] if x.get("title")]


def all_titles() -> set[str]:
    """Jeder jemals gepostete Titel, klein geschrieben.

    recent_titles(40) reichte nicht: Die lokale Bank hat 16 Fakten, und
    YouTube zeigte am 16.09. "Der Eiffelturm waechst im Sommer" fuenfmal auf
    dem Kanal - die Wiederholungen lagen bei 1 bis 2 Aufrufen.
    """
    return {x["title"].strip().lower() for x in _load() if x.get("title")}


def add_entry(kind: str, title: str, category: str = "") -> None:
    """Appends a posted item (kind = 'short' or 'long'). Keeps the last 500."""
    items = _load()
    items.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ts_utc": datetime.now(timezone.utc).isoformat(),  # for quota/spacing logic
        "kind": kind,
        "category": category,
        "title": title,
    })
    _history_file().write_text(json.dumps(items[-500:], ensure_ascii=False, indent=2))


# ---------- quota / spacing helpers (reliable pacing under a flaky cron) ----------

def _quota_day_key(dt_utc: datetime):
    return (dt_utc - timedelta(hours=QUOTA_RESET_UTC_HOUR)).date()


def _parse_ts(entry: dict):
    ts = entry.get("ts_utc")
    if not ts:
        return None
    try:
        d = datetime.fromisoformat(ts)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def uploads_in_current_window(kind: str = None) -> int:
    """How many videos were uploaded in the current quota day (optionally by kind)."""
    key = _quota_day_key(datetime.now(timezone.utc))
    n = 0
    for x in _load():
        d = _parse_ts(x)
        if d and _quota_day_key(d) == key and (kind is None or x.get("kind") == kind):
            n += 1
    return n


def hours_since_last_upload():
    """Hours since the most recent upload, or None if there is no dated history."""
    now = datetime.now(timezone.utc)
    latest = None
    for x in _load():
        d = _parse_ts(x)
        if d and (latest is None or d > latest):
            latest = d
    return None if latest is None else (now - latest).total_seconds() / 3600


def avoid_block(titles: list[str]) -> str:
    """Builds a prompt snippet telling the model which topics to avoid."""
    if not titles:
        return ""
    joined = "\n".join(f"- {t}" for t in titles[-30:])
    return ("\n\nDIESE THEMEN GAB ES SCHON — wähle etwas KOMPLETT anderes "
            f"(kein ähnliches Thema, keine Umformulierung):\n{joined}\n")
