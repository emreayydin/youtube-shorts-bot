"""Generates trivia facts with a local bank and an optional text API."""
import json
import os
import random


CATEGORIES = [
    "Wissenschaft", "Geschichte", "Natur", "Technologie",
    "Weltrekorde", "Psychologie", "Astronomie", "Biologie",
]

PROMPT_TEMPLATE = """Du bist Experte für virale YouTube Shorts und schreibst fesselnde Trivia.

Erstelle einen einzelnen, faszinierenden Fakt über das Thema: {category}
{avoid}
Die ersten 2 Sekunden entscheiden alles. Der HOOK muss ein Pattern-Interrupt sein:
- Maximal 8 Wörter, extrem zugespitzt
- Erzeugt eine Wissenslücke ("Curiosity Gap") die man füllen MUSS
- Niemals "Wusstest du?" oder "Stell dir vor"
- Gute Muster: schockierende Zahl, scheinbarer Widerspruch, "Das ist verboten weil…", "Niemand glaubt dass…"

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
        category = random.choice(CATEGORIES)

    from history import avoid_block
    prompt = PROMPT_TEMPLATE.format(category=category, avoid=avoid_block(avoid or []))

    # Scheduled uploads use the local, curated bank. An API is an opt-in
    # experiment and never a prerequisite for producing a video.
    if os.environ.get("ANTHROPIC_ENABLED", "0") != "1" or not os.environ.get("ANTHROPIC_API_KEY"):
        from local_content import generate_fact as local_generate_fact
        return local_generate_fact(category, avoid)

    import anthropic
    client = anthropic.Anthropic()
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
