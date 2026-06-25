"""Text to speech via edge-tts (free Microsoft neural voices).

Also extracts word-level timing (WordBoundary events) so the video renderer can
draw animated captions synced to the voice.
"""
import asyncio
import edge_tts
from pathlib import Path


# German neural voices (natural-sounding)
VOICES = [
    "de-DE-KillianNeural",   # male, deep
    "de-DE-ConradNeural",    # male, clear
    "de-DE-AmalaNeural",     # female, clear
]


async def _synthesize(text: str, output_path: str, voice: str, rate: str):
    """Streams TTS, saving audio and collecting word timings."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration are in 100-nanosecond ticks
                start = chunk["offset"] / 10_000_000
                duration = chunk["duration"] / 10_000_000
                words.append({
                    "text": chunk["text"],
                    "start": start,
                    "end": start + duration,
                })
    return words


def generate_audio(text: str, output_path: str, voice: str = VOICES[0], rate: str = "+8%"):
    """
    Generates an MP3 and returns word-level timing.
    Returns: list of {"text", "start", "end"} dicts.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    return asyncio.run(_synthesize(text, output_path, voice, rate))


if __name__ == "__main__":
    words = generate_audio(
        "Die Sonne ist so gross, dass eine Million Erden hineinpassen wuerden.",
        "/tmp/test_audio.mp3",
    )
    print(f"{len(words)} Wörter mit Timing erfasst")
    for w in words[:5]:
        print(f"  {w['start']:.2f}s - {w['end']:.2f}s: {w['text']}")
