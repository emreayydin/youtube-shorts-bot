#!/usr/bin/env python3
"""Vorrat fuer Faktastisch mit der lokalen KI auffuellen (laeuft auf dem Mac).

  venv/bin/python scripts/vorrat_fuellen.py            bis ZIEL auffuellen, committen, pushen
  venv/bin/python scripts/vorrat_fuellen.py --trocken  nur erzeugen und anzeigen

Kosten: keine. Die Anfragen gehen an Ollama auf diesem Rechner (lokal_ki.py).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))

ZIEL = int(os.environ.get("VORRAT_ZIEL", "18"))       # 3 Tage bei 6 Shorts/Tag

os.environ.update({"ANTHROPIC_ENABLED": "1", "ANTHROPIC_API_KEY": "lokal",
                   "ANTHROPIC_BASE_URL": "http://localhost:11434"})
os.environ.setdefault("ANTHROPIC_MODEL", "gemma4:26b")

import lokal_ki                      # noqa: E402
lokal_ki.aktivieren()
import generate_content as gen       # noqa: E402
import history                       # noqa: E402
import vorrat                        # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=WURZEL, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trocken", action="store_true")
    args = ap.parse_args()

    if not args.trocken:
        git("pull", "-q", "--rebase", "--autostash")
    fehlt = ZIEL - len(vorrat.dateien())
    print(f"Vorrat: {len(vorrat.dateien())}, Ziel {ZIEL}, erzeuge {max(0, fehlt)}")
    neu = 0
    for _ in range(max(0, fehlt) * 2):          # Puffer fuer verworfene Versuche
        if neu >= fehlt:
            break
        gesperrt = history.all_titles() | vorrat.titel()
        avoid = sorted(gesperrt) + history.recent_titles(150)
        try:
            fakt = gen.generate_fact(gen.pick_category(), avoid=avoid)
        except Exception as e:                   # noqa: BLE001 - naechster Versuch
            print("  verworfen:", e)
            continue
        if fakt["title"].strip().lower() in gesperrt or not fakt.get("body"):
            print("  verworfen: Dublette oder leer")
            continue
        if args.trocken:
            print(f"  [{fakt.get('category')}] {fakt['title']}")
            neu += 1
            continue
        vorrat.lege_ab(fakt); neu += 1
        print(f"  + [{fakt.get('category')}] {fakt['title']}")

    if args.trocken or neu == 0:
        return
    git("add", "vorrat")
    git("commit", "-q", "-m", f"Vorrat: {neu} neue Fakten (lokal erzeugt) [skip ci]")
    for _ in range(3):
        if git("pull", "-q", "--rebase", "--autostash").returncode == 0 and git("push", "-q").returncode == 0:
            print("gepusht"); return
    sys.exit("Push gescheitert")


if __name__ == "__main__":
    main()
