"""Generates a multi-fact compilation script (long-form 16:9 video) via Claude."""
import anthropic
import json
import random

from generate_content import CATEGORIES


PROMPT_TEMPLATE = """Du bist ein Autor für faszinierende YouTube-Wissensvideos.

Erstelle ein Skript für ein "Top 10"-Compilation-Video zum Thema: {category}

Regeln:
- Genau 10 verblüffende, wahre, möglichst unbekannte Fakten
- Jeder Fakt: 60-80 Wörter, lebendig und überraschend erzählt
- Intro: packender Einstieg (max 40 Wörter), der neugierig macht
- Outro: Frage an die Zuschauer + Aufruf zu abonnieren (max 35 Wörter)
- Sprache: Deutsch, direkt den Zuschauer ansprechen
- Reihenfolge: spannend aufbauen, der beste Fakt zuletzt

Antworte NUR mit einem JSON-Objekt (keine Erklärung, kein Markdown):
{{
  "title": "Clickbait-Titel (max 70 Zeichen)",
  "topic": "Kurzes Thema (1-3 Wörter)",
  "intro": "Intro-Text",
  "facts": [
    {{"headline": "Kurze Überschrift (max 40 Zeichen)", "text": "Fakt-Text 60-80 Wörter"}}
  ],
  "outro": "Outro-Text",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "category": "{category}"
}}

Die "facts"-Liste muss genau 10 Einträge haben."""


def generate_compilation(category: str = None) -> dict:
    if category is None:
        category = random.choice(CATEGORIES)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(category=category)}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw.strip())

    # Safety: ensure facts list is non-empty
    if not data.get("facts"):
        raise ValueError("Keine Fakten generiert")
    return data


if __name__ == "__main__":
    comp = generate_compilation()
    print(f"Titel: {comp['title']}")
    print(f"Fakten: {len(comp['facts'])}")
    for i, f in enumerate(comp["facts"], 1):
        print(f"  {i}. {f['headline']}")
