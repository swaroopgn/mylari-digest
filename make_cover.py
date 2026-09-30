#!/usr/bin/env python3
"""Show cover per save-to-spotify cover-image.md, Path 3 (CDN artwork + Pillow typography).
No AI image API is configured on this box, so the CDN base art is used (variant chosen by hash of show name).
Output: cover.jpg (1400x1400, <1 MB, show name in white Montserrat Bold, bottom-left)."""
import hashlib, io, json, os, sys, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
TITLE = json.loads((ROOT / "show.json").read_text())["title"]
CANVAS, MARGIN = 1400, 64
MAX_TEXT_WIDTH = int((CANVAS - 2 * MARGIN) * 0.85)
MAX_TEXT_HEIGHT = CANVAS - MARGIN - CANVAS // 2
MIN_FONT_SIZE, MAX_FONT_SIZE, LEADING_FACTOR = 100, 400, 0.97
FONT_CACHE = Path.home() / ".cache" / "save-to-spotify" / "fonts"
FONT_URL = "https://raw.githubusercontent.com/JulietaUla/Montserrat/master/fonts/ttf/Montserrat-Bold.ttf"
LOCAL_VAR = "/usr/share/fonts/truetype/sand-box/google/Montserrat/Montserrat-VariableFont_wght.ttf"


def load_font(size):
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    p = FONT_CACHE / "Montserrat-Bold.ttf"
    if not p.exists():
        try:
            urllib.request.urlretrieve(FONT_URL, p)
        except Exception:
            pass
    if p.exists():
        return ImageFont.truetype(str(p), size)
    f = ImageFont.truetype(LOCAL_VAR, size); f.set_variation_by_name("Bold"); return f


def width(font, t):
    b = font.getbbox(t); return b[2] - b[0]


def combos(words, n):
    if n == 1:
        yield [words]; return
    for i in range(1, len(words) - n + 2):
        for rest in combos(words[i:], n - 1):
            yield [words[:i]] + rest


def break_lines(title, font):
    if ", " in title:  # break on meaning: keep comma-separated phrases together when they fit
        lines = [x if i == len(title.split(", ")) - 1 else x + "," for i, x in enumerate(title.split(", "))]
        if len(lines) <= 3:
            return lines  # fit() shrinks the font until these lines fit
    words, best, best_d = title.split(), None, float("inf")
    for n in range(1, min(len(words), 3) + 1):
        for c in combos(words, n):
            lines = [" ".join(p) for p in c]
            ws = [width(font, l) for l in lines]
            if max(ws) > MAX_TEXT_WIDTH: continue
            if max(ws) - min(ws) < best_d: best_d, best = max(ws) - min(ws), lines
    return best or [title]


def fit(title):
    for sz in range(MAX_FONT_SIZE, MIN_FONT_SIZE - 1, -2):
        f = load_font(sz); lines = break_lines(title, f)
        if len(lines) > 3 or max(width(f, l) for l in lines) > MAX_TEXT_WIDTH: continue
        lh = int(sz * LEADING_FACTOR)
        if lh * (len(lines) - 1) + f.getbbox(lines[-1])[3] > MAX_TEXT_HEIGHT: continue
        return f, lines, sz
    f = load_font(MIN_FONT_SIZE); return f, break_lines(title, f), MIN_FONT_SIZE


def main(out=ROOT / "cover.jpg"):
    n = int(hashlib.sha256(TITLE.encode()).hexdigest(), 16) % 20 + 1
    url = f"https://save-to-spotify.spotifycdn.com/assets/uts-{n:02d}.png"
    base = Image.open(io.BytesIO(urllib.request.urlopen(url, timeout=30).read())).convert("RGB")
    s = min(base.size); base = base.crop(((base.width - s) // 2, (base.height - s) // 2,
                                          (base.width + s) // 2, (base.height + s) // 2)).resize((CANVAS, CANVAS))
    d = ImageDraw.Draw(base); f, lines, sz = fit(TITLE); lh = int(sz * LEADING_FACTOR)
    y = max(CANVAS - MARGIN - (lh * (len(lines) - 1) + f.getbbox(lines[-1])[3]), CANVAS // 2)
    for l in lines:
        d.text((MARGIN, y), l, font=f, fill=(255, 255, 255)); y += lh
    base.save(out, "JPEG", quality=90, optimize=True)
    print(out, f"base=uts-{n:02d}", lines, sz, os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cover.jpg")
