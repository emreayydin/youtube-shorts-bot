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
SEG = 3.0           # seconds per clip before a cut (faster = more dynamic)
BASE_TARGET = 78.0  # length of the base montage before it loops (more variety)
ZOOM_PER_SEG = 0.14 # Ken-Burns push per clip


def _gradient(top, bottom, path):
    base = Image.new("RGB", (LW, LH), top)
    layer = Image.new("RGB", (LW, LH), bottom)
    mask = Image.new("L", (LW, LH))
    mask.putdata([int(255 * (y / LH)) for y in range(LH) for _ in range(LW)])
    base.paste(layer, (0, 0), mask)
    base.save(path)
    return path


def _new_scrim_img():
    """New full-frame RGBA image with the scrim already drawn (baked into cards)."""
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, LW, LH], fill=(0, 0, 0, 80))
    d.rectangle([0, 0, LW, 230], fill=(0, 0, 0, 80))          # top band for banner
    d.rectangle([0, LH - 160, LW, LH], fill=(0, 0, 0, 70))    # bottom band
    return img, d


def _intro_card(comp, path):
    img, d = _new_scrim_img()
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
    img, d = _new_scrim_img()
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
    img, d = _new_scrim_img()
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


def make_thumbnail(comp: dict, path: str) -> str:
    """Generates a 1280x720 YouTube thumbnail for the compilation."""
    TW, TH = 1280, 720
    top, bottom = CATEGORY_COLORS.get(comp.get("category", ""), DEFAULT_COLORS)
    img = Image.new("RGB", (TW, TH), top)
    layer = Image.new("RGB", (TW, TH), bottom)
    mask = Image.new("L", (TW, TH))
    mask.putdata([int(255 * (y / TH)) for y in range(TH) for _ in range(TW)])
    img.paste(layer, (0, 0), mask)
    d = ImageDraw.Draw(img)

    n = len(comp["facts"])
    # giant number, right-aligned with margin so it never clips
    big = _find_font(380)
    num = str(n)
    nw = d.textlength(num, font=big)
    nx = TW - nw - 60
    ny = (TH - 380) / 2 + 20
    d.text((nx, ny), num, font=big, fill=(255, 210, 63),
           stroke_width=12, stroke_fill=(0, 0, 0))

    # category badge
    cat_f = _find_font(46)
    cat = _strip_emoji(comp.get("category", "")).upper()
    if cat:
        cw = d.textlength(cat, font=cat_f)
        d.rounded_rectangle([60, 70, 60 + cw + 48, 150], radius=18, fill=(255, 210, 63))
        d.text((84, 84), cat, font=cat_f, fill=(11, 20, 55))

    # title (big, left)
    title_f = _find_font(88)
    lines = _wrap(d, _strip_emoji(comp["title"]), title_f, 700)
    y = 210
    for line in lines[:4]:
        d.text((64, y), line, font=title_f, fill=(255, 255, 255),
               stroke_width=6, stroke_fill=(0, 0, 0))
        y += 104
    img.save(path)
    return path


def _build_montage(clips, out_path):
    """Builds a varied base montage (~BASE_TARGET s) with fast cuts + zoom-push.

    Cycles through the clips with varied start points so the same clip never
    shows the same moment twice, then this base is looped to fill the video.
    """
    durations = {c: _probe_duration(c) for c in clips}
    clips = [c for c in clips if durations[c] >= 1.0] or clips

    n_segments = max(len(clips), math.ceil(BASE_TARGET / SEG))
    seg_frames = max(1, int(SEG * 30))
    zin = ZOOM_PER_SEG / seg_frames
    usage = {c: 0 for c in clips}

    inputs, filters, labels = [], [], []
    for i in range(n_segments):
        clip = clips[i % len(clips)]
        dur = durations.get(clip, 0) or SEG
        max_start = max(0.0, dur - SEG)
        start = (usage[clip] * SEG) % (max_start + 0.001) if max_start > 0 else 0.0
        usage[clip] += 1

        inputs += ["-ss", f"{start:.2f}", "-t", f"{SEG:.2f}", "-i", clip]
        if i % 2 == 0:
            zexpr = f"min(zoom+{zin:.5f},{1 + ZOOM_PER_SEG:.3f})"
        else:
            zexpr = f"if(eq(on,0),{1 + ZOOM_PER_SEG:.3f},max(zoom-{zin:.5f},1.0))"
        filters.append(
            f"[{i}:v]fps=30,"
            f"scale={int(LW*1.25)}:{int(LH*1.25)}:force_original_aspect_ratio=increase,"
            f"crop={int(LW*1.25)}:{int(LH*1.25)},"
            f"zoompan=z='{zexpr}':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"s={LW}x{LH}:fps=30,setsar=1,format=yuv420p[v{i}]")
        labels.append(f"[v{i}]")

    concat = "".join(labels) + f"concat=n={n_segments}:v=1:a=0[bg]"
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filters + [concat]), "-map", "[bg]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-r", "30", "-an", "-threads", "0", out_path]
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
                                   count=14, tags=comp.get("tags"), orientation="landscape")
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

    # ---- one card per section (scrim baked in) ----
    total_facts = len(comp["facts"])
    cards, fact_i = [], 0
    for i, s in enumerate(sections):
        p = str(work / f"card_{i}.png")
        if s["label"] == "intro":
            _intro_card(comp, p)
        elif s["label"] == "outro":
            _outro_card(comp, p)
        else:
            fact_i += 1
            _fact_card(fact_i, total_facts, comp["facts"][fact_i - 1]["headline"], p)
        cards.append({"path": p, "dur": max(0.1, s["end"] - s["start"])})

    # concat-demuxer list -> ONE timed overlay track (last entry repeated for its duration)
    list_path = work / "cards.txt"
    lines = []
    for c in cards:
        lines.append(f"file '{c['path']}'")
        lines.append(f"duration {c['dur']:.3f}")
    lines.append(f"file '{cards[-1]['path']}'")
    list_path.write_text("\n".join(lines))

    # ---- compose: background + ONE overlay track + audio (only 3 inputs) ----
    cmd = ["ffmpeg", "-y"] + bg_input
    cmd += ["-f", "concat", "-safe", "0", "-i", str(list_path)]   # 1: overlay track
    cmd += ["-i", audio_path]                                     # 2: audio

    filter_complex = (
        bg_filter
        + ";[1:v]fps=30,format=rgba,setsar=1[ov]"
        + ";[bg][ov]overlay=eof_action=pass:format=auto[v]"
    )
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "2:a",
        # ultrafast: GitHub's 2-core runner is slow at libx264; YouTube re-encodes anyway.
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-r", "30",
        "-threads", "0", "-t", f"{total:.2f}", "-shortest", output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{r.stderr[-2500:]}")
    return output_path
