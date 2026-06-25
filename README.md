# YouTube Shorts Bot 🎬

Erstellt täglich automatisch deutsche Trivia-Fakten als YouTube Shorts.

## Architektur

```
Claude API → Trivia-Fakt generieren
     ↓
edge-tts  → Text zu Sprache (Microsoft Neural Voice)
     ↓
ffmpeg    → Video rendern (1080×1920, 9:16)
     ↓
YouTube API → Short hochladen
     ↓
GitHub Actions → täglich 14:00 Uhr (DE)
```

## Setup

### 1. Python-Abhängigkeiten installieren

```bash
pip install -r requirements.txt
```

Außerdem ffmpeg installieren:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`

### 2. Anthropic API Key holen

1. Gehe zu https://console.anthropic.com
2. Erstelle einen API Key
3. Speichere ihn als Umgebungsvariable: `export ANTHROPIC_API_KEY=sk-ant-...`

### 3. YouTube API einrichten

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

### 4. GitHub Repository einrichten

```bash
git init
git remote add origin https://github.com/DEIN_NAME/youtube-shorts-bot
git add .
git commit -m "Initial commit"
git push -u origin main
```

### 5. GitHub Secrets setzen

Gehe zu: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name | Inhalt |
|---|---|
| `ANTHROPIC_API_KEY` | Dein Anthropic API Key |
| `YOUTUBE_TOKEN_JSON` | Inhalt der `youtube_token.json` (ganzer JSON) |

### 6. Testen

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
| Claude API (Sonnet) | ~$0.01 pro Video |
| edge-tts | Kostenlos |
| ffmpeg | Kostenlos |
| YouTube API | Kostenlos (10.000 Units/Tag) |
| GitHub Actions | Kostenlos (2.000 Min/Monat) |

**Gesamtkosten: ~$0.30/Monat** (30 Videos)
