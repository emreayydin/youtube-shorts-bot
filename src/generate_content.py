"""Generates trivia facts using the Claude API."""
import anthropic
import json
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

Antworte NUR mit einem JSON-Objekt:
{{
  "title": "Clickbait-Titel mit Zahl oder Widerspruch (max 60 Zeichen)",
  "hook": "Schock-Hook, max 8 Wörter",
  "body": "Haupttext des Fakts",
  "cta": "Kurzer Aufruf zu Folgen/Kommentieren",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "{category}"
}}"""


def generate_fact(category: str = None, avoid: list[str] = None) -> dict:
    if category is None:
        category = random.choice(CATEGORIES)

    from history import avoid_block
    prompt = PROMPT_TEMPLATE.format(category=category, avoid=avoid_block(avoid or []))

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip potential markdown code fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


if __name__ == "__main__":
    fact = generate_fact()
    print(json.dumps(fact, ensure_ascii=False, indent=2))
