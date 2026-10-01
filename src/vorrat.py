"""Vorrat an fertigen Texten, die der Mac nachts mit der lokalen KI schreibt.

Seit 01.10.2026 ruft der GitHub-Workflow keine bezahlte API mehr auf (Emre:
"lokal ohne Kosten"). GitHub erreicht den Mac nicht, deshalb laeuft es so:

  Mac (scripts/vorrat_fuellen.py, nachts):  schreibt je Text eine Datei
  GitHub (main.py, tagsueber):             nimmt die aelteste und loescht sie

Eine Datei pro Text, damit sich beide nie ins Gehege kommen: Der Mac legt nur
neue Dateien an, GitHub loescht nur - Git fuehrt das ohne Konflikt zusammen.
Ist der Vorrat leer, greift die lokale Faktenbank und laesst den Slot im
Zweifel aus (lieber kein Video als eine Wiederholung).
"""
import json
import re
from datetime import datetime
from pathlib import Path

ORDNER = Path(__file__).resolve().parent.parent / "vorrat"


def dateien():
    return sorted(ORDNER.glob("*.json")) if ORDNER.exists() else []


def titel():
    ergebnis = set()
    for f in dateien():
        try:
            ergebnis.add(json.loads(f.read_text(encoding="utf-8"))["title"].strip().lower())
        except (ValueError, KeyError, OSError):
            continue
    return ergebnis


def nimm(gesperrt, verbrauchen=True):
    """Aeltesten noch nicht geposteten Text liefern (und die Datei entfernen)."""
    gesperrt = {str(t).strip().lower() for t in gesperrt}
    for f in dateien():
        try:
            daten = json.loads(f.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            if verbrauchen:
                f.unlink(missing_ok=True)
            continue
        if str(daten.get("title", "")).strip().lower() in gesperrt:
            if verbrauchen:
                f.unlink(missing_ok=True)      # schon gepostet - nie wiederholen
            continue
        if verbrauchen:
            f.unlink(missing_ok=True)
        return daten
    return None


def lege_ab(daten):
    ORDNER.mkdir(parents=True, exist_ok=True)
    kurz = re.sub(r"[^a-z0-9]+", "-", str(daten.get("title", "")).lower()).strip("-")[:40]
    ziel = ORDNER / f"{datetime.now():%Y%m%d-%H%M%S-%f}-{kurz or 'text'}.json"
    ziel.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    return ziel
