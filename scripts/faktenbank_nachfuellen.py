"""Faktastisch: Faktensammlung montags mit Gemini auffuellen (laeuft auf GitHub).

Ziel: mindestens ZIEL frische Fakten (Titel noch nie gepostet). Neue Fakten
landen in src/faktenbank_neu.py; local_content.py nimmt sie in die Auswahl.
Jeder Fakt wird mit Google-Suche geschrieben und unabhaengig gegengeprueft
(siehe gemini_kern.py). Ergebnis: Exitcode 0, auch wenn das Ziel nicht
erreicht wird - dann meldet der Lauf nur, wie viele fehlen.

    python scripts/faktenbank_nachfuellen.py            # auffuellen
    python scripts/faktenbank_nachfuellen.py --anzahl 3 # kleiner Test
"""
import argparse
import os
import random
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL / "src"))
sys.path.insert(0, str(WURZEL / "scripts"))

import gemini_kern as g  # noqa: E402
import history  # noqa: E402
import local_content  # noqa: E402
from generate_content import CATEGORY_WEIGHTS  # noqa: E402

NEU_DATEI = WURZEL / "src" / "faktenbank_neu.py"
ZIEL = int(os.environ.get("FAKTEN_ZIEL", "45"))
PRO_AUFRUF = 6
MAX_RUNDEN = 12

AUFTRAG = """Du schreibst Fakten fuer den deutschen YouTube-Shorts-Kanal "Faktastisch".
Nutze die Google-Suche und schreibe NUR Fakten, die du an zuverlaessigen Quellen
(Museen, Universitaeten, NASA/ESA, Britannica, Fachzeitschriften, Guinness)
belegt gefunden hast. Lieber weniger Fakten als ein unsicherer.

Schreibe {anzahl} neue Fakten aus der Kategorie "{kategorie}".

Diese Themen liefen schon - nimm keines davon, auch nicht mit neuem Titel:
{schon}

Format je Fakt:
- title: hoechstens 55 Zeichen, deutsch, macht neugierig, stimmt aber genau.
  Gut liefen z. B.: "Australien verlor einen Krieg gegen Emus",
  "Saturn wuerde in Wasser schwimmen". Keine Clickbait-Luegen.
- hook: ein Satz, hoechstens 60 Zeichen.
- body: 60 bis 95 Woerter, gesprochenes Deutsch, kurze Saetze, Zahlen und
  Namen genau. Keine Uebertreibung.
- cta: eine Frage an die Zuschauer.
- tags: 5 deutsche Schlagwoerter.
- sources: 1-2 echte Quellen als "Herausgeber: Titel".
- image_prompts: genau 4 englische Bildbeschreibungen, jede endet mit ", no text".

Antworte NUR mit einem JSON-Array dieser Objekte in einem ```json Block.
Jedes Objekt hat zusaetzlich "category": "{kategorie}"."""


def frische(alle):
    gepostet = {t.lower() for t in history.all_titles()}
    return [f for f in alle if f["title"].lower() not in gepostet]


def gueltig(f, bekannt):
    pflicht = ("title", "hook", "body", "cta", "tags", "sources", "image_prompts", "category")
    if any(not f.get(k) for k in pflicht):
        return "Feld fehlt"
    if f["title"].lower() in bekannt:
        return "Titel schon bekannt"
    if len(f["title"]) > 70:
        return "Titel zu lang"
    woerter = len(str(f["body"]).split())
    if not 45 <= woerter <= 120:
        return f"Text {woerter} Woerter"
    if f["category"] not in CATEGORY_WEIGHTS:
        return "unbekannte Kategorie"
    if not isinstance(f["image_prompts"], list) or len(f["image_prompts"]) != 4:
        return "image_prompts"
    if not isinstance(f["sources"], list) or not isinstance(f["tags"], list):
        return "sources/tags"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anzahl", type=int, help="hoechstens so viele neue Fakten")
    args = ap.parse_args()

    try:
        from faktenbank_neu import NEU
    except ImportError:
        NEU = []
    NEU = list(NEU)
    fehlend = max(0, ZIEL - len(frische(local_content.FACTS)))
    if args.anzahl is not None:
        fehlend = args.anzahl
    print(f"Frische Fakten: {len(frische(local_content.FACTS))}, Ziel {ZIEL}, fehlen {fehlend}")
    if not fehlend:
        return

    bekannt = {t.lower() for t in history.all_titles()} | {f["title"].lower() for f in local_content.FACTS}
    schon = sorted(bekannt)
    neu, verworfen = [], 0
    for runde in range(MAX_RUNDEN):
        if len(neu) >= fehlend:
            break
        namen = list(CATEGORY_WEIGHTS)
        kategorie = random.choices(namen, weights=[CATEGORY_WEIGHTS[n] for n in namen])[0]
        print(f"Runde {runde + 1}: {kategorie}")
        vorschlaege = g.erzeugen(AUFTRAG.format(
            anzahl=PRO_AUFRUF, kategorie=kategorie,
            schon="\n".join(f"- {t}" for t in schon[-400:])))
        for f in vorschlaege:
            if len(neu) >= fehlend:
                break
            f["category"] = kategorie
            grund = gueltig(f, bekannt)
            if grund:
                verworfen += 1
                print(f"  verworfen ({grund}): {f.get('title')}")
                continue
            ok, warum = g.pruefen(
                {k: f[k] for k in ("title", "hook", "body", "sources")},
                "The text is German. The title must be accurate, not misleading.")
            if not ok:
                verworfen += 1
                print(f"  Pruefung nein: {f['title']} - {warum}")
                continue
            print(f"  + {f['title']}")
            eintrag = {k: f[k] for k in ("category", "title", "hook", "body", "cta", "tags",
                                         "sources", "image_prompts")}
            neu.append(eintrag)
            bekannt.add(f["title"].lower())
            schon.append(f["title"].lower())

    if neu:
        g.schreibe_modul(NEU_DATEI, "NEU", NEU + neu,
                         "Von Gemini geschriebene und gegengepruefte Fakten "
                         "(scripts/faktenbank_nachfuellen.py). Nicht von Hand ordnen.")
    print(f"Ergebnis: {len(neu)} neu, {verworfen} verworfen, "
          f"noch fehlend {max(0, fehlend - len(neu))}")


if __name__ == "__main__":
    main()
