"""Renders a YouTube Short (9:16, 1080x1920) with fast cuts + animated captions.

Pipeline:
  1. Background = montage of several Pexels stock clips, hard-cut every ~2.5s for
     a fast-paced "dopamine" feel. Falls back to an animated Ken-Burns gradient
     if no Pexels key / no clips.
  2. Pillow renders transparent PNG layers: a dark scrim, a title bar, and one
     caption PNG per spoken phrase.
  3. ffmpeg composites everything with `overlay`, timing each caption to the
     voice via `enable='between(t,start,end)'`.

Uses only ffmpeg filters available without freetype/libass (overlay, scale,
crop, concat, trim), so it runs on the limited local build and Ubuntu CI alike.
"""
import subprocess
import re
import os
import math
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from fetch_background import fetch_background_clips

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SEGMENT = 2.5          # seconds per clip before a hard cut

CATEGORY_COLORS = {
    "Wissenschaft":  ((13, 27, 42),   (27, 79, 114)),
    "Geschichte":    ((44, 24, 16),   (110, 44, 26)),
    "Natur":         ((10, 46, 10),   (26, 107, 26)),
    "Technologie":   ((13, 13, 43),   (26, 26, 107)),
    "Weltrekorde":   ((43, 26, 13),   (139, 69, 19)),
    "Psychologie":   ((26, 13, 43),   (107, 26, 139)),
    "Astronomie":    ((0, 0, 20),     (13, 13, 75)),
    "Biologie":      ((10, 43, 26),   (26, 107, 75)),
}
DEFAULT_COLORS = ((13, 13, 13), (26, 26, 46))

BOLD_FONTS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
]

EMOJI_PATTERN = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]+",
    flags=re.UNICODE,
)


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in BOLD_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _strip_emoji(text: str) -> str:
    return EMOJI_PATTERN.sub("", text).strip()


def _probe_duration(path: str) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# ---------- caption grouping ----------

def _group_captions(words: list[dict], max_words: int = 3, total: float = None) -> list[dict]:
    groups, cur = [], []
    for w in words:
        cur.append(w)
        ends = w["text"] and w["text"][-1] in ".!?,;:"
        if len(cur) >= max_words or ends:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)

    captions = []
    for g in groups:
        text = " ".join(x["text"] for x in g).strip().rstrip(",;:")
        captions.append({"text": text, "start": g[0]["start"], "end": g[-1]["end"]})

    for i in range(len(captions)):
        if i == 0:
            captions[i]["start"] = 0.0
        if i < len(captions) - 1:
            captions[i]["end"] = captions[i + 1]["start"]
        elif total:
            captions[i]["end"] = total
    return captions


# ---------- PNG layers (Pillow) ----------

def _gradient_png(top_rgb, bottom_rgb, path):
    base = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), top_rgb)
    top = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), bottom_rgb)
    mask = Image.new("L", (VIDEO_WIDTH, VIDEO_HEIGHT))
    mask.putdata([int(255 * (y / VIDEO_HEIGHT)) for y in range(VIDEO_HEIGHT) for _ in range(VIDEO_WIDTH)])
    base.paste(top, (0, 0), mask)
    base.save(path)
    return path


def _scrim_png(path):
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, VIDEO_WIDTH, VIDEO_HEIGHT], fill=(0, 0, 0, 90))
    d.rectangle([0, 0, VIDEO_WIDTH, 340], fill=(0, 0, 0, 70))
    d.rectangle([0, VIDEO_HEIGHT - 360, VIDEO_WIDTH, VIDEO_HEIGHT], fill=(0, 0, 0, 70))
    img.save(path)
    return path


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _title_png(fact, path):
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    badge_font = _find_font(40)
    title_font = _find_font(58)

    badge = _strip_emoji(fact.get("category", "")).upper()
    if badge:
        bw = d.textlength(badge, font=badge_font)
        bx = (VIDEO_WIDTH - bw) / 2
        d.rounded_rectangle([bx - 28, 120, bx + bw + 28, 188], radius=20, fill=(255, 215, 0))
        d.text((bx, 130), badge, font=badge_font, fill=(0, 0, 0))

    title = _strip_emoji(fact.get("title", ""))
    lines = _wrap(d, title, title_font, VIDEO_WIDTH - 140)
    y = 220
    for line in lines:
        w = d.textlength(line, font=title_font)
        x = (VIDEO_WIDTH - w) / 2
        d.text((x, y), line, font=title_font, fill=(255, 255, 255),
               stroke_width=4, stroke_fill=(0, 0, 0))
        y += 72
    img.save(path)
    return path


def _caption_png(text, path):
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = _find_font(86)
    lines = _wrap(d, text.upper(), font, VIDEO_WIDTH - 160)
    line_h = 104
    block_h = len(lines) * line_h
    y = (VIDEO_HEIGHT - block_h) / 2 + 120
    for line in lines:
        w = d.textlength(line, font=font)
        x = (VIDEO_WIDTH - w) / 2
        d.text((x, y), line, font=font, fill=(255, 255, 255),
               stroke_width=9, stroke_fill=(0, 0, 0))
        y += line_h
    img.save(path)
    return path


# ---------- background montage ----------

def _build_montage(clips: list[str], total: float, out_path: str) -> str:
    """Concatenates clips with hard cuts every SEGMENT seconds to fill `total`."""
    durations = {c: _probe_duration(c) for c in clips}
    clips = [c for c in clips if durations[c] >= 1.0] or clips

    n_segments = max(1, math.ceil(total / SEGMENT))
    usage = {c: 0 for c in clips}

    inputs, filters, labels = [], [], []
    for i in range(n_segments):
        clip = clips[i % len(clips)]
        dur = durations.get(clip, 0) or SEGMENT
        # vary the start point so reused clips don't show the same moment
        max_start = max(0.0, dur - SEGMENT)
        start = (usage[clip] * SEGMENT) % (max_start + 0.001) if max_start > 0 else 0.0
        usage[clip] += 1

        inputs += ["-ss", f"{start:.2f}", "-t", f"{SEGMENT:.2f}", "-i", clip]
        lbl = f"v{i}"
        filters.append(
            f"[{i}:v]scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT},setsar=1,fps=30,format=yuv420p[{lbl}]"
        )
        labels.append(f"[{lbl}]")

    concat = "".join(labels) + f"concat=n={n_segments}:v=1:a=0[bg]"
    filter_complex = ";".join(filters + [concat])

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[bg]",
        "-t", f"{total:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30", "-an",
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Montage failed:\n{r.stderr[-2000:]}")
    return out_path


# ---------- compose ----------

def render_video(fact: dict, audio_path: str, output_path: str,
                 words: list[dict] = None, background_video: str = None) -> str:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="short_"))

    total = (max(w["end"] for w in words) + 0.8) if words else _probe_duration(audio_path)
    if total <= 0:
        total = 50.0

    # ----- background -----
    clips = [background_video] if background_video else \
        fetch_background_clips(fact.get("category", ""), str(work / "clips"),
                               count=6, tags=fact.get("tags"))

    t_arg = ["-t", f"{total:.2f}"]
    if clips:
        bg = _build_montage(clips, total, str(work / "montage.mp4"))
        bg_input = ["-i", bg]
        bg_filter = f"[0:v]setsar=1[bg]"
    else:
        top, bottom = CATEGORY_COLORS.get(fact.get("category", ""), DEFAULT_COLORS)
        grad = _gradient_png(top, bottom, str(work / "grad.png"))
        bg_input = ["-loop", "1"] + t_arg + ["-i", grad]
        bg_filter = (
            f"[0:v]scale={int(VIDEO_WIDTH*1.2)}:{int(VIDEO_HEIGHT*1.2)},"
            f"crop={VIDEO_WIDTH}:{VIDEO_HEIGHT}:"
            f"x='(in_w-{VIDEO_WIDTH})/2+sin(t/5)*60':"
            f"y='(in_h-{VIDEO_HEIGHT})/2+cos(t/6)*60',setsar=1[bg]"
        )

    # ----- overlay layers -----
    scrim = _scrim_png(str(work / "scrim.png"))
    title = _title_png(fact, str(work / "title.png"))
    captions = _group_captions(words or [], total=total) if words else []
    cap_paths = [_caption_png(c["text"], str(work / f"cap_{i}.png"))
                 for i, c in enumerate(captions)]

    cmd = ["ffmpeg", "-y"] + bg_input
    cmd += ["-loop", "1"] + t_arg + ["-i", scrim]      # 1
    cmd += ["-loop", "1"] + t_arg + ["-i", title]      # 2
    for p in cap_paths:                                # 3..N
        cmd += ["-loop", "1"] + t_arg + ["-i", p]
    cmd += ["-i", audio_path]                          # last
    audio_idx = 3 + len(cap_paths)

    parts = [bg_filter, "[bg][1:v]overlay[d]", "[d][2:v]overlay[base]"]
    last = "base"
    for i, c in enumerate(captions):
        out = f"c{i}"
        parts.append(
            f"[{last}][{3 + i}:v]overlay=enable='between(t,{c['start']:.2f},{c['end']:.2f})'[{out}]"
        )
        last = out
    filter_complex = ";".join(parts)

    cmd += [
        "-filter_complex", filter_complex,
        "-map", f"[{last}]", "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-t", f"{total:.2f}", "-shortest",
        output_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{r.stderr[-2500:]}")
    return output_path


if __name__ == "__main__":
    from text_to_speech import generate_audio
    sample = {
        "title": "Neutronensterne sind extrem",
        "hook": "Ein Loeffel davon waere Milliarden Tonnen schwer.",
        "body": "Neutronensterne entstehen wenn massereiche Sterne kollabieren. "
                "Sie drehen sich hunderte Male pro Sekunde und sind winzig klein.",
        "cta": "Folge fuer mehr Weltraum-Fakten!",
        "category": "Astronomie",
        "tags": ["galaxy", "space"],
    }
    text = f"{sample['hook']} {sample['body']} {sample['cta']}"
    w = generate_audio(text, "/tmp/test_audio.mp3")
    render_video(sample, "/tmp/test_audio.mp3", "/tmp/test_video.mp4", words=w)
    print("Video: /tmp/test_video.mp4")
