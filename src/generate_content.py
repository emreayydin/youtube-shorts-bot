"""Generates trivia facts using the Claude API."""
import anthropic
import json
import random


CATEGORIES = [
    "Wissenschaft", "Geschichte", "Natur", "Technologie",
    "Weltrekorde", "Psychologie", "Astronomie", "Biologie",
]

PROMPT_TEMPLATE = """Du bist ein Trivia-Experte für YouTube Shorts.

Erstelle einen einzelnen, faszinierenden Fakt über das Thema: {category}

Regeln:
- Maximal 150 Wörter
- Beginne mit einer packenden Aussage (kein "Wusstest du?")
- Überraschend, unbekannt, aber wahr
- Sprich direkt den Zuschauer an
- Ende mit einem Cliffhanger-Satz der neugierig macht
- Sprache: Deutsch

Antworte NUR mit einem JSON-Objekt:
{{
  "title": "Kurzer, clickbait-artiger Titel (max 60 Zeichen)",
  "hook": "Erster Satz zum Einhaken (max 15 Wörter)",
  "body": "Haupttext des Fakts",
  "cta": "Call-to-action Satz",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "category": "{category}"
}}"""


def generate_fact(category: str = None) -> dict:
    if category is None:
        category = random.choice(CATEGORIES)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(category=category)}],
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
