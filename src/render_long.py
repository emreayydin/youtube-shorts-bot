"""Renders a long-form 16:9 (1920x1080) fact-compilation video.

Background = looped montage of landscape Pexels clips (hard cuts). On top, each
section (intro / fact 1-10 / outro) gets its own overlay card shown for its time
window: the intro title, a "FAKT n/10 + headline" banner per fact, an outro card.

No per-word captions here (a 6-min video would need hundreds of overlays); the
per-fact headline banner labels the content instead. Uses only overlay/scale/
crop/concat so it works on the limited local ffmpeg and on Ubuntu CI.
"""
import subprocess
import math
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw

from fetch_background import fetch_background_clips
from render_video import _find_font, _strip_emoji, _wrap, _probe_duration, CATEGORY_COLORS, DEFAULT_COLORS

LW, LH = 1920, 1080
SEG = 6.0  # seconds per clip in the base montage


def _gradient(top, bottom, path):
    base = Image.new("RGB", (LW, LH), top)
    layer = Image.new("RGB", (LW, LH), bottom)
    mask = Image.new("L", (LW, LH))
    mask.putdata([int(255 * (y / LH)) for y in range(LH) for _ in range(LW)])
    base.paste(layer, (0, 0), mask)
    base.save(path)
    return path


def _scrim(path):
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, LW, LH], fill=(0, 0, 0, 80))
    d.rectangle([0, 0, LW, 230], fill=(0, 0, 0, 80))          # top band for banner
    d.rectangle([0, LH - 160, LW, LH], fill=(0, 0, 0, 70))    # bottom band
    img.save(path)
    return path


def _intro_card(comp, path):
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    badge_f = _find_font(54)
    title_f = _find_font(108)

    badge = f"{len(comp['facts'])} FAKTEN"
    bw = d.textlength(badge, font=badge_f)
    d.rounded_rectangle([(LW - bw) / 2 - 34, 300, (LW + bw) / 2 + 34, 384],
                        radius=22, fill=(255, 210, 63))
    d.text(((LW - bw) / 2, 312), badge, font=badge_f, fill=(11, 20, 55))

    lines = _wrap(d, _strip_emoji(comp["title"]), title_f, LW - 320)
    y = 440
    for line in lines:
        w = d.textlength(line, font=title_f)
        d.text(((LW - w) / 2, y), line, font=title_f, fill=(255, 255, 255),
               stroke_width=6, stroke_fill=(0, 0, 0))
        y += 124
    img.save(path)
    return path


def _fact_card(idx, total, headline, path):
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    num_f = _find_font(60)
    head_f = _find_font(76)

    # big watermark number
    big_f = _find_font(420)
    num = str(idx)
    d.text((70, LH - 470), num, font=big_f, fill=(255, 255, 255, 28))

    # top banner: "FAKT idx/total"  +  headline
    pill = f"FAKT {idx}/{total}"
    pw = d.textlength(pill, font=num_f)
    d.rounded_rectangle([80, 70, 80 + pw + 52, 156], radius=20, fill=(255, 210, 63))
    d.text((106, 82), pill, font=num_f, fill=(11, 20, 55))

    head = _strip_emoji(headline)
    lines = _wrap(d, head, head_f, LW - 200)
    y = 176
    for line in lines[:2]:
        d.text((84, y), line, font=head_f, fill=(255, 255, 255),
               stroke_width=5, stroke_fill=(0, 0, 0))
        y += 90
    img.save(path)
    return path


def _outro_card(comp, path):
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    q_f = _find_font(82)
    sub_f = _find_font(56)

    q = "Welcher Fakt hat dich am meisten überrascht?"
    lines = _wrap(d, q, q_f, LW - 360)
    y = 360
    for line in lines:
        w = d.textlength(line, font=q_f)
        d.text(((LW - w) / 2, y), line, font=q_f, fill=(255, 255, 255),
               stroke_width=5, stroke_fill=(0, 0, 0))
        y += 96

    cta = "ABONNIEREN FÜR MEHR FAKTEN"
    cw = d.textlength(cta, font=sub_f)
    d.rounded_rectangle([(LW - cw) / 2 - 40, y + 40, (LW + cw) / 2 + 40, y + 128],
                        radius=24, fill=(255, 210, 63))
    d.text(((LW - cw) / 2, y + 56), cta, font=sub_f, fill=(11, 20, 55))
    img.save(path)
    return path


def _build_montage(clips, out_path):
    """Concatenates clips (SEG seconds each) once into a base montage to be looped."""
    durations = {c: _probe_duration(c) for c in clips}
    clips = [c for c in clips if durations[c] >= 1.0] or clips

    inputs, filters, labels = [], [], []
    for i, clip in enumerate(clips):
        seg = min(SEG, max(1.0, durations.get(clip, SEG)))
        inputs += ["-ss", "0", "-t", f"{seg:.2f}", "-i", clip]
        filters.append(
            f"[{i}:v]scale={LW}:{LH}:force_original_aspect_ratio=increase,"
            f"crop={LW}:{LH},setsar=1,fps=30,format=yuv420p[v{i}]")
        labels.append(f"[v{i}]")
    concat = "".join(labels) + f"concat=n={len(clips)}:v=1:a=0[bg]"
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filters + [concat]), "-map", "[bg]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Montage failed:\n{r.stderr[-2000:]}")
    return out_path


def render_long(comp: dict, audio_path: str, sections: list[dict], output_path: str) -> str:
    """sections: [{label, start, end}] from build_narration (intro/fact_i/outro)."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="long_"))
    total = max(s["end"] for s in sections) + 0.5

    # ---- background ----
    clips = fetch_background_clips(comp.get("category", ""), str(work / "clips"),
                                   count=12, tags=comp.get("tags"), orientation="landscape")
    if clips:
        base = _build_montage(clips, str(work / "base.mp4"))
        bg_input = ["-stream_loop", "-1", "-i", base]
        bg_filter = f"[0:v]scale={LW}:{LH},setsar=1[bg]"
    else:
        top, bottom = CATEGORY_COLORS.get(comp.get("category", ""), DEFAULT_COLORS)
        grad = _gradient(top, bottom, str(work / "grad.png"))
        bg_input = ["-loop", "1", "-t", f"{total:.2f}", "-i", grad]
        bg_filter = (f"[0:v]scale={int(LW*1.15)}:{int(LH*1.15)},"
                     f"crop={LW}:{LH}:x='(in_w-{LW})/2+sin(t/6)*50':"
                     f"y='(in_h-{LH})/2+cos(t/7)*40',setsar=1[bg]")

    t_arg = ["-t", f"{total:.2f}"]
    scrim = _scrim(str(work / "scrim.png"))

    # ---- one card per section ----
    total_facts = len(comp["facts"])
    cards = []
    fact_i = 0
    for s in sections:
        p = str(work / f"card_{len(cards)}.png")
        if s["label"] == "intro":
            _intro_card(comp, p)
        elif s["label"] == "outro":
            _outro_card(comp, p)
        else:
            fact_i += 1
            headline = comp["facts"][fact_i - 1]["headline"]
            _fact_card(fact_i, total_facts, headline, p)
        cards.append({"path": p, "start": s["start"], "end": s["end"]})

    # ---- compose ----
    cmd = ["ffmpeg", "-y"] + bg_input
    cmd += ["-loop", "1"] + t_arg + ["-i", scrim]   # 1
    for c in cards:                                  # 2..N
        cmd += ["-loop", "1"] + t_arg + ["-i", c["path"]]
    cmd += ["-i", audio_path]                        # last
    audio_idx = 2 + len(cards)

    parts = [bg_filter, "[bg][1:v]overlay[base0]"]
    last = "base0"
    for i, c in enumerate(cards):
        out = f"s{i}"
        parts.append(f"[{last}][{2 + i}:v]overlay=enable='between(t,{c['start']:.2f},{c['end']:.2f})'[{out}]")
        last = out

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", f"[{last}]", "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-r", "30",
        "-t", f"{total:.2f}", "-shortest", output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{r.stderr[-2500:]}")
    return output_path
