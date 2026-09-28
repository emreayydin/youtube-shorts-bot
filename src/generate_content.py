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
# Stand 20.09.2026, Median der Aufrufe reifer Videos je Kategorie:
# Geschichte 256, Astronomie 239, Wissenschaft 171, Weltrekorde 166,
# Natur 130, Biologie 117, Psychologie 64, Technologie 35.
# Stand 28.09.2026, Shorts vom 17.-26.09. (n=42, Median je Kategorie):
# Astronomie 237 (7), Natur 105 (5), Weltrekorde 10 (10), Biologie 5 (5),
# Geschichte 3 (10). Kanal gesamt: Astronomie 235, Wissenschaft 171, Natur 119,
# Geschichte 101. Astronomie ist in beiden Zeitraeumen vorn, Geschichte faellt.
CATEGORY_WEIGHTS = {
    "Astronomie": 30, "Natur": 20, "Wissenschaft": 15, "Geschichte": 12,
    "Weltrekorde": 10, "Biologie": 6, "Psychologie": 4, "Technologie": 3,
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

Diese TITEL liefen auf dem Kanal am besten (Median liegt bei 160 Aufrufen):
- "Dieser Römische Kaiser regierte – 6 Stunden lang"      1.600
- "Dieser Ozean brennt – unter dem Meeresgrund"           1.200
- "Dein Körper tötet sich selbst – jeden Tag Milliarden Male"  1.200
- "Dein Gehirn erfindet 40% deiner Erinnerungen"          1.100
- "Dieser Weltrekord wurde aus Versehen gebrochen"        1.100
Gemeinsam ist ihnen der INHALT, nicht die Schreibweise: eine einzelne,
nachpruefbare Behauptung, die dem gesunden Menschenverstand widerspricht,
mit einer konkreten Zahl, Zeit oder Menge.

Diese liefen am schlechtesten (1 bis 3 Aufrufe):
- "Blitze sind heißer als die Sonnenoberfläche"   (kennt jeder)
- "Honig kann sehr lange haltbar bleiben"         (vage: "sehr lange")
- "Oxford ist älter als das Aztekenreich"         (kein Bild im Kopf)

Der Gedankenstrich ist KEINE Regel. Im selben Zeitraum gemessen liegen Titel
mit Gedankenstrich bei 119 Aufrufen, Titel ohne bei 256. Schreib den Titel so,
wie der Fakt es verlangt.

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


# Wie im Muslim-World-Bot: freies JSON scheiterte an langen Texten mit
# Anfuehrungszeichen. Ein Werkzeug-Schema liefert strukturierte Felder.
FACT_TOOL = {
    "name": "fakt",
    "description": "Ein Trivia-Fakt fuer ein deutsches YouTube Short.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "hook": {"type": "string"},
            "body": {"type": "string"},
            "cta": {"type": "string"},
            "category": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "image_prompts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["title", "hook", "body", "tags", "image_prompts"],
    },
}


def _unwrap(payload):
    for _ in range(4):
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return payload
            continue
        if isinstance(payload, dict) and "title" not in payload and len(payload) == 1:
            payload = next(iter(payload.values()))
            continue
        break
    return payload

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
                tools=[FACT_TOOL],
                tool_choice={"type": "tool", "name": "fakt"},
                messages=[{"role": "user", "content": prompt}],
            )
            data = next((_unwrap(b.input) for b in message.content
                         if getattr(b, "type", "") == "tool_use"), None)
            if not isinstance(data, dict):
                raise ValueError("keine strukturierte Antwort")
            if not data.get("body"):
                raise ValueError("Kein Fakt-Text generiert")
            title = str(data.get("title", "")).strip().lower()
            if title in {str(x).strip().lower() for x in (avoid or [])}:
                raise ValueError(f"Titel schon gepostet: {data.get('title')}")
            data.setdefault("category", category)
            data.setdefault("cta", "Folge fuer taegliche Fakten.")
            return data
        except Exception as e:  # noqa: BLE001 - Netz, Guthaben, Schema: Bank greift
            last_err = e
            print(f"Versuch {attempt + 1}/{attempts} gescheitert: {e}")

    print(f"Anthropic nicht verfuegbar ({last_err}) - nutze lokale Faktenbank")
    from local_content import generate_fact as local_generate_fact
    return local_generate_fact(category, avoid)


if __name__ == "__main__":
    fact = generate_fact()
    print(json.dumps(fact, ensure_ascii=False, indent=2))
