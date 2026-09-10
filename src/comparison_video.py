"""Render a clean, data-first comparison video for The Difference Money.

The visual language is intentionally simple: a white canvas, a highlighted
headline, small hand-drawn icons, and one historical line chart that reveals
itself over time.  It borrows the explanatory mechanic of the reference video
without reusing its footage, music, watermark, artwork, or exact copy.
"""

from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

BLACK = (24, 24, 24)
BLUE = (63, 125, 214)
GREEN = (79, 178, 76)
LIGHT_GREEN = (224, 244, 221)
GRID = (226, 229, 233)
MUTED = (116, 123, 132)
WHITE = (255, 255, 255)

FONT_PATHS = {
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS["bold" if bold else "regular"]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _money(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 100_000:
        return f"${value:,.0f}"
    return f"${value:,.0f}"


def _center_segments(draw: ImageDraw.ImageDraw, y: int, segments: list[tuple[str, tuple[int, int, int], bool]], size: int) -> int:
    """Draw one centered line made of differently coloured text segments."""
    fonts = [_font(size, bold) for _, _, bold in segments]
    widths = [draw.textlength(text, font=font) for (text, _, _), font in zip(segments, fonts)]
    x = (VIDEO_WIDTH - sum(widths)) / 2
    for (text, colour, _), font, width in zip(segments, fonts, widths):
        draw.text((x, y), text, font=font, fill=colour)
        x += width
    return int(y + size * 1.15)


def _draw_money_bag(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Small original vector icon; no external stock artwork is needed."""
    s = scale
    draw.ellipse((x + 22 * s, y + 35 * s, x + 118 * s, y + 155 * s), fill=(103, 190, 91), outline=(54, 135, 61), width=max(1, int(4 * s)))
    draw.polygon([(x + 26 * s, y + 50 * s), (x + 114 * s, y + 50 * s), (x + 95 * s, y + 20 * s), (x + 45 * s, y + 20 * s)], fill=(78, 164, 73))
    draw.arc((x + 45 * s, y + 5 * s, x + 95 * s, y + 48 * s), 180, 360, fill=(54, 135, 61), width=max(1, int(4 * s)))
    font = _font(max(18, int(56 * s)), bold=True)
    draw.text((x + 60 * s, y + 69 * s), "$", font=font, fill=WHITE, anchor="mm")
    for dx, dy in ((-18, 132), (105, 132), (2, 160)):
        draw.ellipse((x + dx * s, y + dy * s, x + (dx + 34) * s, y + (dy + 22) * s), fill=(244, 196, 66), outline=(191, 142, 33), width=max(1, int(2 * s)))


def _draw_wallet(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    s = scale
    draw.rounded_rectangle((x, y + 35 * s, x + 145 * s, y + 115 * s), radius=int(16 * s), fill=(91, 144, 214), outline=(48, 91, 151), width=max(1, int(4 * s)))
    draw.rounded_rectangle((x + 18 * s, y + 16 * s, x + 122 * s, y + 73 * s), radius=int(12 * s), fill=(133, 176, 232), outline=(48, 91, 151), width=max(1, int(4 * s)))
    draw.rounded_rectangle((x + 76 * s, y + 62 * s, x + 170 * s, y + 105 * s), radius=int(12 * s), fill=(222, 239, 255), outline=(48, 91, 151), width=max(1, int(4 * s)))
    draw.ellipse((x + 126 * s, y + 73 * s, x + 139 * s, y + 86 * s), fill=(48, 91, 151))


def _draw_mini_chart(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    s = scale
    points = [(x + 0 * s, y + 105 * s), (x + 28 * s, y + 75 * s), (x + 52 * s, y + 91 * s), (x + 79 * s, y + 45 * s), (x + 106 * s, y + 59 * s), (x + 138 * s, y + 8 * s)]
    draw.line(points, fill=BLUE, width=max(2, int(5 * s)), joint="curve")
    for px, py in points:
        draw.ellipse((px - 5 * s, py - 5 * s, px + 5 * s, py + 5 * s), fill=BLUE)


def _tick_step(value: float) -> float:
    raw = max(value, 1.0)
    magnitude = 10 ** math.floor(math.log10(raw))
    for multiplier in (1, 2, 5, 10):
        step = multiplier * magnitude
        if raw / step <= 6:
            return step
    return 10 * magnitude


def _downsample(series: list[dict], maximum: int = 220) -> list[dict]:
    if len(series) <= maximum:
        return series
    indices = [round(i * (len(series) - 1) / (maximum - 1)) for i in range(maximum)]
    return [series[i] for i in indices]


def _frame(fact: dict, progress: float) -> Image.Image:
    comparison = fact["comparison"]
    series = _downsample(comparison["series"])
    initial = float(comparison["initialAmount"])
    values = [float(point["value"]) for point in series]
    final_value = values[-1]
    y_max = math.ceil(max(initial, max(values)) * 1.15 / _tick_step(max(initial, max(values)))) * _tick_step(max(initial, max(values)))

    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)

    # Headline: same visual grammar as the reference, with original copy.
    y = 74
    y = _center_segments(draw, y, [("If someone invested ", BLACK, False), (_money(initial), GREEN, True)], 72)
    y = _center_segments(draw, y + 4, [("in ", BLACK, False), (comparison["assetLabel"], BLUE, True), (" instead of", BLACK, False)], 72)
    _center_segments(draw, y + 4, [("keeping ", BLACK, False), ("cash", BLACK, True)], 72)

    _draw_money_bag(draw, 105, 384, 1.05)
    _draw_mini_chart(draw, 404, 405, 1.25)
    _draw_wallet(draw, 817, 392, 0.88)

    left, right = 135, 960
    top, bottom = 720, 1588
    chart_height = bottom - top

    # Grid and axes.
    for tick in range(6):
        value = y_max * tick / 5
        yy = bottom - (value / y_max) * chart_height
        draw.line((left, yy, right, yy), fill=GRID, width=2)
        label = _money(value)
        draw.text((left - 16, yy), label, font=_font(28, bold=True), fill=BLACK, anchor="ra")
    draw.line((left, top, left, bottom), fill=BLACK, width=6)
    draw.line((left, bottom, right, bottom), fill=BLACK, width=6)

    def xy(index: int, value: float) -> tuple[float, float]:
        x = left + (right - left) * index / max(1, len(series) - 1)
        yy = bottom - (value / y_max) * chart_height
        return x, yy

    # Cash is the constant green reference line.
    cash_y = xy(0, initial)[1]
    draw.line((left, cash_y, right, cash_y), fill=GREEN, width=7)
    draw.rounded_rectangle((right - 218, cash_y - 37, right - 10, cash_y + 37), radius=16, fill=LIGHT_GREEN)
    draw.text((right - 114, cash_y), f"Cash\n{_money(initial)}", font=_font(25, bold=True), fill=GREEN, anchor="mm", align="center")

    # Reveal the adjusted-price series over the whole video.
    visible = max(2, min(len(series), int(progress * (len(series) - 1)) + 1))
    line = [xy(i, values[i]) for i in range(visible)]
    draw.line(line, fill=BLUE, width=10, joint="curve")
    end_x, end_y = xy(visible - 1, values[visible - 1])
    draw.ellipse((end_x - 9, end_y - 9, end_x + 9, end_y + 9), fill=BLUE)
    label_value = values[visible - 1]
    label_x = min(max(left + 12, end_x + 14), right - 180)
    draw.text((label_x, max(top + 14, end_y - 24)), f"{comparison['assetLabel']}\n{_money(label_value)}", font=_font(28, bold=True), fill=BLUE)

    # Date labels and tiny provenance line keep the chart understandable when
    # the video is reposted without its description.
    date_labels = [series[0].get("date", "")[:4], series[len(series) // 2].get("date", "")[:4], series[-1].get("date", "")[:4]]
    for fraction, label in zip((0, 0.5, 1), date_labels):
        xx = left + (right - left) * fraction
        draw.text((xx, bottom + 28), label, font=_font(28, bold=True), fill=BLACK, anchor="ma")

    source = comparison.get("asOf", "")[:10]
    draw.text((52, 1698), f"Historical comparison • {date_labels[0]}–{date_labels[-1]} • data through {source}", font=_font(24), fill=MUTED)
    draw.text((52, 1742), "Educational illustration — not financial advice. Past performance is not a guarantee.", font=_font(22), fill=MUTED)
    draw.text((52, 1808), "THE DIFFERENCE MONEY", font=_font(30, bold=True), fill=BLUE)
    return image


def render_comparison_video(fact: dict, audio_path: str, output_path: str, duration: float | None = None) -> str:
    """Render a 60+ second comparison animation and pad the voiceover safely."""
    series = fact.get("comparison", {}).get("series") or []
    if len(series) < 2:
        raise ValueError("Comparison braucht mindestens zwei historische Datenpunkte")

    total = float(duration or os.environ.get("COMPARISON_DURATION", "61.2"))
    if total <= 60:
        total = 61.2
    fps = max(8, int(os.environ.get("COMPARISON_RENDER_FPS", "15")))
    frame_count = max(1, math.ceil(total * fps))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}", "-r", str(fps), "-i", "-",
        "-i", audio_path,
        "-filter_complex", f"[1:a]apad,atrim=duration={total:.3f}[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-pix_fmt", "yuv420p",
        "-r", "30", "-t", f"{total:.3f}", "-movflags", "+faststart", output_path,
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for index in range(frame_count):
            progress = index / max(1, frame_count - 1)
            process.stdin.write(_frame(fact, progress).tobytes())
        process.stdin.close()
    except (BrokenPipeError, OSError):
        if process.stdin:
            process.stdin.close()
    stderr = process.stderr.read().decode("utf-8", errors="replace")
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"Comparison-Video konnte nicht gerendert werden:\n{stderr[-2500:]}")
    return output_path
