"""Generates YouTube channel branding: profile picture (800x800) and banner
(2048x1152) matching the channel's facts/trivia style."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.dirname(os.path.abspath(__file__))

# Palette
NAVY_TOP = (11, 20, 55)
PURPLE_BOTTOM = (59, 42, 140)
GOLD = (255, 210, 63)
WHITE = (255, 255, 255)
LIGHT = (210, 215, 240)

BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def gradient(w, h, top, bottom):
    base = Image.new("RGB", (w, h), top)
    layer = Image.new("RGB", (w, h), bottom)
    mask = Image.new("L", (w, h))
    mask.putdata([int(255 * (y / h)) for y in range(h) for _ in range(w)])
    base.paste(layer, (0, 0), mask)
    return base


def draw_bulb(d, cx, cy, r):
    """Draws a glowing lightbulb (idea / fact icon) with a zigzag filament."""
    # soft glow (subtle)
    for i, a in enumerate([22, 38, 60]):
        rr = r + (3 - i) * 18
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(255, 210, 63, a))
    # bulb
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=GOLD)
    # zigzag filament (W) so it reads as a bulb, not a sun
    fw = max(5, r // 12)
    pts = [
        (cx - 0.42 * r, cy + 0.18 * r),
        (cx - 0.21 * r, cy - 0.30 * r),
        (cx,            cy + 0.12 * r),
        (cx + 0.21 * r, cy - 0.30 * r),
        (cx + 0.42 * r, cy + 0.18 * r),
    ]
    d.line(pts, fill=(70, 50, 0), width=fw, joint="curve")
    # two contact wires down to the base
    d.line([(cx - 0.42 * r, cy + 0.18 * r), (cx - 0.15 * r, cy + 0.7 * r)],
           fill=(70, 50, 0), width=fw)
    d.line([(cx + 0.42 * r, cy + 0.18 * r), (cx + 0.15 * r, cy + 0.7 * r)],
           fill=(70, 50, 0), width=fw)
    # screw base
    base_w, base_h = int(r * 0.85), int(r * 0.55)
    bx, by = cx - base_w // 2, cy + r - 2
    d.rounded_rectangle([bx, by, bx + base_w, by + base_h], radius=8, fill=(70, 70, 82))
    for k in range(3):
        yy = by + 8 + k * (base_h // 3)
        d.line([bx, yy, bx + base_w, yy], fill=(35, 35, 44), width=5)


def make_profile():
    S = 800
    img = gradient(S, S, NAVY_TOP, PURPLE_BOTTOM).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")
    draw_bulb(d, S // 2, 330, 150)
    f = font(BOLD, 92)
    text = "FAKTEN"
    w = d.textlength(text, font=f)
    d.text(((S - w) / 2, 540), text, font=f, fill=WHITE, stroke_width=5, stroke_fill=(0, 0, 0))
    f2 = font(BOLD, 44)
    sub = "TÄGLICH NEU"
    w2 = d.textlength(sub, font=f2)
    d.rounded_rectangle([(S - w2) / 2 - 24, 650, (S + w2) / 2 + 24, 712], radius=16, fill=GOLD)
    d.text(((S - w2) / 2, 658), sub, font=f2, fill=(11, 20, 55))
    path = os.path.join(OUT, "profile_800x800.png")
    img.convert("RGB").save(path)
    return path


def make_banner():
    W, H = 2048, 1152
    img = gradient(W, H, NAVY_TOP, PURPLE_BOTTOM).convert("RGBA")
    d = ImageDraw.Draw(img, "RGBA")

    # decorative dots
    import random
    random.seed(7)
    for _ in range(70):
        x, y = random.randint(0, W), random.randint(0, H)
        rr = random.randint(1, 3)
        d.ellipse([x, y, x + rr, y + rr], fill=(255, 255, 255, random.randint(20, 70)))

    # everything inside the safe area (center 1546x423)
    cx, cy = W // 2, H // 2
    draw_bulb(d, cx - 620, cy - 10, 115)

    f_name = font(BOLD, 150)
    name = "FAKTASTISCH"
    d.text((cx - 350, cy - 130), name, font=f_name, fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))

    f_tag = font(REG, 56)
    d.text((cx - 345, cy + 40), "Verblüffende Fakten – täglich in 60 Sekunden",
           font=f_tag, fill=LIGHT)

    f_small = font(BOLD, 40)
    chip = "NEUES SHORT JEDEN TAG · 14:00 UHR"
    w = d.textlength(chip, font=f_small)
    d.rounded_rectangle([cx - 345, cy + 120, cx - 345 + w + 44, cy + 184], radius=18, fill=GOLD)
    d.text((cx - 323, cy + 130), chip, font=f_small, fill=(11, 20, 55))

    path = os.path.join(OUT, "banner_2048x1152.png")
    img.convert("RGB").save(path)
    return path


if __name__ == "__main__":
    p = make_profile()
    b = make_banner()
    print("Profilbild:", p)
    print("Banner:", b)
