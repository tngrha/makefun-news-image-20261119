"""One Day in One Page - Thursday 19 November 2026.

A pure-stdlib Python 3.13 program that paints a 1024x1024 newspaper
front page summing up the day's world news and writes it to
<MAKEFUN_OUTPUT_DIR>/entry.png. No Pillow, no system fonts, no
network: the glyphs live in a compact string table below and the PNG
bytes are assembled by hand. The output is fully deterministic -
same bytes on every run. Facts were verified against news reports
published on 19 November 2026. Text is set in UPPERCASE, as a
broadsheet would set it.
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024

# Newsprint palette.
PAPER = (248, 244, 233)
NAVY = (14, 40, 66)
NAVY2 = (22, 56, 88)
PANEL = (12, 36, 58)
INK = (26, 30, 36)
MUTED = (76, 82, 90)
RULE = (198, 190, 170)
LIGHT = (216, 226, 236)
GOLD = (202, 163, 40)
RED = (176, 32, 32)
GREEN = (46, 125, 50)
GREEN_D = (34, 96, 38)
TEAL = (16, 108, 108)
GREY = (112, 118, 124)
WHITE = (255, 255, 255)
TILE = (255, 255, 255)
PURPLE = (88, 62, 140)
BROWN = (122, 44, 44)
OCHRE = (90, 60, 20)
SLATE = (70, 70, 110)

# ------------------------------------------------------------------ glyphs
# One line per glyph: the character, then its seven 5-cell rows.
# 'SP' is the space, 'BULLET' the bullet. A parser below turns the
# block into the table the text routines use.
_FONT_BLOCK = """
SP ..... ..... ..... ..... ..... ..... .....
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..
" .#.#. .#.#. .#.#. ..... ..... ..... .....
# .#.#. .#.#. ##### .#.#. ##### .#.#. .#.#.
$ ..#.. .#### #.#.# .###. ..#.# ####. ..#..
% ##..# ##.#. ...#. ..#.. .#... #.##. #..##
& .##.. #..#. #..#. .#... #.#.# #..#. .##.#
' ..#.. ..#.. ..#.. ..... ..... ..... .....
( ...#. ..#.. .#... .#... .#... ..#.. ...#.
) .#... ..#.. ...#. ...#. ...#. ..#.. .#...
* ..... .#.#. ..#.. ##### ..#.. .#.#. .....
+ ..... ..#.. ..#.. ##### ..#.. ..#.. .....
, ..... ..... ..... ..... .##.. .##.. .#...
- ..... ..... ..... ##### ..... ..... .....
. ..... ..... ..... ..... ..... .##.. .##..
/ ....# ...#. ...#. ..#.. .#... .#... #....
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ####. ....# ....# .###. ....# ....# ####.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 .###. #.... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ...#. ..#.. ..#.. ..#..
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ....# .###.
: ..... .##.. .##.. ..... .##.. .##.. .....
; ..... .##.. .##.. ..... .##.. .##.. .#...
= ..... ..... ##### ..... ##### ..... .....
? .###. #...# ....# ...#. ..#.. ..... ..#..
@ .###. #...# #.### #.#.# #.### #.... .###.
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .#### #.... #.... #.... #.... #.... .####
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .#### #.... #.... #.### #...# #...# .###.
H #...# #...# #...# ##### #...# #...# #...#
I ##### ..#.. ..#.. ..#.. ..#.. ..#.. #####
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# ##..# ##..# #.#.# #..## #..## #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# ##.## #...#
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
BULLET ..... ..... .##.. .##.. ..... ..... .....
"""


def _build_font(block):
    table = {}
    for line in block.strip().splitlines():
        parts = line.split()
        key = parts[0]
        if key == "SP":
            key = " "
        elif key == "BULLET":
            key = "•"
        table[key] = parts[1:]
    return table


GLYPHS = _build_font(_FONT_BLOCK)
EMPTY_ROWS = ["....."] * 7


def glyph_rows(ch):
    """The seven 5-cell rows of a glyph, blanks for unknown chars."""
    return GLYPHS.get(ch, EMPTY_ROWS)


# ------------------------------------------------------------------ canvas
fb = bytearray(W * H * 3)


def put_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        fb[i] = c[0]
        fb[i + 1] = c[1]
        fb[i + 2] = c[2]


def box(x, y, w, h, c):
    """Solid rectangle, clipped to the canvas."""
    x0 = max(x, 0)
    y0 = max(y, 0)
    x1 = min(x + w, W)
    y1 = min(y + h, H)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(c) * (x1 - x0)
    n = (x1 - x0) * 3
    for yy in range(y0, y1):
        i = (yy * W + x0) * 3
        fb[i:i + n] = row


def seg(x0, y0, x1, y1, c):
    """One-pixel Bresenham segment."""
    dx = x1 - x0
    dy = y1 - y0
    sx = 1 if dx > 0 else -1
    sy = 1 if dy > 0 else -1
    dx = abs(dx)
    dy = abs(dy)
    if dx >= dy:
        err = 2 * dy - dx
        y = y0
        for k in range(dx + 1):
            put_px(x0 + k * sx, y, c)
            if err >= 0:
                y += sy
                err -= 2 * dx
            err += 2 * dy
    else:
        err = 2 * dx - dy
        x = x0
        for k in range(dy + 1):
            put_px(x, y0 + k * sy, c)
            if err >= 0:
                x += sx
                err -= 2 * dy
            err += 2 * dx


def seg_w(x0, y0, x1, y1, w, c):
    """Thick segment: parallel thin ones."""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    half = w // 2
    if dx >= dy:
        for k in range(-half, half + 1):
            seg(x0, y0 + k, x1, y1 + k, c)
    else:
        for k in range(-half, half + 1):
            seg(x0 + k, y0, x1 + k, y1, c)


def disc(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        box(cx - dx, cy + dy, 2 * dx + 1, 1, c)


def ring(cx, cy, r, c):
    x, y, d = 0, r, 1 - r
    while x <= y:
        for px, py in ((x, y), (y, x), (-x, y), (y, -x),
                       (x, -y), (-y, x), (-x, -y), (-y, -x)):
            put_px(cx + px, cy + py, c)
        if d < 0:
            d += 2 * x + 3
        else:
            d += 2 * (x - y) + 5
            y -= 1
        x += 1


def poly(pts, c):
    """Even-odd scanline polygon fill."""
    ys = [p[1] for p in pts]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            box(int(xs[i]), y, int(xs[i + 1]) - int(xs[i]) + 1, 1, c)


def rrect(x, y, w, h, r, c):
    box(x + r, y, w - 2 * r, h, c)
    box(x, y + r, w, h - 2 * r, c)
    for cx, cy in ((x + r, y + r), (x + w - r - 1, y + r),
                   (x + r, y + h - r - 1), (x + w - r - 1, y + h - r - 1)):
        disc(cx, cy, r, c)


def edge_box(x, y, w, h, r, width, border, fill):
    rrect(x, y, w, h, r, border)
    inner = r - width if r > width else 0
    rrect(x + width, y + width, w - 2 * width, h - 2 * width, inner, fill)

# ------------------------------------------------------------------ text
def upper_text(text):
    """Uppercase broadsheet text; fold curly quotes and dashes."""
    return (text.upper()
            .replace("’", "'").replace("‘", "'")
            .replace("–", "-").replace("—", "-"))


def glyph_w(text, scale, tracking=0):
    n = len(text)
    if n == 0:
        return 0
    return n * 5 * scale + (n - 1) * (scale + tracking)


def put_text(x, y, text, scale, c, tracking=0):
    """Set text at integer scale; advance is 6*scale + tracking."""
    step = 6 * scale + tracking
    cx = x
    for ch in text:
        rows = glyph_rows(ch)
        for ry in range(7):
            row = rows[ry]
            for rx in range(5):
                if row[rx] == "#":
                    box(cx + rx * scale, y + ry * scale, scale, scale, c)
        cx += step
    return cx


def wrap_text(text, scale, max_w, tracking=0):
    """Greedy word wrap by pixel width."""
    lines, cur = [], ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if glyph_w(trial, scale, tracking) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_text(text, scale, max_w, max_lines, tracking=0):
    """Wrap to at most max_lines lines, ellipsising the last one."""
    lines = wrap_text(text, scale, max_w, tracking)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    last = lines[-1]
    while last and glyph_w(last + "...", scale, tracking) > max_w:
        last = last[:-1].rstrip()
        if " " in last:
            last = last[:last.rfind(" ")].rstrip()
    lines[-1] = (last + "...") if last else "..."
    return lines


# ------------------------------------------------------------------ icons
def pict(kind, x, y, s, bg):
    """Flat pictogram in a coloured square, s = 52."""
    rrect(x, y, s, s, 10, bg)
    cx, cy = x + s // 2, y + s // 2
    if kind == "chart":  # Anthropic IPO: rising chart
        box(x + 10, y + s - 14, s - 20, 2, WHITE)
        pts = [(x + 11, y + 38), (x + 19, y + 34), (x + 27, y + 36),
               (x + 35, y + 26), (x + 43, y + 16)]
        for i in range(len(pts) - 1):
            seg_w(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 4, WHITE)
        poly([(x + 43, y + 10), (x + 51, y + 18), (x + 41, y + 20)], WHITE)
    elif kind == "radar":  # US-Iran: radar sweeps
        for r in (9, 16, 23):
            ring(cx, cy, r, WHITE)
        disc(cx, cy, 4, RED)
        seg_w(cx, cy, cx + 16, cy - 16, 3, WHITE)
        box(cx - 1, cy - 23, 2, 8, WHITE)
    elif kind == "warn":  # Gaza: warning triangle
        poly([(cx, y + 8), (x + s - 9, y + s - 10),
              (x + 9, y + s - 10)], WHITE)
        put_text(cx - 7, cy - 2, "!", 3, RED)
    elif kind == "bridge":  # Crimea bridge
        box(x + 8, y + s - 13, s - 16, 3, WHITE)
        for px in range(cx - 17, cx + 18):
            t = (px - cx) / 17.0
            py = (y + s - 13) - int(13 * (1 - t * t) ** 0.5)
            put_px(px, py, WHITE)
            put_px(px, py + 1, WHITE)
        for px in (x + 15, cx - 1, x + s - 18):
            box(px, y + 28, 3, 12, WHITE)
        box(cx - 8, y + 12, 16, 3, RED)
    elif kind == "bank":  # EU loan: bank and columns
        poly([(x + 7, y + 20), (cx, y + 9), (x + s - 7, y + 20)], WHITE)
        for px in (x + 13, x + 24, x + 35):
            box(px, y + 24, 4, 13, WHITE)
        box(x + 8, y + s - 13, s - 16, 4, WHITE)
    elif kind == "sat":  # Voyager 1: satellite and signal rings
        box(cx - 12, cy - 4, 24, 8, WHITE)
        box(cx - 4, cy - 11, 8, 22, GOLD)
        box(x + 6, cy - 3, 8, 6, WHITE)
        box(x + s - 14, cy - 3, 8, 6, WHITE)
        ring(cx, cy, 20, GOLD)
        ring(cx, cy, 24, GOLD)
    elif kind == "storm":  # Cyclone Akvan: spiral
        for r in (6, 12, 18):
            ring(cx, cy, r, WHITE)
        disc(cx, cy, 4, WHITE)
        seg_w(cx, cy, cx + 18, cy - 6, 3, WHITE)
        seg_w(cx - 6, cy + 14, cx + 6, cy + 18, 3, WHITE)
    elif kind == "scales":  # Jeffries / Speaker: scales of the house
        box(cx - 2, y + 9, 4, 30, WHITE)
        box(x + 12, y + 13, s - 24, 4, WHITE)
        for sx in (x + 14, x + s - 14):
            box(sx - 1, y + 17, 3, 11, WHITE)
            poly([(sx - 9, y + 28), (sx + 9, y + 28), (sx, y + 41)], WHITE)
        box(x + 14, y + s - 12, s - 28, 4, WHITE)


def hero_scene(x, y, w, h):
    """Vice City skyline at dusk, with a game controller in front."""
    rrect(x, y, w, h, 12, PANEL)
    # Dusk sky bands.
    box(x, y, w, 40, (58, 28, 66))
    box(x, y + 40, w, 30, (120, 52, 60))
    box(x, y + 70, w, 26, (214, 130, 60))
    # Low sun.
    disc(x + w - 52, y + 62, 20, (255, 214, 120))
    # Two depths of skyline.
    base = y + h - 118
    far = [(0, 46), (26, 34), (52, 58), (86, 30), (118, 52), (150, 38),
           (182, 60), (214, 36), (246, 54), (278, 42), (310, 58)]
    for bx, bh in far:
        box(x + bx, base + 58 - bh, 24, bh, (30, 44, 74))
    near = [(8, 78), (44, 96), (82, 66), (120, 104), (160, 72),
            (198, 92), (238, 64), (274, 86), (308, 70)]
    for bx, bh in near:
        box(x + bx, base + 118 - bh, 30, bh, (16, 26, 48))
    # Lit windows.
    for bx, bh in near:
        for wy in range(base + 118 - bh + 8, base + 110, 14):
            for wx in (x + bx + 5, x + bx + 17):
                box(wx, wy, 4, 5, GOLD)
    # Water line and reflections.
    box(x, base + 118, w, 2, GOLD)
    box(x + 40, base + 128, 90, 3, (214, 130, 60))
    box(x + 180, base + 138, 120, 3, (214, 130, 60))
    # Game controller, bottom centre.
    cx, cy = x + w // 2, base + 74
    rrect(cx - 62, cy - 22, 124, 46, 18, WHITE)
    disc(cx - 38, cy - 4, 9, NAVY2)
    disc(cx + 38, cy - 4, 9, NAVY2)
    box(cx - 8, cy - 14, 5, 16, NAVY2)
    box(cx - 13, cy - 9, 15, 5, NAVY2)
    for dx, dy, col in ((30, -12, RED), (40, -4, GREEN),
                        (30, 4, GOLD), (20, -4, TEAL)):
        disc(cx + dx, cy + dy, 4, col)

# ------------------------------------------------------------------ stories
# Verified brief for Thursday 19 November 2026. Sources: AP / People /
# Gulf Business (GTA VI launch); FinanceFeeds, ZeroHedge, The Desk,
# TradingView (Anthropic IPO); SimpleLife, Gulf Business, Cultura
# Colectiva / Reuters (US-Iran Gulf strikes); Crypto Economics / Sky
# News, Cultura Colectiva / Reuters (Gaza ground operation, Crimea
# bridge); Jagran Josh, Disclosure News / FT (EU Ukraine loan,
# Voyager 1, Cyclone Akvan); Newsmriti / NDTV, BBC (Jeffries);
# SimpleLife (Fed minutes, Trump-Xi-Putin Shenzhen talks); Jagran
# Josh (Nvidia acting CEO, US senators on AI cyber threats).
TILES = [
    ("chart", "MARKETS", GREEN_D,
     "Anthropic IPO: $81.3bn, biggest ever",
     "Claude maker priced at $83; debuts on Nasdaq as ANT today."),
    ("radar", "MIDDLE EAST", RED,
     "US and Iran trade fire in the Gulf",
     "US hit Qeshm Island site; Iran struck bases in Bahrain, Kuwait."),
    ("warn", "MIDDLE EAST", BROWN,
     "Israeli troops push into central Gaza",
     "Rare ground operation displaces families in a ceasefire zone."),
    ("bridge", "EUROPE", OCHRE,
     "Crimea bridge hit again",
     "Traffic halted after a new attack on the key supply route."),
    ("bank", "EUROPE", NAVY2,
     "EU plans EUR 45bn loan for Ukraine",
     "Repayable from Russian reparations."),
    ("sat", "SCIENCE", PURPLE,
     "Voyager 1 reaches one light-day",
     "After 48 years in space, NASA confirms the milestone today."),
    ("storm", "ASIA", TEAL,
     "Cyclone Akvan nears India's east coast",
     "Landfall expected between Machilipatnam and Puri."),
    ("scales", "POLITICS", SLATE,
     "Jeffries set to be first Black Speaker",
     "Democrats nominate Hakeem Jeffries to lead the House."),
]

BRIEF = [
    "Nvidia: acting CEO promises earlier pay raises; H-chips to China halted.",
    "Trump, Xi and Putin to hold trilateral talks in Shenzhen at APEC.",
    "Fed minutes: most officials see more rate hikes if inflation stays high.",
]


# ------------------------------------------------------------------ PNG out
def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
    return out


def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += fb[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ------------------------------------------------------------------ the page
MARGIN = 24
MAST_H = 104
HERO_H = 302
GRID_TOP = 432
TILE_W = 482
TILE_H = 110
TILE_GAP = 12
FOOT_TOP = 916
FOOT_H = 92


def masthead():
    box(0, 0, W, MAST_H, NAVY)
    box(0, MAST_H, W, 4, GOLD)
    put_text(MARGIN + 4, 14, upper_text("The World in One Page"), 3, WHITE,
             tracking=2)
    put_text(MARGIN + 4, 42, upper_text("Thursday 19 November 2026"), 6,
             WHITE)
    tag = upper_text("One day - One page")
    put_text(W - MARGIN - 4 - glyph_w(tag, 2), 22, tag, 2, GOLD)


def hero():
    hx, hy = MARGIN, MAST_H + 14
    hw, hh = W - 2 * MARGIN, HERO_H
    rrect(hx, hy, hw, hh, 12, NAVY2)
    put_text(hx + 24, hy + 16, upper_text("Top story - Culture"), 2, GOLD)
    head = upper_text("GTA VI is out at last - 13-year wait ends")
    y = hy + 42
    for ln in fit_text(head, 4, 580, 3):
        put_text(hx + 24, y, ln, 4, WHITE)
        y += 34
    body = upper_text(
        "Rockstar's Grand Theft Auto VI launches worldwide at midnight "
        "local time on PS5 and Xbox, $79.99, after two delays. Metacritic "
        "99 from 140+ reviews; 12m preorders worth $1.18bn.")
    y = hy + 148
    for ln in fit_text(body, 3, 580, 6):
        put_text(hx + 24, y, ln, 3, LIGHT)
        y += 25
    hero_scene(hx + 620, hy + 16, hw - 644, hh - 32)
    put_text(hx + 648, hy + 28, upper_text("Vice City returns"), 2, GOLD)
    put_text(hx + 648, hy + 48, upper_text("Jason and Lucia star"), 2, WHITE)


def story_grid():
    for i, (kind, tag, color, head, summ) in enumerate(TILES):
        x = MARGIN + (i % 2) * (TILE_W + TILE_GAP)
        y = GRID_TOP + (i // 2) * (TILE_H + TILE_GAP)
        edge_box(x, y, TILE_W, TILE_H, 10, 1, RULE, TILE)
        pict(kind, x + 12, y + 12, 52, color)
        tx = x + 76
        put_text(tx, y + 8, upper_text(tag), 2, color)
        hy2 = y + 26
        for ln in fit_text(upper_text(head), 3, TILE_W - 88, 2):
            put_text(tx, hy2, ln, 3, INK)
            hy2 += 24
        sy = hy2 + 4
        for ln in fit_text(upper_text(summ), 2, TILE_W - 88, 2):
            put_text(tx, sy, ln, 2, MUTED)
            sy += 15


def footer():
    fx, fy = MARGIN, FOOT_TOP
    fw, fh = W - 2 * MARGIN, FOOT_H
    rrect(fx, fy, fw, fh, 10, NAVY)
    put_text(fx + 20, fy + 12, upper_text("Also in brief"), 2, GOLD)
    date = upper_text("19 Nov 2026")
    put_text(W - MARGIN - 4 - glyph_w(date, 2), fy + 12, date, 2, GOLD)
    by = fy + 34
    for item in BRIEF:
        for ln in fit_text(upper_text("•  " + item), 2, fw - 40, 1):
            put_text(fx + 20, by, ln, 2, WHITE)
            by += 18


def main():
    fb[:] = bytes(PAPER) * (W * H)
    masthead()
    hero()
    story_grid()
    footer()
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    write_png(os.path.join(out, "entry.png"))


if __name__ == "__main__":
    main()
