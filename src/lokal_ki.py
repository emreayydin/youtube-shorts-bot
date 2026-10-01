"""Claude-Aufrufe kostenlos auf das lokale Modell (Ollama) umleiten.

Die Pipeline ruft ueberall `anthropic.Anthropic().messages.create(...)` auf.
Diese Datei ersetzt genau diese eine Methode, wenn ANTHROPIC_BASE_URL auf den
eigenen Rechner zeigt - die Aufrufstellen bleiben unveraendert.

Warum nicht einfach Ollamas eingebaute Claude-Schnittstelle (/v1/messages)?
Getestet am 01.10.2026 mit gemma4:26b: Sie erzwingt kein Werkzeug. Statt der
verlangten Felder kam freier Text zurueck, einmal sogar eine Rueckfrage
("Wie war das Ergebnis des Tests?"). Die native Schnittstelle /api/chat kann
dagegen ein JSON-Schema als Grammatik vorgeben - das Modell kann dann gar
nichts anderes erzeugen als gueltige Felder. Deshalb laeuft jeder Aufruf mit
Werkzeug ueber `format=<input_schema>`.

Ohne Werkzeug wird normaler Text zurueckgegeben. Das "Nachdenken" des Modells
ist abgeschaltet: Es kostete Zeit und frass bei kleinem max_tokens die ganze
Antwort auf.
"""
import json
import os
import uuid
from types import SimpleNamespace

import requests

MODELL_STANDARD = "gemma4:26b"
KONTEXT = int(os.environ.get("LOKALE_KI_KONTEXT", "16384"))
ZEITLIMIT = int(os.environ.get("LOKALE_KI_ZEITLIMIT", "600"))


def _basis():
    return os.environ.get("ANTHROPIC_BASE_URL", "http://localhost:11434").rstrip("/")


def _text(inhalt):
    """Claude-Inhalt (String oder Liste von Bloecken) -> reiner Text."""
    if isinstance(inhalt, str):
        return inhalt
    teile = []
    for block in inhalt or []:
        if isinstance(block, dict):
            if block.get("type") == "text":
                teile.append(block.get("text", ""))
            elif block.get("type") == "tool_result":
                teile.append(_text(block.get("content")))
        elif getattr(block, "type", "") == "text":
            teile.append(block.text)
    return "\n".join(t for t in teile if t)


def _schema_ohne_grenzen(schema):
    """minItems/maxItems u. ae. kennt die Grammatik nicht zuverlaessig - raus.

    Die Pipeline prueft Laengen ohnehin selbst nach (_sanitize & Co.).
    """
    if isinstance(schema, dict):
        return {k: _schema_ohne_grenzen(v) for k, v in schema.items()
                if k not in ("minItems", "maxItems", "minLength", "maxLength")}
    if isinstance(schema, list):
        return [_schema_ohne_grenzen(x) for x in schema]
    return schema


def erzeuge(*, model=None, messages, system=None, tools=None, tool_choice=None,
            max_tokens=1024, temperature=None, **_unbenutzt):
    """Ersatz fuer messages.create - gleiche Rueckgabeform wie die Anthropic-SDK."""
    verlauf = []
    if system:
        verlauf.append({"role": "system", "content": _text(system)})
    for nachricht in messages:
        verlauf.append({"role": nachricht["role"], "content": _text(nachricht["content"])})

    werkzeug = None
    if tools:
        name = (tool_choice or {}).get("name") if isinstance(tool_choice, dict) else None
        werkzeug = next((t for t in tools if t.get("name") == name), tools[0])
        verlauf.append({"role": "user", "content":
                        f"Antworte ausschliesslich mit den Feldern fuer '{werkzeug['name']}' "
                        f"({werkzeug.get('description', '')})."})

    anfrage = {
        "model": (model if model and not str(model).startswith("claude") else
                  os.environ.get("ANTHROPIC_MODEL", MODELL_STANDARD)),
        "messages": verlauf,
        "stream": False,
        "think": False,
        "options": {"num_ctx": KONTEXT, "num_predict": int(max_tokens or 1024)},
    }
    if temperature is not None:
        anfrage["options"]["temperature"] = temperature
    if werkzeug:
        anfrage["format"] = _schema_ohne_grenzen(werkzeug["input_schema"])

    antwort = requests.post(f"{_basis()}/api/chat", json=anfrage, timeout=ZEITLIMIT)
    antwort.raise_for_status()
    daten = antwort.json()
    text = (daten.get("message") or {}).get("content", "")
    nutzung = SimpleNamespace(input_tokens=daten.get("prompt_eval_count", 0),
                              output_tokens=daten.get("eval_count", 0),
                              cache_read_input_tokens=0, cache_creation_input_tokens=0)

    if werkzeug:
        try:
            eingabe = json.loads(text)
        except json.JSONDecodeError as fehler:
            raise ValueError(f"lokale KI: kein gueltiges JSON ({fehler})") from fehler
        block = SimpleNamespace(type="tool_use", id=f"toolu_{uuid.uuid4().hex[:20]}",
                                name=werkzeug["name"], input=eingabe)
        return SimpleNamespace(content=[block], stop_reason="tool_use", usage=nutzung,
                               model=anfrage["model"])
    block = SimpleNamespace(type="text", text=text)
    grund = "max_tokens" if daten.get("done_reason") == "length" else "end_turn"
    return SimpleNamespace(content=[block], stop_reason=grund, usage=nutzung,
                           model=anfrage["model"])


def aktivieren():
    """Ersetzt Messages.create der Anthropic-SDK durch den lokalen Aufruf."""
    import anthropic.resources.messages as nachrichten

    def create(self, *args, **kwargs):
        return erzeuge(**kwargs)

    nachrichten.Messages.create = create
