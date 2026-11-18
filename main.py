#!/usr/bin/env python3
"""THE WORLD IN A DAY - Tuesday 17 November 2026.

A one-page newspaper front page, drawn entirely from code: a small
pure-Python rasterizer (framebuffer, rectangles, lines, circles,
polygons), an embedded 5x7 bitmap font, and a PNG encoder built on
zlib/struct. No network, no image assets, no third-party libraries -
the picture below is rendered pixel by pixel every time this runs,
and two runs produce byte-identical output.

Run it the way the grader runs it: python3 main.py
Reads nothing; writes $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

import os
import struct
import zlib

W = H = 1024

# Flat newspaper palette: cream paper, near-black ink, one red accent,
# warm greys for tone (water, shading).
PAPER = (246, 240, 224)
INK = (22, 22, 25)
RED = (198, 24, 44)
GREY = (208, 201, 184)
GREY_D = (141, 135, 119)
WHITE = (253, 251, 245)

# ---------------------------------------------------------------------------
# Embedded bitmap font: 5x7 glyphs, '#' is ink, '.' is empty.
# Only these characters exist; every string drawn below uses nothing else:
# uppercase A-Z, digits 0-9, space and the punctuation . , ; : ' - and the
# middle dot and dollar sign defined at the end of the table.
# ---------------------------------------------------------------------------

FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ';': (".....", ".....", ".##..", ".##..", ".....", ".##..", ".#..."),
    ':': (".....", ".....", ".##..", ".##..", ".....", ".##..", ".##.."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '·': (".....", ".....", ".....", ".##..", ".##..", ".....", "....."),
    '$': ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
}

# Fail loudly at import time if any glyph is malformed, so a typo in the
# table can never silently garble the front page.
for _ch, _glyph in FONT.items():
    assert len(_glyph) == 7, _ch
    for _row in _glyph:
        assert len(_row) == 5 and set(_row) <= set("#."), (_ch, _row)


# ---------------------------------------------------------------------------
# Rasterizer: an RGB framebuffer and the handful of primitives the page
# is built from. Everything is integer math, so renders are exact.
# ---------------------------------------------------------------------------


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.fb = bytearray(bytes(bg) * (w * h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.fb[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.fb[i:i + len(row)] = row

    def frame(self, x, y, w, h, color, t=2):
        self.rect(x, y, w, t, color)
        self.rect(x, y + h - t, w, t, color)
        self.rect(x, y, t, h, color)
        self.rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        # Bresenham, stamped with a square brush of thickness t.
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        off = t // 2
        while True:
            self.rect(x0 - off, y0 - off, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color):
        r2 = r * r
        for dy in range(-r, r + 1):
            dx = int((r2 - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def poly(self, pts, color):
        # Scanline even-odd fill of a polygon given as (x, y) vertices.
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(min(ys), max(ys) + 1):
            nodes = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    nodes.append(x0 + (y - y0) * (x1 - x0) // (y1 - y0))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.rect(nodes[i], y, nodes[i + 1] - nodes[i] + 1, 1, color)


# ---------------------------------------------------------------------------
# Text: draw with the bitmap font at an integer scale. Each glyph is
# 5x7 cells; the advance is 6 cells (one cell of tracking by default,
# adjustable for the dense small print at the bottom of the page).
# ---------------------------------------------------------------------------


def text_width(s, scale, tracking=0):
    if not s:
        return 0
    return len(s) * (6 * scale + tracking) - (scale + tracking)


def draw_text(cv, x, y, s, scale, color, tracking=0):
    adv = 6 * scale + tracking
    for ch in s:
        glyph = FONT[ch]
        for r in range(7):
            row = glyph[r]
            for c in range(5):
                if row[c] == '#':
                    cv.rect(x + c * scale, y + r * scale, scale, scale, color)
        x += adv
    return x


def draw_text_centered(cv, cx, y, s, scale, color, tracking=0):
    return draw_text(cv, cx - text_width(s, scale, tracking) // 2, y,
                     s, scale, color, tracking)


def draw_text_right(cv, xr, y, s, scale, color, tracking=0):
    return draw_text(cv, xr - text_width(s, scale, tracking), y,
                     s, scale, color, tracking)


def wrap(s, scale, max_w, tracking=0):
    """Greedy word wrap: split s into lines no wider than max_w."""
    lines = []
    cur = ""
    for word in s.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Illustrations. Each is drawn from the primitives above, in ink with the
# red accent used sparingly, inside a box whose origin is passed in.
# ---------------------------------------------------------------------------


def draw_bridge(cv, x, y):
    """The Kerch Bridge over grey water, one span down. Box: 944x112."""
    # Sun and water.
    cv.circle(x + 880, y + 20, 14, GREY)
    cv.rect(x, y + 76, 944, 36, GREY)
    for i in range(21):
        cv.rect(x + 12 + i * 45, y + 87, 18, 2, GREY_D)
        cv.rect(x + 34 + i * 45, y + 99, 18, 2, GREY_D)
    # Pylons and suspension cables.
    cv.rect(x + 196, y + 2, 12, 76, INK)
    cv.rect(x + 516, y + 2, 12, 76, INK)
    cv.line(x + 202, y + 4, x + 60, y + 47, INK, 2)
    cv.line(x + 202, y + 4, x + 344, y + 47, INK, 2)
    cv.line(x + 522, y + 4, x + 396, y + 47, INK, 2)
    cv.line(x + 522, y + 4, x + 616, y + 47, INK, 2)
    cv.line(x + 130, y + 27, x + 130, y + 47, INK, 1)
    cv.line(x + 276, y + 27, x + 276, y + 47, INK, 1)
    cv.line(x + 460, y + 27, x + 460, y + 47, INK, 1)
    # The deck: intact left and right, broken in the middle.
    cv.rect(x + 16, y + 47, 604, 7, INK)
    cv.rect(x + 766, y + 47, 162, 7, INK)
    cv.line(x + 620, y + 50, x + 656, y + 74, INK, 8)
    cv.line(x + 766, y + 50, x + 720, y + 88, INK, 8)
    # Splash where the fallen span meets the water.
    cv.line(x + 720, y + 90, x + 706, y + 75, WHITE, 3)
    cv.line(x + 720, y + 90, x + 720, y + 72, WHITE, 3)
    cv.line(x + 720, y + 90, x + 734, y + 75, WHITE, 3)
    # The strike: a red burst at the break.
    cv.circle(x + 694, y + 40, 7, RED)
    for dx, dy in ((-16, 0), (16, 0), (0, -16), (0, 16),
                   (-11, -11), (11, -11), (-11, 11), (11, 11)):
        cv.line(x + 694 + dx // 2, y + 40 + dy // 2,
                x + 694 + dx, y + 40 + dy, RED, 3)


def draw_jet(cv, x, y):
    """A passenger jet in profile, nose right. Box: 104x42."""
    cv.poly([(x + 8, y + 24), (x + 15, y + 7), (x + 25, y + 7),
             (x + 27, y + 21)], INK)                             # tail fin
    cv.poly([(x + 6, y + 24), (x + 20, y + 17), (x + 70, y + 15),
             (x + 92, y + 19), (x + 98, y + 24), (x + 92, y + 29),
             (x + 70, y + 31), (x + 20, y + 30),
             (x + 6, y + 27)], INK)                              # fuselage
    cv.poly([(x + 44, y + 29), (x + 66, y + 29), (x + 56, y + 41),
             (x + 46, y + 41)], INK)                             # wing
    for i in range(4):
        cv.rect(x + 56 + i * 8, y + 20, 3, 3, PAPER)             # windows


def draw_tanker(cv, x, y):
    """An oil tanker on a wavy sea line. Box: 104x42."""
    cv.rect(x + 10, y + 9, 18, 3, INK)                           # bridge top
    cv.rect(x + 12, y + 12, 14, 12, INK)                         # superstructure
    for cx in (44, 60, 76):
        cv.circle(x + cx, y + 21, 5, INK)                        # tank domes
    cv.rect(x + 32, y + 22, 60, 2, INK)                          # deck pipe
    cv.rect(x + 8, y + 24, 88, 3, INK)                           # deck
    cv.poly([(x + 4, y + 27), (x + 100, y + 27),
             (x + 92, y + 37), (x + 12, y + 37)], INK)           # hull
    for wx in (14, 44, 74):
        cv.rect(x + wx, y + 40, 12, 2, GREY_D)                   # waves


def draw_fighter(cv, x, y):
    """A fighter jet from above, nose right. Box: 104x42."""
    cv.poly([(x + 98, y + 21), (x + 74, y + 15), (x + 68, y + 5),
             (x + 60, y + 5), (x + 54, y + 14), (x + 36, y + 11),
             (x + 22, y + 14), (x + 26, y + 21), (x + 22, y + 28),
             (x + 36, y + 31), (x + 54, y + 28), (x + 60, y + 37),
             (x + 68, y + 37), (x + 74, y + 27)], INK)
    cv.circle(x + 76, y + 21, 3, PAPER)                          # canopy


def draw_chart(cv, x, y):
    """Rising bars and a dollar sign. Box: 104x42."""
    cv.rect(x + 8, y + 4, 2, 34, INK)
    cv.rect(x + 8, y + 38, 66, 2, INK)
    cv.rect(x + 16, y + 28, 11, 10, INK)
    cv.rect(x + 31, y + 22, 11, 16, INK)
    cv.rect(x + 46, y + 15, 11, 23, INK)
    cv.rect(x + 61, y + 8, 11, 30, RED)
    draw_text(cv, x + 80, y + 7, "$", 4, RED)


# ---------------------------------------------------------------------------
# The day's news, as reported on Tuesday 17 November 2026. All display
# strings are uppercase because the bitmap font is uppercase-only.
# ---------------------------------------------------------------------------

DATE_LINE = "TUESDAY 17 NOVEMBER 2026"

LEAD_HEADLINE = "UKRAINE STRIKES CRIMEA BRIDGE"
LEAD_SUMMARY = (
    "A SECTION OF THE KERCH BRIDGE COLLAPSES AFTER A UKRAINIAN STRIKE "
    "ZELENSKYY HAILED AS UNPRECEDENTED; RUSSIA HITS KYIV'S BRIDGES IN REPLY."
)

PANELS = [
    (draw_jet, "ASIA · DIPLOMACY",
     ["TRUMP IN MANILA"],
     "IN MANILA FOR ASEAN SUMMIT; SIGNS JOINT TRADE STATEMENT WITH "
     "THAILAND; XI AND PUTIN TALKS AHEAD."),
    (draw_tanker, "MIDDLE EAST · ENERGY",
     ["TANKERS HIT IN", "HORMUZ STRAIT"],
     "IRAN'S GUARDS SAY TWO TANKERS HIT MINES IN THE STRAIT; THIRD US "
     "CARRIER ARRIVES."),
    (draw_fighter, "ASIA · SECURITY",
     ["JAPAN SCRAMBLES", "JETS"],
     "STRONG PROTEST LODGED AFTER TWO SUSPECTED RUSSIAN AIRCRAFT "
     "VIOLATED JAPAN'S AIRSPACE."),
    (draw_chart, "BUSINESS · US",
     ["BUFFETT GIVES", "$5.47 BILLION"],
     "WARREN BUFFETT DONATES $5.47 BILLION IN BERKSHIRE HATHAWAY "
     "SHARES TO FAMILY FOUNDATIONS."),
]

GTA_HEADLINE = "GTA VI LEAK HACKER PLEADS GUILTY"
GTA_SUMMARY = ("THE HACKER BEHIND THE 2022 LEAKS PLEADS GUILTY, "
               "DAYS BEFORE THE GAME LAUNCHES.")
TICKER = (
    "ALSO TUESDAY: FIVE EUROPEAN NATIONS PLAN RWANDA RETURN HUB FOR "
    "REJECTED ASYLUM SEEKERS · ULA VULCAN FAILURE DESTROYS 40 AMAZON "
    "SATELLITES · JPMORGAN BLAMES SOFTWARE BUG FOR MONDAY'S BANKING "
    "OUTAGE · UK SANCTIONS ISRAELI SETTLEMENT FIRMS"
)


def draw_panel(cv, px, py, icon, kicker, headline, summary):
    cv.frame(px, py, 482, 236, INK, 2)
    icon(cv, px + 14, py + 10)
    draw_text(cv, px + 132, py + 24, kicker, 2, RED)
    cv.rect(px + 14, py + 56, 454, 2, INK)
    y = py + 64
    for line in headline:
        draw_text(cv, px + 14, y, line, 5, INK)
        y += 36
    lines = wrap(summary, 3, 454)
    sy = py + 230 - ((len(lines) - 1) * 22 + 21)
    for line in lines:
        draw_text(cv, px + 14, sy, line, 3, INK)
        sy += 22


def build_page():
    cv = Canvas(W, H, PAPER)

    # Masthead: the title in a black band, the date loud beneath it.
    cv.rect(0, 0, W, 84, INK)
    draw_text_centered(cv, 512, 14, "THE WORLD IN A DAY", 8, PAPER)
    cv.rect(0, 84, W, 4, RED)
    draw_text_centered(cv, 512, 91, DATE_LINE, 4, INK)
    cv.rect(168, 99, 10, 10, RED)
    cv.rect(846, 99, 10, 10, RED)
    cv.rect(0, 122, W, 3, INK)

    # Lead story: the bridge, full width.
    cv.frame(24, 135, 976, 248, INK, 2)
    draw_bridge(cv, 40, 145)
    cv.rect(40, 145, 132, 24, RED)
    draw_text(cv, 47, 150, "LEAD STORY", 2, PAPER)
    draw_text(cv, 40, 267, LEAD_HEADLINE, 5, INK)
    y = 310
    for line in wrap(LEAD_SUMMARY, 3, 944):
        draw_text(cv, 40, y, line, 3, INK)
        y += 23

    # Four more stories in a 2x2 grid.
    spots = [(24, 395), (518, 395), (24, 643), (518, 643)]
    for (px, py), (icon, kicker, headline, summary) in zip(spots, PANELS):
        draw_panel(cv, px, py, icon, kicker, headline, summary)

    # Bottom strip: the GTA VI hacker, then the day's smaller stories.
    cv.rect(0, 891, W, 34, RED)
    draw_text(cv, 40, 894, GTA_HEADLINE, 4, PAPER)
    draw_text_right(cv, 984, 901, "17 NOVEMBER 2026", 2, PAPER, tracking=-1)
    draw_text(cv, 40, 933, GTA_SUMMARY, 2, INK, tracking=-1)
    y = 955
    for line in wrap(TICKER, 2, 944, tracking=-1):
        draw_text(cv, 40, y, line, 2, INK, tracking=-1)
        y += 15

    # Footer: the date once more, in a black band.
    cv.rect(0, 1006, W, 18, INK)
    draw_text_centered(cv, 512, 1008, "TUESDAY · 17 NOVEMBER · 2026",
                       2, PAPER)
    return cv


# ---------------------------------------------------------------------------
# PNG encoder: filter-0 scanlines, one IDAT, standard chunks.
# ---------------------------------------------------------------------------


def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def save_png(cv, path):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)
        raw += cv.fb[y * stride:(y + 1) * stride]
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    save_png(build_page(), os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
