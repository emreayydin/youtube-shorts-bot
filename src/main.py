"""Main entry point: generates a trivia fact, renders a Short, uploads to YouTube."""
import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Load .env file if present (so ANTHROPIC_API_KEY is picked up automatically)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

from generate_content import generate_fact
from text_to_speech import generate_audio
from render_video import render_video
from upload_youtube import upload_short


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

OUTPUT_DIR = Path("output")


def run(category: str = None, dry_run: bool = False, privacy: str = "public"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Generate fact (avoiding previously posted topics)
    log.info("Generiere Trivia-Fakt...")
    import history
    fact = generate_fact(category, avoid=history.recent_titles(40, kind="short"))
    log.info(f"Fakt: {fact['title']}")

    fact_path = OUTPUT_DIR / f"fact_{timestamp}.json"
    fact_path.write_text(json.dumps(fact, ensure_ascii=False, indent=2))

    # 2. Text to speech (also returns word-level timing for captions)
    log.info("Generiere Audio...")
    tts_text = f"{fact['hook']}. {fact['body']} {fact['cta']}"
    audio_path = str(OUTPUT_DIR / f"audio_{timestamp}.mp3")
    words = generate_audio(tts_text, audio_path)
    log.info(f"Audio: {audio_path} ({len(words)} Wörter)")

    # 3. Render video (motion background + animated captions)
    log.info("Rendere Video...")
    video_path = str(OUTPUT_DIR / f"short_{timestamp}.mp4")
    background = os.environ.get("BACKGROUND_VIDEO_PATH")
    render_video(fact, audio_path, video_path, words=words, background_video=background)
    log.info(f"Video: {video_path}")

    if dry_run:
        log.info(f"[DRY RUN] Video nicht hochgeladen. Gespeichert unter: {video_path}")
        return video_path

    # 4. Upload to YouTube
    log.info(f"Lade Video hoch (privacy={privacy})...")
    video_id = upload_short(
        video_path=video_path,
        title=fact["title"],
        description=fact["body"],
        tags=fact.get("tags", []),
        privacy=privacy,
    )
    # Only record actually-posted videos so the topic is avoided next time
    history.add_entry("short", fact["title"], fact.get("category", ""))
    log.info(f"Fertig! https://youtube.com/shorts/{video_id}")
    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Shorts Bot")
    parser.add_argument("--category", type=str, default=None, help="Kategorie (optional)")
    parser.add_argument("--dry-run", action="store_true", help="Kein Upload, nur lokale Ausgabe")
    parser.add_argument("--privacy", type=str, default=os.environ.get("UPLOAD_PRIVACY", "public"),
                        choices=["public", "private", "unlisted"],
                        help="Sichtbarkeit des Uploads")
    args = parser.parse_args()

    run(category=args.category, dry_run=args.dry_run, privacy=args.privacy)
