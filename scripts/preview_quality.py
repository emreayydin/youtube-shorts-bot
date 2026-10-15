"""Create one reviewable local trivia video, never upload or consume history."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from local_content import FACTS
from text_to_speech import generate_audio
from render_video import render_video


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", default="Der Mythos von der Chinesischen Mauer im All")
    parser.add_argument("--name", default="great-wall")
    args = parser.parse_args()
    fact = next((dict(f) for f in FACTS if f["title"] == args.title), None)
    if not fact or not fact.get("sources"):
        raise SystemExit("Choose an existing source-marked bank title.")
    out = ROOT / "output" / "quality-2026-10-15" / args.name
    out.mkdir(parents=True, exist_ok=True)
    text = f"{fact['hook']}. {fact['body']} {fact['cta']}"
    cache = out / "narration.json"
    audio = out / "voice.mp3"
    data = json.loads(cache.read_text()) if cache.exists() else {}
    if data.get("text") == text and audio.exists():
        words = data["words"]
    else:
        words = generate_audio(text, str(audio), rate="+4%")
        cache.write_text(json.dumps({"text": text, "words": words}, ensure_ascii=False, indent=2))
    (out / "content.json").write_text(json.dumps(fact, ensure_ascii=False, indent=2))
    render_video(fact, str(audio), str(out / "preview.mp4"), words=words)
    print(out / "preview.mp4")


if __name__ == "__main__":
    main()
