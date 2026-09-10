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
        "/System/Library/Fonts/Supplemental/Comic Sans MS.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "bold": [
        "/System/Library/Fonts/Supplemental/Comic Sans MS Bold.ttf",
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


def _axis_font(size: int = 18) -> ImageFont.FreeTypeFont:
    """Compact axis font so every annual tick remains readable."""
    paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
    ]
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return _font(size, bold=True)


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


def _draw_house(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Small original house icon for purchase-vs-investment comparisons."""
    s = scale
    roof = [(x + 7 * s, y + 62 * s), (x + 78 * s, y + 4 * s), (x + 149 * s, y + 62 * s)]
    draw.polygon(roof, fill=(68, 91, 125), outline=(42, 57, 83))
    draw.rectangle((x + 24 * s, y + 58 * s, x + 133 * s, y + 143 * s), fill=(246, 238, 220), outline=(42, 57, 83), width=max(1, int(4 * s)))
    draw.rectangle((x + 70 * s, y + 98 * s, x + 92 * s, y + 143 * s), fill=(194, 75, 68), outline=(122, 51, 46), width=max(1, int(3 * s)))
    draw.rectangle((x + 39 * s, y + 82 * s, x + 61 * s, y + 105 * s), fill=(110, 170, 212), outline=(42, 57, 83), width=max(1, int(3 * s)))
    draw.rectangle((x + 101 * s, y + 82 * s, x + 123 * s, y + 105 * s), fill=(110, 170, 212), outline=(42, 57, 83), width=max(1, int(3 * s)))
    draw.ellipse((x + 85 * s, y + 119 * s, x + 90 * s, y + 124 * s), fill=(246, 220, 115))
    draw.ellipse((x + 10 * s, y + 135 * s, x + 48 * s, y + 155 * s), fill=(103, 173, 91))
    draw.ellipse((x + 113 * s, y + 135 * s, x + 151 * s, y + 155 * s), fill=(103, 173, 91))


def _draw_car(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Original vector car icon for purchase-vs-stock comparisons."""
    s = scale
    draw.ellipse((x + 10 * s, y + 135 * s, x + 170 * s, y + 155 * s), fill=(224, 226, 230))
    body = [
        (x + 12 * s, y + 96 * s), (x + 35 * s, y + 91 * s),
        (x + 61 * s, y + 48 * s), (x + 121 * s, y + 48 * s),
        (x + 151 * s, y + 91 * s), (x + 166 * s, y + 98 * s),
        (x + 166 * s, y + 130 * s), (x + 12 * s, y + 130 * s),
    ]
    draw.polygon(body, fill=(68, 91, 125), outline=(42, 57, 83))
    draw.polygon(
        [(x + 65 * s, y + 53 * s), (x + 82 * s, y + 53 * s),
         (x + 82 * s, y + 88 * s), (x + 49 * s, y + 88 * s)],
        fill=(166, 205, 224), outline=(42, 57, 83),
    )
    draw.polygon(
        [(x + 87 * s, y + 53 * s), (x + 119 * s, y + 53 * s),
         (x + 143 * s, y + 88 * s), (x + 87 * s, y + 88 * s)],
        fill=(166, 205, 224), outline=(42, 57, 83),
    )
    draw.rectangle((x + 20 * s, y + 99 * s, x + 158 * s, y + 117 * s), fill=(91, 144, 214))
    draw.ellipse((x + 28 * s, y + 116 * s, x + 57 * s, y + 145 * s), fill=(35, 38, 43), outline=(18, 18, 18))
    draw.ellipse((x + 121 * s, y + 116 * s, x + 150 * s, y + 145 * s), fill=(35, 38, 43), outline=(18, 18, 18))
    draw.ellipse((x + 37 * s, y + 125 * s, x + 48 * s, y + 136 * s), fill=(183, 188, 195))
    draw.ellipse((x + 130 * s, y + 125 * s, x + 141 * s, y + 136 * s), fill=(183, 188, 195))
    draw.rounded_rectangle((x + 148 * s, y + 98 * s, x + 164 * s, y + 108 * s), radius=int(3 * s), fill=(246, 220, 115))


def _draw_earbuds(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Original vector earbuds case for small consumer-product comparisons."""
    s = scale
    draw.rounded_rectangle((x + 28 * s, y + 75 * s, x + 132 * s, y + 143 * s), radius=int(18 * s), fill=(239, 243, 247), outline=(161, 170, 181), width=max(1, int(3 * s)))
    draw.arc((x + 28 * s, y + 51 * s, x + 132 * s, y + 105 * s), 180, 360, fill=(161, 170, 181), width=max(1, int(3 * s)))
    draw.line((x + 80 * s, y + 81 * s, x + 80 * s, y + 137 * s), fill=(190, 198, 207), width=max(1, int(2 * s)))
    for offset in (0, 58):
        draw.ellipse((x + (40 + offset) * s, y + 20 * s, x + (64 + offset) * s, y + 48 * s), fill=(250, 252, 254), outline=(161, 170, 181), width=max(1, int(3 * s)))
        draw.rounded_rectangle((x + (49 + offset) * s, y + 39 * s, x + (64 + offset) * s, y + 91 * s), radius=int(7 * s), fill=(250, 252, 254), outline=(161, 170, 181), width=max(1, int(3 * s)))


def _draw_football(draw: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0) -> None:
    """Simple original football icon for sports-fee comparisons."""
    s = scale
    draw.ellipse((x + 20 * s, y + 18 * s, x + 140 * s, y + 138 * s), fill=(245, 245, 242), outline=(45, 45, 45), width=max(1, int(4 * s)))
    center = (x + 80 * s, y + 78 * s)
    pentagon = [
        (x + 80 * s, y + 56 * s), (x + 101 * s, y + 71 * s),
        (x + 93 * s, y + 96 * s), (x + 67 * s, y + 96 * s),
        (x + 59 * s, y + 71 * s),
    ]
    draw.polygon(pentagon, fill=(45, 45, 45))
    for px, py in ((38, 55), (122, 55), (44, 113), (116, 113)):
        draw.line((center[0], center[1], x + px * s, y + py * s), fill=(85, 85, 85), width=max(1, int(3 * s)))


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


def _draw_time_axis(draw: ImageDraw.ImageDraw, series: list[dict], progress: float,
                    left: int, right: int, bottom: int, plot_right: int | None = None) -> tuple[str, str]:
    """Animate the time axis like the reference explainer.

    The visible history is compressed into a stable chart window as new years
    arrive. This keeps the current point at the right edge while the year
    labels and ticks move along with the history instead of growing into a
    fixed, increasingly crowded strip.
    """
    if not series:
        return "", ""
    denominator = max(1, len(series) - 1)
    first_year_at: dict[str, float] = {}
    for index, point in enumerate(series):
        year = str(point.get("date", ""))[:4]
        if len(year) == 4 and year not in first_year_at:
            first_year_at[year] = index / denominator

    plot_right = plot_right or right
    current_position = min(float(denominator), max(0.0, progress * denominator))
    current_index = min(len(series) - 1, max(0, int(current_position)))
    current_year = str(series[current_index].get("date", ""))[:4]
    visible_denominator = max(1.0, current_position)
    cursor_x = plot_right if current_position > 0 else left
    draw.line((cursor_x, bottom - 14, cursor_x, bottom + 17), fill=BLUE, width=4)

    visible_years = [
        (year, position)
        for year, position in first_year_at.items()
        if position * denominator <= current_position + 0.5
    ]
    label_step = max(1, math.ceil(max(0, len(visible_years) - 1) / 5))
    label_indices = set(range(0, len(visible_years), label_step))
    if visible_years:
        label_indices.add(len(visible_years) - 1)

    font = _axis_font(18)
    for visible_number, (year, position) in enumerate(visible_years):
        index = position * denominator
        x = left + (plot_right - left) * min(1.0, index / visible_denominator)
        reveal = min(1.0, max(0.0, (current_position - index) / max(0.55, denominator * 0.018)))
        y = bottom + 28 + (1.0 - reveal) * 14
        colour = BLUE if year == current_year else BLACK
        draw.line((x, bottom, x, bottom + 12), fill=colour, width=2)
        if visible_number in label_indices:
            draw.text((x, y), year, font=font, fill=colour, anchor="ma")

    return str(series[0].get("date", ""))[:4], str(series[-1].get("date", ""))[:4]


def _frame(fact: dict, progress: float) -> Image.Image:
    comparison = fact["comparison"]
    full_series = comparison["series"]
    series = _downsample(full_series)
    initial = float(comparison["initialAmount"])
    values = [float(point["value"]) for point in series]
    final_value = values[-1]
    y_max = math.ceil(max(initial, max(values)) * 1.15 / _tick_step(max(initial, max(values)))) * _tick_step(max(initial, max(values)))

    image = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), WHITE)
    draw = ImageDraw.Draw(image)

    # Headline: same visual grammar as the reference, with original copy.
    y = 74
    y = _center_segments(draw, y, [("If Someone invested ", BLACK, False), (_money(initial), GREEN, True)], 72)
    y = _center_segments(draw, y + 4, [("in ", BLACK, False), (comparison["assetLabel"], BLUE, True), (" instead of", BLACK, False)], 72)
    _center_segments(draw, y + 4, [("", BLACK, False), (comparison.get("alternativePhrase", "keeping cash"), BLACK, True)], 72)

    _draw_money_bag(draw, 105, 384, 1.05)
    _draw_mini_chart(draw, 404, 405, 1.25)
    alternative_icon = comparison.get("alternativeIcon")
    if alternative_icon == "house":
        _draw_house(draw, 817, 392, 0.88)
    elif alternative_icon == "car":
        _draw_car(draw, 817, 392, 0.88)
    elif alternative_icon == "earbuds":
        _draw_earbuds(draw, 817, 392, 0.88)
    elif alternative_icon == "football":
        _draw_football(draw, 817, 392, 0.88)
    else:
        _draw_wallet(draw, 817, 392, 0.88)

    left, right = 160, 960
    plot_right = right - 210
    top, bottom = 720, 1588
    chart_height = bottom - top

    # Grid and axes.
    for tick in range(6):
        value = y_max * tick / 5
        yy = bottom - (value / y_max) * chart_height
        draw.line((left, yy, right, yy), fill=GRID, width=2)
        label = _money(value)
        draw.text((left - 18, yy), label, font=_font(24, bold=True), fill=BLACK, anchor="ra")
    draw.line((left, top, left, bottom), fill=BLACK, width=6)
    draw.line((left, bottom, right, bottom), fill=BLACK, width=6)

    position = min(len(series) - 1, max(0.0, progress * (len(series) - 1)))
    visible_denominator = max(1.0, position)
    whole = int(position)
    fraction = position - whole

    def xy(index: float, value: float) -> tuple[float, float]:
        x = left + (plot_right - left) * min(1.0, index / visible_denominator)
        yy = bottom - (value / y_max) * chart_height
        return x, yy

    current_value = values[whole] + (values[min(whole + 1, len(values) - 1)] - values[whole]) * fraction
    current_y = xy(position, current_value)[1]

    # The alternative is a constant green reference line, just like the
    # reference explainer. It is deliberately labelled as a reference rather
    # than pretending to model ownership costs or property appreciation.
    reference_y = xy(0, initial)[1]
    draw.line((left, reference_y, plot_right, reference_y), fill=GREEN, width=7)
    reference_label = comparison.get("alternativeLabel", "Cash")
    reference_label_y = reference_y
    if abs(current_y - reference_y) < 130:
        # Keep the two endpoint labels readable when the series finishes near
        # the reference line; the lower slot mirrors the stacked labels in the
        # reference videos and stays above the x-axis.
        reference_label_y = min(bottom - 40, reference_y + 90)
    draw.rounded_rectangle((right - 218, reference_label_y - 37, right - 10, reference_label_y + 37), radius=16, fill=LIGHT_GREEN)
    draw.text((right - 114, reference_label_y), f"{reference_label}\n{_money(initial)}", font=_font(25, bold=True), fill=GREEN, anchor="mm", align="center")

    # Reveal the adjusted-price series over the whole video.
    line = [xy(i, values[i]) for i in range(whole + 1)]
    if whole < len(series) - 1:
        interpolated = values[whole] + (values[whole + 1] - values[whole]) * fraction
        line.append(xy(whole + fraction, interpolated))
    draw.line(line, fill=BLUE, width=10, joint="curve")
    end_x, end_y = line[-1]
    draw.ellipse((end_x - 9, end_y - 9, end_x + 9, end_y + 9), fill=BLUE)
    label_value = current_value
    label_x = min(max(left + 12, end_x + 14), right - 180)
    chart_label = comparison.get("chartLabel", comparison["assetLabel"])
    draw.text((label_x, max(top + 14, end_y - 24)), f"{chart_label}\n{_money(label_value)}", font=_font(28, bold=True), fill=BLUE)

    # The time axis moves with the data instead of showing three static years.
    # This keeps each annual change synchronized with the moving line.
    start_year, end_year = _draw_time_axis(draw, full_series, progress, left, right, bottom, plot_right=plot_right)

    source = comparison.get("asOf", "")[:10]
    draw.text((52, 1698), f"Historical comparison • {start_year}–{end_year} • data through {source}", font=_font(24), fill=MUTED)
    reference_note = comparison.get("referenceNote", "")
    if reference_note:
        draw.text((52, 1738), reference_note, font=_font(20), fill=MUTED)
        disclaimer_y = 1772
    else:
        disclaimer_y = 1742
    draw.text((52, disclaimer_y), "Educational illustration — not financial advice. Past performance is not a guarantee.", font=_font(22), fill=MUTED)
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
    fps = max(15, int(os.environ.get("COMPARISON_RENDER_FPS", "30")))
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
