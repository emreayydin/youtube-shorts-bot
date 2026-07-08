"""Generates a multi-fact compilation script (long-form 16:9 video) via Claude."""
import anthropic
import json
import random

from generate_content import CATEGORIES


PROMPT_TEMPLATE = """Du bist ein Autor für faszinierende YouTube-Wissensvideos.

Erstelle ein Skript für ein "Top 10"-Compilation-Video zum Thema: {category}
{avoid}
Regeln:
- Genau 10 verblüffende, wahre, möglichst unbekannte Fakten
- Jeder Fakt: 60-80 Wörter, lebendig und überraschend erzählt
- Intro: packender Einstieg (max 40 Wörter), der neugierig macht
- Outro: Frage an die Zuschauer + Aufruf zu abonnieren (max 35 Wörter)
- Sprache: Deutsch, direkt den Zuschauer ansprechen
- Reihenfolge: spannend aufbauen, der beste Fakt zuletzt

WICHTIG für gültiges JSON: Verwende NIEMALS doppelte Anführungszeichen (") innerhalb
der Texte — nutze stattdessen einfache (') oder gar keine. Keine Zeilenumbrüche in Werten.

BILD-PROMPTS (image_prompt / hook_visual): englische, cinematische KI-Bild-Prompts,
die den jeweiligen Inhalt illustrieren (Motiv, Schauplatz, Stimmung, Licht) — passend
zum Thema. KEINE Prominenten/Marken/Logos, KEIN Text im Bild.

Antworte NUR mit einem JSON-Objekt (keine Erklärung, kein Markdown):
{{
  "title": "Clickbait-Titel (max 70 Zeichen)",
  "topic": "Kurzes Thema (1-3 Wörter)",
  "intro": "Intro-Text",
  "hook_visual": "englischer cinematischer Bild-Prompt zum Thema",
  "facts": [
    {{"headline": "Kurze Überschrift (max 40 Zeichen)", "text": "Fakt-Text 60-80 Wörter", "image_prompt": "englischer cinematischer Bild-Prompt"}}
  ],
  "outro": "Outro-Text",
  "tags": ["tag1","tag2","tag3","tag4","tag5"],
  "category": "{category}"
}}

Die "facts"-Liste muss genau 10 Einträge haben."""


def generate_compilation(category: str = None, avoid: list[str] = None,
                         attempts: int = 3) -> dict:
    if category is None:
        category = random.choice(CATEGORIES)

    from history import avoid_block
    prompt = PROMPT_TEMPLATE.format(category=category, avoid=avoid_block(avoid or []))

    client = anthropic.Anthropic()
    last_err = None
    for attempt in range(attempts):
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            data = json.loads(raw.strip())
            if not data.get("facts"):
                raise ValueError("Keine Fakten generiert")
            return data
        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            print(f"Antwort ungültig (Versuch {attempt + 1}/{attempts}): {e} — wiederhole...")

    raise RuntimeError(f"Konnte nach {attempts} Versuchen kein gültiges Skript erzeugen: {last_err}")


if __name__ == "__main__":
    comp = generate_compilation()
    print(f"Titel: {comp['title']}")
    print(f"Fakten: {len(comp['facts'])}")
    for i, f in enumerate(comp["facts"], 1):
        print(f"  {i}. {f['headline']}")
