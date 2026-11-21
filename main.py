"""THE WORLD IN ONE DAY - Friday 20 November 2026.

A one-page broadsheet of the day's world news, drawn entirely by
program: masthead, a pictured lead (the Shenzhen trilateral summit),
the World Court's Myanmar verdict, a dotted world map with the day's
flashpoints marked, and a briefs grid. Pure Python standard library -
no Pillow, no network, no randomness: two runs produce byte-identical
files. The page is written to /output/entry.png (a copy beside this
file is attempted too, and never allowed to fail the run).
"""

import struct
import zlib
from pathlib import Path

W = 1024
H = 1024

PAPER = (247, 242, 231)
INK = (20, 22, 26)
RED = (179, 35, 27)
NAVY = (29, 53, 87)
NAVY_DARK = (16, 30, 52)
GOLD = (201, 162, 39)
GREY = (107, 111, 118)
STONE = (232, 224, 205)
WHITE = (255, 255, 255)
SKIN = (222, 184, 150)


class Canvas:
    """A flat RGB pixel buffer with clipped drawing primitives."""

    def __init__(self, w, h, colour):
        self.w = w
        self.h = h
        self.px = bytearray(bytes(colour) * (w * h))

    def set_px(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = colour[0]
            self.px[i + 1] = colour[1]
            self.px[i + 2] = colour[2]

    def rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def disc(self, cx, cy, r, colour):
        r2 = r * r
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            for xx in range(cx - r, cx + r + 1):
                dx = xx - cx
                if dx * dx + dy * dy <= r2:
                    self.set_px(xx, yy, colour)

    def ring(self, cx, cy, r, colour, thick=2):
        r2o = r * r
        r2i = (r - thick) * (r - thick)
        for yy in range(cy - r, cy + r + 1):
            dy = yy - cy
            for xx in range(cx - r, cx + r + 1):
                dx = xx - cx
                d2 = dx * dx + dy * dy
                if r2i < d2 <= r2o:
                    self.set_px(xx, yy, colour)

    def line(self, x0, y0, x1, y1, colour, thick=2):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        r = max(1, thick // 2)
        for i in range(steps + 1):
            x = x0 + (x1 - x0) * i // steps
            y = y0 + (y1 - y0) * i // steps
            self.disc(x, y, r, colour)

    def poly(self, pts, colour):
        ys = [p[1] for p in pts]
        y_lo = max(0, min(ys))
        y_hi = min(self.h - 1, max(ys))
        n = len(pts)
        for yy in range(y_lo, y_hi + 1):
            nodes = []
            for i in range(n):
                xa, ya = pts[i]
                xb, yb = pts[(i + 1) % n]
                if ya == yb:
                    continue
                if (ya <= yy < yb) or (yb <= yy < ya):
                    nodes.append(xa + (yy - ya) * (xb - xa) // (yb - ya))
            nodes.sort()
            for i in range(0, len(nodes) - 1, 2):
                self.rect(nodes[i], yy, nodes[i + 1] - nodes[i] + 1, 1, colour)


# A compact 5x7 pixel font. Each glyph is 7 rows of 5 bits.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17), "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14), "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31), "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15), "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),      "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17), "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17), "N": (17, 17, 25, 21, 19, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14), "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13), "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),   "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14), "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10), "X": (17, 10, 4, 4, 4, 10, 17),
    "Y": (17, 10, 4, 4, 4, 4, 4),      "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14), "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 2, 4, 8, 31),     "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),     "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),   "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14), "9": (14, 17, 17, 15, 1, 2, 12),
    ".": (0, 0, 0, 0, 0, 12, 12),      ",": (0, 0, 0, 0, 12, 4, 8),
    "'": (4, 4, 8, 0, 0, 0, 0),        "-": (0, 0, 0, 31, 0, 0, 0),
    ":": (0, 12, 12, 0, 12, 12, 0),    ";": (0, 12, 12, 0, 12, 4, 8),
    "!": (4, 4, 4, 4, 4, 0, 4),        "?": (14, 17, 1, 2, 4, 0, 4),
    "$": (4, 15, 20, 14, 5, 30, 4),    "%": (24, 25, 2, 4, 8, 19, 3),
    "+": (0, 4, 4, 31, 4, 4, 0),       "/": (1, 1, 2, 4, 8, 16, 16),
    "(": (2, 4, 8, 8, 8, 4, 2),        ")": (8, 4, 2, 2, 2, 4, 8),
    "&": (12, 18, 20, 8, 21, 18, 13),  '"': (10, 10, 10, 0, 0, 0, 0),
    "£": (6, 8, 8, 30, 8, 16, 31),
    "·": (0, 0, 0, 12, 12, 0, 0),      " ": (0, 0, 0, 0, 0, 0, 0),
}


def text_width(s, scale, tracking=1):
    if not s:
        return 0
    return len(s) * (5 + tracking) * scale - tracking * scale


def draw_text(cv, x, y, s, scale, colour, align="left", tracking=1):
    s = s.upper().replace("–", "-").replace("—", "-")
    w = text_width(s, scale, tracking)
    if align == "center":
        x = x - w // 2
    elif align == "right":
        x = x - w
    adv = (5 + tracking) * scale
    for ch in s:
        glyph = FONT.get(ch, FONT[" "])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits & (1 << (4 - col)):
                    cv.rect(x + col * scale, y + row * scale, scale, scale, colour)
        x += adv
    return w


def wrap_text(s, scale, max_width, tracking=1):
    words = s.upper().split()
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, tracking) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, s, scale, colour, max_width, step, align="left"):
    for ln in wrap_text(s, scale, max_width):
        draw_text(cv, x, y, ln, scale, colour, align=align)
        y += step
    return y


# A dotted world map on a 26 x 104 grid, built from land spans
# (row: [(first column, last column), ...]). Stylised - the markers
# and labels carry the geography that matters.
MAP_SPANS = {
    2: [(12, 24), (60, 98)],
    3: [(3, 30), (36, 41), (52, 100)],
    4: [(8, 31), (37, 40), (47, 47), (50, 100)],
    5: [(9, 29), (47, 99)],
    6: [(10, 27), (47, 90), (91, 93)],
    7: [(11, 26), (47, 72), (74, 88), (90, 92)],
    8: [(12, 24), (47, 52), (57, 71), (75, 85)],
    9: [(13, 20), (47, 64), (67, 70), (76, 81)],
    10: [(15, 19), (46, 60), (67, 69), (76, 80)],
    11: [(23, 27), (47, 61), (77, 79)],
    12: [(24, 30), (48, 61)],
    13: [(25, 32), (49, 60)],
    14: [(26, 33), (50, 59), (78, 78), (81, 81), (84, 84)],
    15: [(26, 32), (51, 58), (76, 77), (80, 82), (85, 88)],
    16: [(27, 31), (52, 57), (79, 80), (83, 86)],
    17: [(27, 30), (52, 56)],
    18: [(27, 30), (53, 56), (84, 88)],
    19: [(28, 30), (53, 55), (82, 94)],
    20: [(28, 29), (83, 93)],
    21: [(28, 29), (85, 91)],
    22: [(28, 28), (100, 101)],
    23: [(100, 100)],
}


def _build_map_rows():
    rows = []
    for r in range(26):
        cells = ["."] * 104
        for a, b in MAP_SPANS.get(r, []):
            for c in range(a, b + 1):
                cells[c] = "#"
        rows.append("".join(cells))
    return rows


MAP_ROWS = _build_map_rows()

# (column, row, label or None, side) - the day's flashpoints; side is
# "r" when the label sits right of the marker, "l" when it ends left.
MARKERS = [
    (80, 10, "SHENZHEN", "r"), (57, 5, "KYIV", "l"), (49, 5, "THE HAGUE", "r"),
    (56, 8, None, "r"), (61, 9, "RIYADH", "r"), (83, 10, None, "r"),
    (78, 16, "JAKARTA", "r"), (60, 7, None, "r"), (47, 8, None, "r"),
    (52, 5, None, "r"), (90, 7, "TOKYO", "r"), (55, 7, None, "r"),
    (22, 8, "WASHINGTON", "r"), (99, 19, None, "r"), (48, 5, None, "r"),
]

MAPLAND = (104, 114, 128)


def draw_map(cv, x, y, pitch_x, pitch_y):
    for r, row in enumerate(MAP_ROWS):
        row = row.ljust(104)[:104]
        for c, ch in enumerate(row):
            if ch == "#":
                mx = x + int(c * pitch_x)
                my = y + int(r * pitch_y)
                cv.rect(mx - 2, my - 2, 5, 4, MAPLAND)
    for c, r, label, side in MARKERS:
        mx = x + int(c * pitch_x)
        my = y + int(r * pitch_y)
        cv.disc(mx, my, 5, WHITE)
        cv.disc(mx, my, 4, RED)
        if label and side == "r":
            draw_text(cv, mx + 8, my - 3, label, 1, INK)
        elif label:
            draw_text(cv, mx - 8, my - 3, label, 1, INK, align="right")


def flag_us(cv, x, y, w, h):
    stripe = h // 7
    for i in range(7):
        cv.rect(x, y + i * stripe, w, stripe + 1, RED if i % 2 == 0 else WHITE)
    cw = w * 2 // 5
    ch = stripe * 4
    cv.rect(x, y, cw, ch, NAVY)
    for r in range(4):
        for c in range(5):
            cv.disc(x + 5 + c * (cw - 8) // 4, y + 5 + r * (ch - 8) // 3, 1, WHITE)


def flag_cn(cv, x, y, w, h):
    cv.rect(x, y, w, h, RED)
    cv.disc(x + 11, y + 11, 5, GOLD)
    for dx, dy in ((20, 5), (23, 11), (20, 17)):
        cv.disc(x + dx, y + dy, 2, GOLD)


def flag_ru(cv, x, y, w, h):
    third = h // 3
    cv.rect(x, y, w, third + 1, WHITE)
    cv.rect(x, y + third, w, third + 1, NAVY)
    cv.rect(x, y + 2 * third, w, h - 2 * third, RED)


def draw_summit(cv, x, y, w, h):
    """Three leaders at one table, three flags behind them."""
    cv.rect(x, y, w, h, NAVY_DARK)
    cv.rect(x, y, w, h * 3 // 5, NAVY)
    centres = [x + w // 4, x + w // 2, x + 3 * w // 4]
    flag_fns = [flag_us, flag_cn, flag_ru]
    for cx, fn in zip(centres, flag_fns):
        cv.line(cx, y + 6, cx, y + h - 30, GOLD, thick=3)
        fn(cv, cx - 34, y + 8, 68, 40)
    # the table
    cv.poly([(x + 60, y + h), (x + 104, y + h - 26),
             (x + w - 104, y + h - 26), (x + w - 60, y + h)], (74, 52, 36))
    for cx in centres:
        cv.disc(cx, y + h - 38, 11, SKIN)
        cv.poly([(cx - 25, y + h), (cx - 15, y + h - 27),
                 (cx + 15, y + h - 27), (cx + 25, y + h)], INK)
        cv.poly([(cx - 5, y + h), (cx, y + h - 24), (cx + 5, y + h)], WHITE)
        cv.rect(cx - 13, y + h - 16, 26, 5, GOLD)


def draw_court(cv, x, y, w, h):
    """A columned courthouse, a gavel, and the 9-6 split."""
    cv.rect(x, y, w, h, STONE)
    cx = x + w // 2 - 30
    cv.poly([(cx - 82, y + 34), (cx + 82, y + 34), (cx, y + 10)], NAVY)
    cv.rect(cx - 82, y + 34, 164, 6, INK)
    for i in range(5):
        colx = cx - 68 + i * 34
        cv.rect(colx, y + 44, 13, h - 66, WHITE)
        cv.rect(colx, y + 44, 13, 3, GREY)
    cv.rect(cx - 88, y + h - 20, 176, 5, GREY)
    cv.rect(cx - 96, y + h - 13, 192, 5, GREY)
    draw_text(cv, x + 14, y + 10, "9-6", 4, RED)
    # gavel, struck, at lower right
    hx, hy = x + w - 46, y + h - 52
    cv.line(hx, hy, x + w - 92, y + h - 12, (74, 52, 36), thick=6)
    cv.line(hx - 13, hy - 11, hx + 13, hy + 11, INK, thick=13)
    cv.rect(x + w - 104, y + h - 10, 46, 6, INK)


BRIEFS = [
    ("KYIV HIT OVERNIGHT",
     "FOUR BALLISTIC MISSILES HIT THE CAPITAL; BRIDGES STRUCK, FIRES BURN."),
    ("AN AI GIANT LISTS",
     "PRICED AT $83, IT RAISES $81BN, CLOSES +17% AND BRIEFLY TOUCHES $2TN."),
    ("COP31: FOSSIL FUELS OUT",
     "ANTALYA DRAFT DROPS EVERY FOSSIL-FUEL LINE AND THE $120BN TARGET."),
    ("RIYADH SKYLINE SCARRED",
     "HOUTHI STRIKES HIT FOUR SAUDI TARGETS; TALLEST TOWER DAMAGED."),
    ("TAIWAN ON EDGE",
     "2,700 CHINA-LINKED ACCOUNTS FLAGGED; STOCKS PLUNGE 2,200 POINTS."),
    ("PRABOWO MEETS XI",
     "TRADE AND THE SOUTH CHINA SEA; $86.8BN OF APEC BUSINESS IN PLAY."),
]

DECK = (58, 61, 66)
M = 36
RIGHT = W - M


def compose():
    cv = Canvas(W, H, PAPER)

    # folio, masthead, date band
    draw_text(cv, M, 24, "FRIDAY EDITION · NO. 20", 2, GREY)
    draw_text(cv, RIGHT, 24, "ONE PAGE · THE WHOLE DAY", 2, GREY, align="right")
    cv.rect(M, 46, RIGHT - M, 3, INK)
    cv.rect(M, 52, RIGHT - M, 1, INK)
    draw_text(cv, W // 2, 62, "THE WORLD IN ONE DAY", 7, INK, align="center")
    cv.rect(M, 120, RIGHT - M, 2, GOLD)
    cv.rect(M, 122, RIGHT - M, 48, INK)
    draw_text(cv, W // 2, 131, "FRIDAY · 20 NOVEMBER 2026", 5, WHITE, align="center")
    cv.rect(M, 170, RIGHT - M, 2, GOLD)
    draw_text(cv, W // 2, 180,
              "RIVALS SIGN A PEACE PACT · A COURT NAMES A GENOCIDE",
              3, INK, align="center")
    draw_text(cv, W // 2, 206,
              "DRONES FOR UKRAINE · GEORGIA BLAST · SPAIN STRIKES · TOKYO MARCHES",
              2, GREY, align="center")

    # lead (left) and second story (right)
    cv.line(632, 236, 632, 604, GREY, thick=1)
    draw_text(cv, M, 232, "SHENZHEN · APEC SUMMIT", 3, RED)
    ly = 260
    for ln in ("TRUMP, XI AND PUTIN", "SIGN FIRST-EVER", "PEACE DECLARATION"):
        draw_text(cv, M, ly, ln, 5, INK)
        ly += 40
    draw_summit(cv, M, 380, 584, 100)
    draw_wrapped(cv, M, 488,
                 "FOUR POINTS: REFORM THE UN, SECURE OIL SUPPLY, CURB THE "
                 "WORLD COURT - AND NEVER FIGHT A NUCLEAR WAR. UKRAINE FIRST.",
                 3, INK, 584, 24)

    draw_text(cv, 644, 232, "THE HAGUE · ICJ", 3, RED)
    ly = 260
    for ln in ("MYANMAR", "GUILTY OF", "GENOCIDE"):
        draw_text(cv, 644, ly, ln, 5, INK)
        ly += 40
    draw_court(cv, 644, 380, 344, 100)
    draw_wrapped(cv, 644, 488,
                 "JUDGES RULED 9-6 THAT MYANMAR'S ARMY COMMITTED GENOCIDE "
                 "AGAINST THE ROHINGYA IN RAKHINE IN 2017, KILLING SOME "
                 "10,000. REPARATIONS AND A SAFE RETURN ARE ORDERED.",
                 2, INK, 344, 17)

    # the day on the map
    cv.rect(M, 618, RIGHT - M, 2, INK)
    draw_text(cv, M, 628, "THE DAY ON THE MAP", 3, INK)
    draw_text(cv, RIGHT, 632, "FIFTEEN FLASHPOINTS, ONE FRIDAY", 2, GREY,
              align="right")
    draw_map(cv, M, 652, 9.1, 4.8)
    draw_text(cv, W // 2, 778,
              "ALSO MARKED: ANTALYA · TBILISI · MADRID · PRAGUE · ISTANBUL · NEW CALEDONIA",
              2, GREY, align="center")

    # briefs
    cv.rect(M, 802, RIGHT - M, 2, INK)
    draw_text(cv, M, 812, "IN BRIEF - THE REST OF THE DAY", 3, RED)
    cols = [M, 360, 684]
    for i, (head, deck) in enumerate(BRIEFS):
        cx = cols[i % 3]
        cy = 840 + (i // 3) * 72
        draw_text(cv, cx, cy, head, 2, INK)
        draw_wrapped(cv, cx, cy + 18, deck, 2, DECK, 304, 15)

    # footer
    cv.rect(M, 988, RIGHT - M, 3, INK)
    draw_text(cv, M, 996, "SOURCES: REUTERS · AP · UN NEWS · LE MONDE", 2, INK)
    draw_text(cv, RIGHT, 996, "FRIDAY · 20 NOVEMBER 2026", 2, INK, align="right")
    return cv


def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for yy in range(cv.h):
        raw.append(0)
        raw += cv.px[yy * stride:(yy + 1) * stride]

    def chunk(tag, payload):
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + chunk(b"IEND", b""))


def main():
    data = encode_png(compose())
    out = Path("/output/entry.png")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
    except OSError:
        pass
    try:
        Path(__file__).with_name("entry.png").write_bytes(data)
    except OSError:
        pass
    print("entry.png:", len(data), "bytes")


if __name__ == "__main__":
    main()
