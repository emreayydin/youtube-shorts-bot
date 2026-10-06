"""Gemini-Aufrufe fuer das woechentliche Nachfuellen der Sammlungen.

Seit 06.10.2026: Die Sammlungen werden montags auf GitHub mit Gemini
nachgefuellt, damit Emres Mac dafuer nicht laufen muss. Schluessel:
GEMINI_API_KEY (Google AI Studio, kostenloses Kontingent).

Gleiche Datei in youtube-shorts-bot, muslim-world-bot und versus.

Zwei Schutzschichten gegen erfundene Fakten (das lokale Modell lag am
01.10. bei 1 von 18):
1. erzeugen() schreibt mit eingeschalteter Google-Suche, also an echten
   Quellen entlang statt aus dem Gedaechtnis.
2. pruefen() laesst jeden Eintrag in einem eigenen Aufruf, wieder mit
   Suche, gegenlesen. Nur "ok": true kommt in die Sammlung.
Danach greifen die festen Pruefungen des jeweiligen Kanals.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
PAUSE = float(os.environ.get("GEMINI_PAUSE_SEC", "13"))   # kostenloses Kontingent: wenige Aufrufe/Minute

_modelle = None


def _anfrage(pfad, daten=None, versuche=4):
    schluessel = os.environ.get("GEMINI_API_KEY", "")
    if not schluessel:
        raise SystemExit("GEMINI_API_KEY fehlt")
    for versuch in range(versuche):
        req = urllib.request.Request(
            f"{API}/{pfad}",
            data=json.dumps(daten).encode() if daten is not None else None,
            headers={"x-goog-api-key": schluessel, "Content-Type": "application/json"},
            method="POST" if daten is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=300) as antwort:
                return json.loads(antwort.read())
        except urllib.error.HTTPError as fehler:
            if fehler.code in (429, 500, 503) and versuch < versuche - 1:
                time.sleep(30 * (versuch + 1))
                continue
            raise


def _version(name):
    zahl = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(zahl.group(1)) if zahl else 0.0


def modelle():
    """Verfuegbare Textmodelle, bestes zuerst (neueste Version, Pro vor Flash)."""
    global _modelle
    if _modelle is None:
        liste = _anfrage("models?pageSize=200").get("models", [])
        brauchbar = []
        for m in liste:
            name = m["name"].split("/")[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if not name.startswith("gemini-") or any(
                    x in name for x in ("tts", "image", "embedding", "live", "lite", "audio", "robotics", "computer")):
                continue
            if "-pro" not in name and "-flash" not in name:
                continue
            brauchbar.append(name)
        brauchbar.sort(key=lambda n: (_version(n), "-pro" in n, "preview" not in n), reverse=True)
        _modelle = brauchbar[:6]
        print("Gemini-Modelle:", ", ".join(_modelle))
    return _modelle


def frage(text, suche=True, temperatur=0.7):
    """Ein Aufruf; wechselt bei Kontingent- oder Modellfehlern zum naechsten Modell."""
    letzter = None
    for modell in modelle():
        daten = {"contents": [{"role": "user", "parts": [{"text": text}]}],
                 "generationConfig": {"temperature": temperatur}}
        if suche:
            daten["tools"] = [{"google_search": {}}]
        try:
            antwort = _anfrage(f"models/{modell}:generateContent", daten)
        except urllib.error.HTTPError as fehler:
            letzter = f"{modell}: HTTP {fehler.code}"
            print("  ", letzter)
            continue
        finally:
            time.sleep(PAUSE)
        teile = (((antwort.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        inhalt = "".join(t.get("text", "") for t in teile)
        if inhalt.strip():
            return inhalt
        letzter = f"{modell}: leere Antwort"
    raise RuntimeError(f"Kein Gemini-Modell antwortete ({letzter})")


def json_aus(text):
    """JSON aus einer Antwort ziehen - mit Suche gibt es keinen festen JSON-Modus."""
    block = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    roh = block.group(1) if block else text
    for auf, zu in (("[", "]"), ("{", "}")):
        i, j = roh.find(auf), roh.rfind(zu)
        if i >= 0 and j > i:
            try:
                return json.loads(roh[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("keine JSON-Antwort")


def erzeugen(auftrag):
    """Liste neuer Eintraege (dicts). Fehlerhafte Antworten ergeben eine leere Liste."""
    try:
        daten = json_aus(frage(auftrag))
    except (ValueError, RuntimeError) as fehler:
        print("  Erzeugen gescheitert:", fehler)
        return []
    return [x for x in (daten if isinstance(daten, list) else [daten]) if isinstance(x, dict)]


def pruefen(eintrag, hinweis="", zusatz=""):
    """Unabhaengiges Gegenlesen mit Google-Suche. True nur bei klarer Bestaetigung."""
    auftrag = (
        "You are a strict fact checker. Use Google Search. Check EVERY factual claim, "
        "number, date, name and source reference in the entry below. "
        f"{hinweis}\n"
        "Answer ONLY with JSON: {\"ok\": true|false, \"reason\": \"short\"}. "
        "ok is true only if every claim is confirmed by reliable sources and the cited "
        "source exists and supports it. If anything is wrong, doubtful, exaggerated or "
        "unverifiable, ok is false.\n\n"
        f"{zusatz}\nENTRY:\n{json.dumps(eintrag, ensure_ascii=False, indent=1)}")
    try:
        urteil = json_aus(frage(auftrag, temperatur=0.0))
    except (ValueError, RuntimeError) as fehler:
        print("  Pruefung gescheitert:", fehler)
        return False, str(fehler)
    return urteil.get("ok") is True, str(urteil.get("reason", ""))[:200]


def schreibe_modul(pfad, name, eintraege, kopf):
    """Neue Eintraege als Python-Modul ablegen (eine Liste, vollstaendig neu geschrieben)."""
    import pprint
    text = f'"""{kopf}"""\n\n{name} = ' + pprint.pformat(eintraege, width=100, sort_dicts=False) + "\n"
    compile(text, str(pfad), "exec")
    pfad.write_text(text, encoding="utf-8")
