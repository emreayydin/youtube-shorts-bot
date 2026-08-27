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

# Long-form videos publish on these UTC weekdays (Mon=0 … Sun=6): Tue, Thu, Sun.
LONG_VIDEO_WEEKDAYS = {1, 3, 6}

# Self-throttle so the bot paces itself even though GitHub's free cron fires
# unreliably. The shorts workflow is over-scheduled (hourly across the active
# window); these caps decide whether a given run actually uploads. YouTube's free
# quota = 10,000 units/day, videos.insert = 1,600 → 6 uploads/day max.
DAILY_UPLOAD_CAP = 6          # total videos (shorts + long) per quota day
# 2h, not 3h: the cron now only fires 08:00-20:00 UTC, a 12h window. At 3h
# spacing five gaps need 15h and the sixth upload would never fit — the cap
# would silently become 5/day. Same reasoning as muslim-world-bot.
MIN_HOURS_BETWEEN = 2.0       # min spacing between uploads so bursts can't happen


def _should_skip_for_quota() -> tuple[bool, str]:
    """Returns (skip, reason) from the day's upload count and spacing, so dropped
    cron triggers get 'caught up' by later ones without exceeding quota."""
    import history
    from datetime import datetime, timezone
    total = history.uploads_in_current_window()
    shorts = history.uploads_in_current_window(kind="short")
    gap = history.hours_since_last_upload()

    # Reserve one slot for the long-form video on its days (Tue/Thu/Sun).
    is_long_day = datetime.now(timezone.utc).weekday() in LONG_VIDEO_WEEKDAYS
    short_cap = DAILY_UPLOAD_CAP - 1 if is_long_day else DAILY_UPLOAD_CAP

    if total >= DAILY_UPLOAD_CAP:
        return True, f"daily upload cap reached ({total}/{DAILY_UPLOAD_CAP})"
    if shorts >= short_cap:
        return True, f"short cap for today reached ({shorts}/{short_cap})"
    if gap is not None and gap < MIN_HOURS_BETWEEN:
        return True, f"only {gap:.1f}h since last upload (min {MIN_HOURS_BETWEEN}h)"
    return False, ""


def run(category: str = None, dry_run: bool = False, privacy: str = "public"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(exist_ok=True)
    import history

    # Scheduled runs pass no category. Self-throttle only those real uploads;
    # a manual run (explicit --category) or a dry run is never skipped.
    if category is None and not dry_run:
        skip, reason = _should_skip_for_quota()
        if skip:
            log.info(f"Überspringe diesen Lauf — {reason}.")
            return None

    # 1. Generate fact (avoiding previously posted topics)
    log.info("Generiere Trivia-Fakt...")
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

    # 2b. AI images illustrating the fact (falls FAL_KEY gesetzt; sonst Pexels)
    ai_images = None
    if os.environ.get("FAL_KEY") and fact.get("image_prompts"):
        try:
            from generate_visuals import images_for_prompts
            log.info("Generiere KI-Bilder (Flux)...")
            ai_images = images_for_prompts(fact["image_prompts"],
                                           str(OUTPUT_DIR / f"visuals_{timestamp}"),
                                           orientation="portrait")
        except Exception as e:
            log.warning(f"KI-Bilder fehlgeschlagen ({e}) — nutze Pexels.")

    # 3. Render video (motion background + animated captions)
    log.info("Rendere Video...")
    video_path = str(OUTPUT_DIR / f"short_{timestamp}.mp4")
    background = os.environ.get("BACKGROUND_VIDEO_PATH")
    render_video(fact, audio_path, video_path, words=words, background_video=background,
                 ai_images=ai_images)
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
