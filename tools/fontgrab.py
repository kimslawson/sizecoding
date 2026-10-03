#!/usr/bin/env python3
"""fontgrab: capture the emulator's character set as a standard 1024-byte Atari .fnt file.

Runs a tiny FastBasic program that pokes all 128 internal character codes onto a GRAPHICS 0
screen (bright on black), screenshots it and turns each 8x8 cell back into 8 bytes. The result
is the font of atari800's built-in AltirraOS, in internal-code order (code 0 = space), which is
what the screen readers and proof.py use.

  fontgrab.py [OUT.fnt]      default: tools/.cache/altirraos.fnt
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu

PROG = """GRAPHICS 0
POKE 709,15:POKE 710,0:POKE 712,0
S=DPEEK(88)
FOR I=0 TO 127:POKE S+I,I:NEXT I
DO:LOOP
"""


def grab(out):
    xex = emu.compile_bas(PROG, 'fontgrab')
    png, _ = emu.run(xex, wait=2.0)
    c = emu.cells(png).reshape(24 * 40, 8, 8)[:128]
    data = np.packbits(c.reshape(128, 64).astype(np.uint8), axis=1).tobytes()
    assert len(data) == 1024
    if not any(data[16 * 8:17 * 8]):       # code 16 is '0': it can't be blank
        raise SystemExit('font capture failed (blank glyphs); is the screen where emu.py expects?')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, 'wb').write(data)
    return out


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(emu.CACHE, 'altirraos.fnt')
    print('wrote', grab(out))
