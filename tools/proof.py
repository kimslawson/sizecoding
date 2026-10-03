#!/usr/bin/env python3
"""proof: render a packed listing as an image, every byte as its ATASCII glyph.

The contest asks for "a program listing that proves the program does not have more characters
than allowed". A text file can't show the control characters and inverse video inside a
string literal; this draws each byte the way an Atari shows it: one glyph per character, so
column 120 really is the 120th character.

  proof.py LISTING [-o proof.png] [--width 120] [--scale 2] [--font FONT.fnt]
                   [--style paper|atari] [--no-ruler] [--wrap N]

By default each listing line is one image row, with a column ruler on top, the line number on
the left and the line's length on the right. --wrap N wraps lines at N columns (like the 40-
column screen would), for a narrower image.

The font is any standard 1024-byte Atari font file (internal code order). Without --font it
uses the one fontgrab.py captures from the emulator (AltirraOS), grabbing it if needed.
"""
import argparse, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fblib

STYLES = {  # background, ink, ruler/margin ink, over-limit ink
    'paper': ((255, 255, 255), (0, 0, 0), (150, 150, 150), (200, 0, 0)),
    'atari': ((0x1C, 0x5E, 0xB5), (0xC8, 0xE4, 0xFF), (0x6E, 0x9E, 0xE0), (255, 120, 120)),
}


def atascii_to_internal(c):
    c &= 0x7F
    return c + 64 if c < 32 else (c - 32 if c < 96 else c)


def load_font(path):
    if path is None:
        import emu
        path = os.path.join(emu.CACHE, 'altirraos.fnt')
        if not os.path.exists(path):
            import fontgrab
            fontgrab.grab(path)
    data = open(path, 'rb').read()
    if len(data) != 1024:
        raise SystemExit(f'{path}: an Atari font is 1024 bytes')
    return np.unpackbits(np.frombuffer(data, np.uint8)).reshape(128, 8, 8).astype(bool)


def glyph(font, byte):
    g = font[atascii_to_internal(byte)]
    return ~g if byte & 0x80 else g


def text_cells(font, s):
    """Glyphs for plain ASCII text (ruler digits, line numbers)."""
    return [glyph(font, ord(ch)) for ch in s]


def render(lines, font, width, style, ruler=True, wrap=None):
    bg, ink, dim, over = STYLES[style]
    rows = []          # each row: list of (glyph, color)
    gutter, right = 3, 5
    cols = wrap or max(width, max((len(l) for l in lines), default=0))

    def margin(text, n):
        return [(g, dim) for g in text_cells(font, text.rjust(n))]
    if ruler:
        tens = ''.join(str((c // 10) % 10) if c % 10 == 0 else ' ' for c in range(1, cols + 1))
        ones = ''.join(str(c % 10) for c in range(1, cols + 1))
        for t in (tens, ones):
            rows.append(margin('', gutter) + [(g, dim) for g in text_cells(font, t)] + margin('', right))
        rows.append(None)  # thin gap
    for i, l in enumerate(lines):
        chunks = [l[k:k + wrap] for k in range(0, max(len(l), 1), wrap)] if wrap else [l]
        for j, ch in enumerate(chunks):
            r = margin(str(i + 1) if j == 0 else '', gutter - 1) + margin('', 1)
            for k, b in enumerate(ch):
                col = (wrap * j if wrap else 0) + k
                r.append((glyph(font, b), over if col >= width else ink))
            r += [(glyph(font, 32), ink)] * (cols - len(ch))
            r += margin(str(len(l)) if j == len(chunks) - 1 else '', right)
            rows.append(r)
    wcells = gutter + cols + right
    h = sum(8 if r else 3 for r in rows)
    img = np.zeros((h, wcells * 8, 3), np.uint8); img[:] = bg
    y = 0
    for r in rows:
        if r is None:
            y += 3; continue
        for x, (g, color) in enumerate(r):
            cell = img[y:y + 8, x * 8:x * 8 + 8]
            cell[g] = color
        y += 8
    # a thin line just right of the last allowed column
    if not wrap:
        x = (gutter + width) * 8
        top = (2 * 8 + 3) if ruler else 0
        img[top:, x] = over
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('listing'); ap.add_argument('-o', '--output', default='proof.png')
    ap.add_argument('--width', type=int, default=120); ap.add_argument('--scale', type=int, default=2)
    ap.add_argument('--font'); ap.add_argument('--style', choices=STYLES, default='paper')
    ap.add_argument('--no-ruler', action='store_true'); ap.add_argument('--wrap', type=int)
    a = ap.parse_args()
    lines = fblib.read_lines(a.listing)
    img = render(lines, load_font(a.font), a.width, a.style, not a.no_ruler, a.wrap)
    im = Image.fromarray(img)
    if a.scale > 1:
        im = im.resize((im.width * a.scale, im.height * a.scale), Image.NEAREST)
    im.save(a.output)
    m = fblib.measure(lines)
    print(f"{a.output}: {m['lines']} lines, longest {m['max']}, {m['chars']} chars, {im.width}x{im.height}")


if __name__ == '__main__':
    main()
