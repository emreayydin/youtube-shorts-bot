"""Generates trivia facts with a local bank and an optional text API."""
import json
import os
import random


CATEGORIES = [
    "Wissenschaft", "Geschichte", "Natur", "Technologie",
    "Weltrekorde", "Psychologie", "Astronomie", "Biologie",
]

# Gewichte aus den eigenen Zahlen (100 Shorts, Stand 16.09.2026, Median der
# Aufrufe je Kategorie): Weltrekorde 573, Geschichte 265, Wissenschaft 256,
# Astronomie 247, Natur 150, Biologie 94, Psychologie 64, Technologie 35.
# Vorher war die Wahl gleichverteilt - unter den letzten 60 Shorts waren 11
# zu Technologie und 2 zu Weltrekorden. Jede Kategorie behaelt einen kleinen
# Anteil, damit sich weiter messen laesst, ob sich das Bild aendert.
CATEGORY_WEIGHTS = {
    "Weltrekorde": 30, "Geschichte": 15, "Wissenschaft": 15, "Astronomie": 15,
    "Natur": 10, "Biologie": 6, "Psychologie": 5, "Technologie": 4,
}


def pick_category() -> str:
    namen = list(CATEGORY_WEIGHTS)
    return random.choices(namen, weights=[CATEGORY_WEIGHTS[n] for n in namen])[0]

PROMPT_TEMPLATE = """Du bist Experte für virale YouTube Shorts und schreibst fesselnde Trivia.

Erstelle einen einzelnen, faszinierenden Fakt über das Thema: {category}
{avoid}
Die ersten 2 Sekunden entscheiden alles. Der HOOK muss ein Pattern-Interrupt sein:
- Maximal 8 Wörter, extrem zugespitzt
- Erzeugt eine Wissenslücke ("Curiosity Gap") die man füllen MUSS
- Niemals "Wusstest du?" oder "Stell dir vor"
- Gute Muster: schockierende Zahl, scheinbarer Widerspruch, "Das ist verboten weil…", "Niemand glaubt dass…"

Diese TITEL liefen auf dem Kanal am besten (je rund 1.000 Aufrufe, der Schnitt
liegt bei 180) - uebernimm das Muster, nicht den Inhalt:
- "Dieser Weltrekord dauerte 0,00000001 Sekunden"   (konkrete, absurde Zahl)
- "Ein Tag auf der Venus dauert länger als ihr Jahr" (Widerspruch in einem Satz)
- "Dieser Fluss fließt – unter dem Meer"             (Gedankenstrich vor der Wendung)
- "Dieser Weltrekord wurde nie angetreten – absichtlich"
Schwach liefen reine Aussagen ohne Wendung ("Honig kann sehr lange haltbar
bleiben", 2 Aufrufe).

Body-Regeln:
- Maximal 130 Wörter, in kurzen gesprochenen Sätzen
- Steigt sofort ein, kein Aufwärmen
- Überraschend, unbekannt, aber faktisch wahr
- Baut Spannung auf, löst sie erst spät auf
- Sprache: Deutsch, direkte Ansprache (du)

BILD-PROMPTS (image_prompts): 4 englische, cinematische KI-Bild-Prompts, die den
Fakt illustrieren (Motiv, Schauplatz, Stimmung, Licht) — passend zum Thema. KEINE
Prominenten/Marken/Logos, KEIN Text im Bild. Reihenfolge = Erzählverlauf.

Antworte NUR mit einem JSON-Objekt:
{{
  "title": "Clickbait-Titel mit Zahl oder Widerspruch (max 60 Zeichen)",
  "hook": "Schock-Hook, max 8 Wörter",
  "body": "Haupttext des Fakts",
  "cta": "Kurzer Aufruf zu Folgen/Kommentieren",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "image_prompts": ["englischer Bild-Prompt 1", "2", "3", "4"],
  "category": "{category}"
}}"""


def generate_fact(category: str = None, avoid: list[str] = None, attempts: int = 3) -> dict:
    if category is None:
        category = pick_category()

    from history import avoid_block
    prompt = PROMPT_TEMPLATE.format(category=category, avoid=avoid_block(avoid or []))

    # Scheduled uploads use the local, curated bank. An API is an opt-in
    # experiment and never a prerequisite for producing a video.
    if os.environ.get("ANTHROPIC_ENABLED", "0") != "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        from local_content import generate_fact as local_generate_fact
        return local_generate_fact(category, avoid)

    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception as e:  # noqa: BLE001 - fehlendes Paket darf keinen Lauf kippen
        print(f"anthropic nicht nutzbar ({e}) - lokale Bank")
        from local_content import generate_fact as _lokal
        return _lokal(category, avoid)
    last_err = None
    for attempt in range(attempts):
        try:
            message = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            # Neuere Modelle koennen vor dem Text einen Denk-Block liefern.
            raw = next(b.text for b in message.content
                       if getattr(b, "type", "") == "text").strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw.strip())
            if not data.get("body"):
                raise ValueError("Kein Fakt-Text generiert")
            title = str(data.get("title", "")).strip().lower()
            if title in {str(x).strip().lower() for x in (avoid or [])}:
                raise ValueError(f"Titel schon gepostet: {data.get('title')}")
            return data
        except Exception as e:  # noqa: BLE001 - Netz, Guthaben, JSON: Bank greift
            last_err = e
            print(f"Versuch {attempt + 1}/{attempts} gescheitert: {e}")

    print(f"Anthropic nicht verfuegbar ({last_err}) - nutze lokale Faktenbank")
    from local_content import generate_fact as local_generate_fact
    return local_generate_fact(category, avoid)


if __name__ == "__main__":
    fact = generate_fact()
    print(json.dumps(fact, ensure_ascii=False, indent=2))
