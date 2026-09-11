# YouTube Shorts Bot 🎬

Erstellt täglich automatisch deutsche Trivia-Fakten als YouTube Shorts.

## Architektur

```
Lokale Faktenbank → Trivia-Fakt generieren
     ↓
edge-tts  → Text zu Sprache (Microsoft Neural Voice)
     ↓
ffmpeg    → Video rendern (1080×1920, 9:16)
     ↓
YouTube API → Short hochladen
     ↓
GitHub Actions → täglich 14:00 Uhr (DE)
```

Die lokale Faktenbank ist der Standard und benötigt keinen Anthropic-Schlüssel.
Für Uploads bleibt nur die separate YouTube-OAuth-Authentifizierung notwendig.

## Setup

### 1. Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Außerdem ffmpeg installieren:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

### 2. YouTube API einrichten

1. Gehe zur [Google Cloud Console](https://console.cloud.google.com)
2. Neues Projekt erstellen
3. **YouTube Data API v3** aktivieren
4. **OAuth 2.0 Client ID** erstellen (Typ: Desktop-App)
5. Credentials als `client_secrets.json` herunterladen → in `/src` ablegen
6. Einmalig lokal authentifizieren:

```bash
cd src
python upload_youtube.py
```

→ Browser öffnet sich → YouTube-Konto autorisieren  
→ Token wird als `youtube_token.json` gespeichert  
→ **Den JSON-Inhalt kopieren** (wird für GitHub Secrets benötigt)

### 3. GitHub Repository einrichten

```bash
git init
git remote add origin https://github.com/DEIN_NAME/youtube-shorts-bot
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 4. GitHub Secrets setzen

Gehe zu: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Inhalt |
|---|---|
| `YOUTUBE_TOKEN_JSON` | Inhalt der `youtube_token.json` (ganzer JSON) |

### 5. Testen

Manuell in GitHub Actions starten:
- Gehe zu **Actions → Daily YouTube Short → Run workflow**
- Aktiviere "Dry run" für einen Test ohne Upload

---

## Lokale Nutzung

```bash
cd src

# Zufälliger Fakt, direkt hochladen
python main.py

# Spezifische Kategorie
python main.py --category Astronomie

# Nur lokal rendern, nicht hochladen
python main.py --dry-run
```

## Kategorien

- Wissenschaft, Geschichte, Natur, Technologie
- Weltrekorde, Psychologie, Astronomie, Biologie

## Token erneuern

YouTube OAuth-Token läuft nach ~6 Monaten ab. Dann:
1. Lokal nochmal `python upload_youtube.py` ausführen
2. Neuen Token-Inhalt als GitHub Secret aktualisieren

## Kosten

| Service | Kosten |
|---|---|
| Lokale Faktenbank | Kostenlos |
| edge-tts | Kostenlos |
| ffmpeg | Kostenlos |
| YouTube API | Kostenlos (10.000 Units/Tag) |
| GitHub Actions | Kostenlos (2.000 Min/Monat) |

**Gesamtkosten: ~$0.30/Monat** (30 Videos)

## Channel takeover: The Difference Money

The repository now keeps the two YouTube channels explicit in
`config/channels.json`. The legacy default remains `faktisch`; the finance
channel is selected deliberately and cannot silently fall back to it:

```bash
cd src
CHANNEL_MODE=difference_money CONTENT_MODE=finance COMPARISON_SYMBOL=ACWI \
  VERIFY_CHANNEL_ID=true python main.py --dry-run
```

For a named preview use `COMPARISON_SCENARIO=mercedes-car` instead of the
ticker. With `COMPARISON_SCENARIO=auto`, the daily workflow rotates through the
configured comparisons (all-world ETF/House, Mercedes, Apple/AirPods, eBay,
Tesla and Solana/transfer fee) deterministically by UTC date.

The finance mode can generate a clean historical comparison in the visual style
of a data explainer: a highlighted headline, original vector icons, and an
animated adjusted-close chart. Numeric values are calculated in
`src/finance_ranking.py`; the language model is not allowed to invent prices or
returns. Each generated description includes the data timestamp, source, and
an educational-not-financial-advice notice. A finance upload first checks the
OAuth channel ID, so the wrong Brand Account fails before `videos.insert`.

Before enabling a scheduled upload, authorize the intended Difference Money
account with the upload and read-only YouTube scopes, update the repository
secret, and run a dry run. Never copy the token into source control or send it
in chat. The comparison defaults live in `config/finance.json`; choose the
ticker deliberately and keep the source/disclaimer in every upload.

The GitHub workflow `.github/workflows/difference_money_ranking.yml` is
scheduled six times daily at 08:00, 10:00, 12:00, 14:00, 16:00 and 18:00 UTC
and uses the separate
`DIFFERENCE_MONEY_YOUTUBE_TOKEN_JSON` secret. It skips safely until that
target-channel secret exists; manual runs start in dry-run mode and scheduled
runs use `public` only after the channel-ID verification gate passes.
