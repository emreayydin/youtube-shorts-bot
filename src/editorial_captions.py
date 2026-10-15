"""Readable, word-timed editorial captions for the trivia lane.

Only uses the narration's real WordBoundary timestamps. No inferred numbers,
claims or sources are added to the script. Finance comparison renders keep
their separate design.
"""
from PIL import Image, ImageDraw


def caption_events(words, total, max_words=4, max_chars=28):
    """Stable phrase windows, split at punctuation and long German words."""
    groups, current = [], []
    for word in words:
        if current and (len(current) >= max_words or
                        len(" ".join(w["text"] for w in current + [word])) > max_chars):
            groups.append(current)
            current = []
        current.append(word)
        if word["text"].endswith((".", "!", "?", ";", ":", ",")):
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    events = []
    for gi, group in enumerate(groups):
        group_end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else total
        for wi, word in enumerate(group):
            start = word["start"] if events else 0.0
            end = group[wi + 1]["start"] if wi + 1 < len(group) else group_end
            if end > start:
                events.append({"words": group, "active": wi, "start": start,
                               "end": end, "progress": start / max(total, 0.001)})
    return events


def editorial_frame(fact, event, path, font, wrap, width=1080, height=1920):
    """One focal caption, generous Shorts safe area and a traceable source."""
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    accent = (134, 239, 172) if fact.get("category") in {"Natur", "Biologie"} else (125, 211, 252)
    draw.rectangle((0, 0, width, height), fill=(3, 9, 20, 70))
    draw.rectangle((0, 0, width, 520), fill=(3, 9, 20, 150))
    draw.text((82, 150), "FAKTASTISCH", font=font(34), fill=accent)
    category = fact.get("category", "WISSEN").upper()
    draw.text((82, 204), category, font=font(30), fill=(220, 230, 240))

    title = fact.get("title", "")
    title_size = 66
    while title_size > 46 and len(wrap(draw, title, font(title_size), 870)) > 3:
        title_size -= 2
    y = 278
    for line in wrap(draw, title, font(title_size), 870)[:3]:
        draw.text((80, y), line, font=font(title_size), fill="white", stroke_width=1)
        y += title_size * 1.18

    # Allocate every token's box in advance, so highlighting never reflows it.
    tokens = [w["text"] for w in event["words"]]
    size = 96
    while size > 56 and any(draw.textlength(t, font=font(size)) > 820 for t in tokens):
        size -= 2
    face, gap = font(size), 26
    rows, row, used = [], [], 0
    for index, token in enumerate(tokens):
        token_width = draw.textlength(token, font=face)
        if row and used + gap + token_width > 850:
            rows.append(row)
            row, used = [], 0
        row.append((index, token, token_width))
        used += (gap if len(row) > 1 else 0) + token_width
    if row:
        rows.append(row)

    block_h = len(rows) * (size + 26)
    top = 1020 - block_h / 2
    draw.rounded_rectangle((58, top - 40, 970, top + block_h + 28), radius=28,
                           fill=(4, 13, 27, 218))
    draw.rounded_rectangle((58, top - 40, 66, top + block_h + 28), radius=4, fill=accent)
    for ri, row in enumerate(rows):
        row_w = sum(v[2] for v in row) + gap * (len(row) - 1)
        x, y = (1028 - row_w) / 2, top + ri * (size + 26)
        for index, token, token_width in row:
            active = index == event["active"]
            draw.text((x, y), token, font=face, fill=accent if active else "white",
                      stroke_width=2, stroke_fill=(4, 13, 27))
            if active:
                draw.rounded_rectangle((x, y + size + 8, x + token_width, y + size + 13),
                                       radius=2, fill=accent)
            x += token_width + gap

    # Source remains above platform controls rather than along the bottom edge.
    source = " · ".join(fact.get("sources") or [])
    if source:
        lines = wrap(draw, "QUELLE: " + source, font(29), 850)
        for line_no, line in enumerate(lines[:3]):
            draw.text((82, 1510 + line_no * 38), line, font=font(29), fill=(214, 225, 235))
    progress = min(1, max(0, event.get("progress", 0)))
    draw.rounded_rectangle((82, 1430, 920, 1436), radius=3, fill=(100, 120, 140, 90))
    if progress > 0:
        draw.rounded_rectangle((82, 1430, 82 + 838 * progress, 1436), radius=3, fill=accent)
    image.save(path)
    return path
