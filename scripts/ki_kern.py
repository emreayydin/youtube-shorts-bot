"""Kostenlose KI-Aufrufe fuer das Nachfuellen der Sammlungen (laeuft auf GitHub).

Seit 07.10.2026. Emre will die Kanaele kostenlos und ohne laufenden Mac.
Gleiche Datei in youtube-shorts-bot, muslim-world-bot und versus.

Anbieter, jeweils im kostenlosen Kontingent, mit automatischem Wechsel:
- Groq    (GROQ_API_KEY)    - gpt-oss-120b u. a., 1.000 Anfragen/Tag, keine Karte
- Mistral (MISTRAL_API_KEY) - optional; Emre nutzt es nicht (08.10.), ohne Schluessel uebersprungen
- Gemini  (GEMINI_API_KEY)  - nur Flash; am 06.10. stark ueberlastet, daher zuletzt
Fehlt ein Schluessel, wird der Anbieter uebersprungen. Schreiben und Pruefen
laufen moeglichst bei verschiedenen Anbietern - zwei Modellfamilien sehen
mehr Fehler als eine.

Schutz gegen erfundene Fakten (das lokale Modell lag am 01.10. bei 1 von 18):
pruefen() liest jeden Eintrag gegen echten Text, den das Skript selbst holt
(Wikipedia-Artikel, Korantext). Nur "ok": true kommt in die Sammlung. Danach
greifen die festen Pruefungen des jeweiligen Kanals.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ZEITLIMIT = 180
_katalog = {}

ANBIETER = {
    "groq": {
        "schluessel": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1",
        # bevorzugte Modelle, in dieser Reihenfolge; gibt es keins davon, das groesste vorhandene
        "wunsch": ["openai/gpt-oss-120b", "qwen", "llama-3.3-70b", "openai/gpt-oss-20b"],
    },
    "mistral": {
        "schluessel": "MISTRAL_API_KEY",
        "url": "https://api.mistral.ai/v1",
        "wunsch": ["mistral-large-latest", "mistral-medium-latest", "magistral-medium-latest",
                   "mistral-small-latest"],
    },
    "gemini": {
        "schluessel": "GEMINI_API_KEY",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "wunsch": ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash",
                   "flash"],
    },
}
REIHENFOLGE = {"schreiben": ["groq", "mistral", "gemini"],
               "pruefen": ["mistral", "gemini", "groq"]}


class KeinModell(RuntimeError):
    """Kein Anbieter hat geantwortet."""


def _http(url, schluessel, daten=None):
    req = urllib.request.Request(
        url, data=json.dumps(daten).encode() if daten is not None else None,
        headers={"Authorization": f"Bearer {schluessel}", "Content-Type": "application/json",
                 "User-Agent": "kanal-sammlung/1.0"},
        method="POST" if daten is not None else "GET")
    with urllib.request.urlopen(req, timeout=ZEITLIMIT) as antwort:
        return json.loads(antwort.read())


def modelle(anbieter):
    """Vorhandene Modelle des Anbieters, nach Wunschliste sortiert ([] ohne Schluessel)."""
    if anbieter in _katalog:
        return _katalog[anbieter]
    info = ANBIETER[anbieter]
    schluessel = os.environ.get(info["schluessel"], "")
    gewaehlt = []
    if schluessel:
        try:
            liste = [m["id"].removeprefix("models/")
                     for m in _http(f"{info['url']}/models", schluessel).get("data", [])]
        except Exception as fehler:  # noqa: BLE001 - Anbieter gerade nicht erreichbar
            print(f"   {anbieter}: Modellliste nicht lesbar ({type(fehler).__name__})")
            liste = []
        for wunsch in info["wunsch"]:
            for m in liste:
                if wunsch in m and m not in gewaehlt and not any(
                        x in m for x in ("tts", "whisper", "guard", "embed", "image", "audio",
                                         "vision", "ocr", "moderation", "live", "lite")):
                    gewaehlt.append(m)
                    break
    _katalog[anbieter] = gewaehlt
    if gewaehlt:
        print(f"   {anbieter}: {', '.join(gewaehlt)}")
    return gewaehlt


def _rufe(anbieter, modell, text, temperatur, max_ausgabe):
    info = ANBIETER[anbieter]
    daten = {"model": modell, "messages": [{"role": "user", "content": text}],
             "temperature": temperatur, "max_tokens": max_ausgabe}
    if "gpt-oss" in modell and not info.get("ohne_denken"):
        daten["reasoning_effort"] = "medium"
    antwort = _http(f"{info['url']}/chat/completions", os.environ[info["schluessel"]], daten)
    nachricht = (antwort.get("choices") or [{}])[0].get("message") or {}
    inhalt = nachricht.get("content") or ""
    if isinstance(inhalt, list):   # Mistral-Denkmodelle liefern Bloecke
        inhalt = "".join(b.get("text", "") for b in inhalt if isinstance(b, dict))
    return inhalt


def frage(text, rolle="schreiben", temperatur=0.7, max_ausgabe=4000):
    """Ein Aufruf mit Wechsel ueber Modelle und Anbieter.

    429: kurz warten (Retry-After, hoechstens 90 s) und bis zu dreimal neu,
    dann naechstes Modell. 5xx/Zeitueberschreitung: sofort naechstes Modell.
    """
    letzter = "kein Anbieter mit Schluessel"
    for anbieter in REIHENFOLGE[rolle]:
        for modell in modelle(anbieter):
            for versuch in range(3):
                try:
                    inhalt = _rufe(anbieter, modell, text, temperatur, max_ausgabe)
                except urllib.error.HTTPError as fehler:
                    try:
                        meldung = json.loads(fehler.read()).get("error", {})
                        meldung = meldung.get("message", "") if isinstance(meldung, dict) else str(meldung)
                    except Exception:  # noqa: BLE001
                        meldung = ""
                    letzter = f"{anbieter}/{modell}: HTTP {fehler.code} {meldung[:140]}"
                    if fehler.code == 429 and versuch < 2:
                        warte = min(90.0, float(fehler.headers.get("retry-after") or 20 * (versuch + 1)))
                        print(f"   {anbieter}: Limit, warte {warte:.0f} s")
                        time.sleep(warte + 1)
                        continue
                    if (fehler.code == 400 and "reasoning" in meldung.lower()
                            and not ANBIETER[anbieter].get("ohne_denken")):
                        ANBIETER[anbieter]["ohne_denken"] = True
                        continue
                    print("  ", letzter)
                    if fehler.code == 404:   # Modell abgeschaltet: fuer diesen Lauf streichen
                        _katalog[anbieter] = [x for x in _katalog.get(anbieter, []) if x != modell]
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as fehler:
                    letzter = f"{anbieter}/{modell}: {type(fehler).__name__}"
                    print("  ", letzter)
                    break
                if inhalt.strip():
                    return inhalt
                letzter = f"{anbieter}/{modell}: leere Antwort"
                break
    raise KeinModell(letzter)


def json_aus(text):
    """JSON aus einer Antwort ziehen (auch aus ```json-Bloecken)."""
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
        daten = json_aus(frage(auftrag, "schreiben"))
    except (ValueError, KeinModell) as fehler:
        print("  Erzeugen gescheitert:", fehler)
        return []
    return [x for x in (daten if isinstance(daten, list) else [daten]) if isinstance(x, dict)]


def pruefen(eintrag, hinweis="", zusatz=""):
    """Gegenlesen gegen den mitgegebenen Referenztext. True nur bei klarer Bestaetigung."""
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
        urteil = json_aus(frage(auftrag, "pruefen", temperatur=0.0, max_ausgabe=1500))
    except (ValueError, KeinModell) as fehler:
        print("  Pruefung gescheitert:", fehler)
        return False, str(fehler)
    return urteil.get("ok") is True, str(urteil.get("reason", ""))[:200]


def _wiki(sprache, params):
    url = f"https://{sprache}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={
        "User-Agent": "kanal-sammlung/1.0 (github.com/emreayydin; fact checking)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def wiki_text(angabe, stichworte="", zeichen=5000):
    """Relevante Absaetze eines Wikipedia-Artikels ("de:Titel" / "en:Titel").

    Findet der genaue Titel nichts, wird nach ihm gesucht und der erste Treffer
    genommen. Aus langen Artikeln kommen die Absaetze, die die meisten
    Stichworte bzw. Zahlen des Eintrags enthalten - so bleibt der Aufruf klein
    (die kostenlosen Kontingente zaehlen Tokens pro Minute).
    """
    sprache, _, titel = str(angabe).partition(":")
    titel = titel.strip()
    if sprache not in ("de", "en") or not titel:
        return ""
    try:
        seiten = _wiki(sprache, {"action": "query", "prop": "extracts", "explaintext": 1,
                                 "redirects": 1, "titles": titel})["query"]["pages"]
        text = (seiten[0].get("extract") or "") if seiten else ""
        if not text:
            treffer = _wiki(sprache, {"action": "query", "list": "search", "srsearch": titel,
                                      "srlimit": 1})["query"]["search"]
            if treffer:
                seiten = _wiki(sprache, {"action": "query", "prop": "extracts", "explaintext": 1,
                                         "redirects": 1, "titles": treffer[0]["title"]})["query"]["pages"]
                text = (seiten[0].get("extract") or "") if seiten else ""
    except Exception:  # noqa: BLE001 - Netz/Format: gilt als nicht gefunden
        return ""
    if len(text) <= zeichen:
        return text
    absaetze = [a.strip() for a in text.split("\n") if len(a.strip()) > 40]
    worte = {w.lower() for w in re.findall(r"\w{5,}|\d[\d.,]*", stichworte)}
    def wert(a):
        al = a.lower()
        return sum(1 for w in worte if w in al)
    auswahl, laenge = [absaetze[0]] if absaetze else [], len(absaetze[0]) if absaetze else 0
    for a in sorted(absaetze[1:], key=wert, reverse=True):
        if laenge + len(a) > zeichen:
            continue
        auswahl.append(a)
        laenge += len(a)
    return "\n".join(auswahl)


def melde(titel, text, wichtig=False):
    """Push aufs Handy ueber ntfy (NTFY_TOPIC als GitHub-Secret), auch ohne Mac."""
    thema = os.environ.get("NTFY_TOPIC", "")
    if not thema:
        return
    nutzlast = {"topic": thema, "title": titel, "message": text[:3000],
                "priority": 4 if wichtig else 2, "tags": ["tv"]}
    try:
        urllib.request.urlopen(urllib.request.Request(
            "https://ntfy.sh", data=json.dumps(nutzlast).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json"}), timeout=20).read()
    except Exception as fehler:  # noqa: BLE001 - eine fehlende Push darf den Lauf nicht kippen
        print("Push fehlgeschlagen:", type(fehler).__name__)


def bericht(kanal, frisch_vorher, neu, fehlend, warnschwelle, verbrauch_pro_tag):
    """Ergebnis ausgeben und bei knappem Bestand aufs Handy melden."""
    frisch = frisch_vorher + neu
    tage = frisch / verbrauch_pro_tag if verbrauch_pro_tag else 0
    zeile = f"{kanal}: {neu} neu, {frisch} frisch (reicht ca. {tage:.0f} Tage)"
    print(zeile)
    if frisch < warnschwelle:
        melde(f"{kanal}: Sammlung fast leer",
              f"{zeile}. Nachfuellen hat {fehlend - neu} nicht geschafft - "
              f"Workflow-Log pruefen (Gratis-Anbieter ueberlastet oder Schluessel fehlt).",
              wichtig=True)


def schreibe_modul(pfad, name, eintraege, kopf):
    """Neue Eintraege als Python-Modul ablegen (eine Liste, vollstaendig neu geschrieben)."""
    import pprint
    text = f'"""{kopf}"""\n\n{name} = ' + pprint.pformat(eintraege, width=100, sort_dicts=False) + "\n"
    compile(text, str(pfad), "exec")
    pfad.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    # Diagnose: welche Anbieter/Modelle antworten (ohne Schluessel auszugeben).
    for a in ANBIETER:
        for m in modelle(a):
            try:
                print(a, m, "->", _rufe(a, m, "Reply with the single word OK.", 0.0, 200)[:40].strip())
            except Exception as f:  # noqa: BLE001
                print(a, m, "->", type(f).__name__, getattr(f, "code", ""))
