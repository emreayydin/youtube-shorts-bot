"""Original explanatory motion graphics for source-backed trivia stories."""
import math
import subprocess
import tempfile
from PIL import Image, ImageDraw


def render_orbital_visibility(duration, output, font, ffmpeg="ffmpeg"):
    """An explicitly schematic view; no invented orbit heights or image data."""
    width, height, fps = 1080, 1920, 24
    base = Image.new("RGB", (width, height), (5, 16, 31))
    gradient = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        gradient.line((0, y, width, y), fill=(5 + int(8*ratio), 16 + int(12*ratio), 31 + int(15*ratio)))
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([
            ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
            "-pix_fmt", "yuv420p", "-an", "-t", str(duration), str(output),
        ], stdin=subprocess.PIPE, stderr=errors)
        try:
            for index in range(math.ceil(duration * fps)):
                t = index / fps
                image = base.copy()
                d = ImageDraw.Draw(image)
                # Large diagram between the headline and caption safe areas.
                d.rounded_rectangle((70, 555, 950, 830), radius=30, fill=(14, 38, 48))
                for ridge in range(3):
                    points = [(90+i*12, 700 + ridge*38 + 22*math.sin(i*.18+ridge)) for i in range(70)]
                    d.line(points, fill=(35+ridge*5, 72+ridge*4, 67+ridge*3), width=12)
                visible = max(3, min(69, int(70*min(1.,t/4))))
                wall = [(90+i*12, 704+22*math.sin(i*.18)) for i in range(visible)]
                if len(wall) > 1:
                    d.line(wall, fill=(123, 146, 123), width=6)
                scan = 92 + int((t*.11 % 1)*824)
                d.line((scan, 612, scan, 788), fill=(125, 211, 252), width=3)
                d.ellipse((scan-7, 605, scan+7, 619), fill=(125, 211, 252))
                d.text((102, 579), "SCHEMATISCHE DARSTELLUNG", font=font(24), fill=(155, 182, 194))
                message = ("Länge allein reicht nicht" if t < duration*.40 else
                           "Breite und Kontrast entscheiden" if t < duration*.75 else
                           "Kameraaufnahme ≠ bloßes Auge")
                d.text((102, 777), message, font=font(34), fill=(225, 241, 248))
                process.stdin.write(image.tobytes())
            process.stdin.close()
        except BaseException:
            process.kill()
            process.wait()
            raise
        if process.wait() != 0:
            errors.seek(0)
            raise RuntimeError(errors.read().decode(errors="replace")[-2500:])
    return str(output)
