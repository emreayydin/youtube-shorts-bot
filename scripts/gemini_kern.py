"""Gemini-Aufrufe fuer das woechentliche Nachfuellen der Sammlungen.

Seit 06.10.2026: Die Sammlungen werden montags auf GitHub mit Gemini
nachgefuellt, damit Emres Mac dafuer nicht laufen muss. Schluessel:
GEMINI_API_KEY (Google AI Studio, kostenloses Kontingent).

Gleiche Datei in youtube-shorts-bot, muslim-world-bot und versus.

Schutz gegen erfundene Fakten (das lokale Modell lag am 01.10. bei 1 von 18):
pruefen() laesst jeden Eintrag in einem eigenen Aufruf gegenlesen - und zwar
gegen echten Text, den das Skript selbst holt (Wikipedia-Artikel, Korantext).
Nur "ok": true kommt in die Sammlung. Danach greifen die festen Pruefungen
des jeweiligen Kanals.

Kostenloses Kontingent (getestet 06.10.2026): Flash-Modelle antworten, die
Google-Suche und die Pro-Modelle liefern 429 "quota exceeded". Deshalb ist
die Suche standardmaessig aus (GEMINI_SUCHE=1 schaltet sie ein) und Pro nur
mit GEMINI_PRO=1 - etwa wenn spaeter ein bezahlter Schluessel hinterlegt ist.
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


def _anfrage(pfad, daten=None, versuche=3):
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
            if fehler.code in (500, 503) and versuch < versuche - 1:
                time.sleep(20 * (versuch + 1))
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
            if "-flash" not in name and not ("-pro" in name and os.environ.get("GEMINI_PRO") == "1"):
                continue
            brauchbar.append(name)
        brauchbar.sort(key=lambda n: (_version(n), "-pro" in n, "preview" not in n), reverse=True)
        _modelle = brauchbar[:6]
        print("Gemini-Modelle:", ", ".join(_modelle))
    return _modelle


SUCHE = os.environ.get("GEMINI_SUCHE") == "1"


def frage(text, suche=None, temperatur=0.7):
    """Ein Aufruf; wechselt bei Kontingent- oder Modellfehlern zum naechsten Modell."""
    letzter = None
    for modell in modelle():
        daten = {"contents": [{"role": "user", "parts": [{"text": text}]}],
                 "generationConfig": {"temperature": temperatur}}
        if SUCHE if suche is None else suche:
            daten["tools"] = [{"google_search": {}}]
        try:
            antwort = _anfrage(f"models/{modell}:generateContent", daten)
        except urllib.error.HTTPError as fehler:
            try:
                meldung = json.loads(fehler.read()).get("error", {}).get("message", "")
            except Exception:  # noqa: BLE001
                meldung = ""
            letzter = f"{modell}: HTTP {fehler.code} {meldung[:300]}"
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
        "You are a strict fact checker. Check EVERY factual claim, number, date, name "
        "and source reference in the entry below against the REFERENCE TEXT. "
        f"{hinweis}\n"
        "Answer ONLY with JSON: {\"ok\": true|false, \"reason\": \"short\"}. "
        "ok is true only if every claim is directly supported by the reference text. "
        "If anything is wrong, doubtful, exaggerated, or simply not in the reference "
        "text, ok is false - your own memory does not count as support.\n\n"
        f"{zusatz}\nENTRY:\n{json.dumps(eintrag, ensure_ascii=False, indent=1)}")
    try:
        urteil = json_aus(frage(auftrag, temperatur=0.0))
    except (ValueError, RuntimeError) as fehler:
        print("  Pruefung gescheitert:", fehler)
        return False, str(fehler)
    return urteil.get("ok") is True, str(urteil.get("reason", ""))[:200]


def wiki_text(angabe, zeichen=12000):
    """Klartext eines Wikipedia-Artikels, angegeben als "de:Titel" oder "en:Titel"."""
    import urllib.parse
    sprache, _, titel = str(angabe).partition(":")
    if sprache not in ("de", "en") or not titel.strip():
        return ""
    url = (f"https://{sprache}.wikipedia.org/w/api.php?action=query&prop=extracts"
           f"&explaintext=1&redirects=1&format=json&titles={urllib.parse.quote(titel.strip())}")
    req = urllib.request.Request(url, headers={"User-Agent": "faktastisch-bot/1.0 (github.com/emreayydin)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            seiten = json.loads(r.read())["query"]["pages"]
    except Exception:  # noqa: BLE001 - Netz/Format: gilt als nicht gefunden
        return ""
    text = next(iter(seiten.values())).get("extract", "") or ""
    return text[:zeichen]


def schreibe_modul(pfad, name, eintraege, kopf):
    """Neue Eintraege als Python-Modul ablegen (eine Liste, vollstaendig neu geschrieben)."""
    import pprint
    text = f'"""{kopf}"""\n\n{name} = ' + pprint.pformat(eintraege, width=100, sort_dicts=False) + "\n"
    compile(text, str(pfad), "exec")
    pfad.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    # Diagnose: je ein Aufruf mit und ohne Google-Suche pro Modell.
    for m in modelle():
        for suche in (False, True):
            _modelle = [m]
            try:
                print(m, "Suche" if suche else "ohne", "->", frage("Say OK.", suche=suche)[:40])
            except RuntimeError as f:
                print(m, "Suche" if suche else "ohne", "->", f)
