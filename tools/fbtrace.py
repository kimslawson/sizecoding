#!/usr/bin/env python3
"""fbtrace: per-frame trace of a FastBasic game's variables, from the real emulator.

  fbtrace.py PROG.bas --vars X,Y,U,V --keys "xdotool ..." --seconds 4 [--frames 64] [--sub OLD=>NEW]

Inserts, at the end of the main loop (before its LOOP at column 0), statements that DPOKE each listed variable
into a ring buffer at $9000 (256 frames x up to 16 words; BASIC must be off), runs the program with the key
script, stops it in atari800's monitor after --seconds, writes the buffer to a file with
the monitor's WRITE command, and prints one line per frame, oldest first.
The trace costs a few units per frame, so don't read lost-frame numbers from it.
"""
import argparse, os, re, subprocess, sys, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu

BUF, FR = 0x9000, 256


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('prog'); ap.add_argument('--vars', required=True)
    ap.add_argument('--keys', default=''); ap.add_argument('--seconds', type=float, default=4)
    ap.add_argument('--frames', type=int, default=64)
    ap.add_argument('--sub', action='append', default=[], help='OLD=>NEW text replacement (must match)')
    a = ap.parse_args()
    names = a.vars.split(',')
    n = len(names)
    assert n <= 16
    src = open(a.prog, 'rb').read().decode('latin1')
    for r in a.sub:
        o, n2 = r.split('=>')
        assert src.count(o) >= 1, 'no match: ' + o
        src = src.replace(o, n2)
    src = src.split('\n')
    idx = [i for i, l in enumerate(src) if re.match(r'LOOP\s*$', l)]
    assert len(idx) == 1, 'need exactly one LOOP line at column 0 (the main loop)'
    i = idx[0] - 1
    ins = [f'  INC Z9N : Z9T = $9000 + (Z9N & 255) * 32']
    ins += [f'  DPOKE Z9T + {2*k}, {v}' for k, v in enumerate(names)]
    src = src[:i + 1] + ins + src[i + 1:]
    xex, labels = emu.compile_with_labels('\n'.join(src), 'trace')
    with emu.Session(xex, labels, wait=2.5) as s:
        k = s.keys(a.keys) if a.keys else None
        time.sleep(a.seconds)
        s.stop()
        cnt = s.var('Z9N')
        out = tempfile.mktemp()
        s._send([f'WRITE {BUF:04X} {BUF + FR*32 - 1:04X} {out}'])
        time.sleep(0.3)
        if k:
            k.kill()
    data = open(out, 'rb').read()
    print('frame ' + ' '.join(f'{v:>7}' for v in names))
    for f in range(max(1, cnt - min(a.frames, FR) + 1), cnt + 1):
        o = (f & 255) * 32
        vals = []
        for j in range(n):
            w = data[o + 2*j] + 256 * data[o + 2*j + 1]
            vals.append(w - 65536 if w >= 32768 else w)
        print(f'{f:5d} ' + ' '.join(f'{v:7d}' for v in vals))


if __name__ == '__main__':
    main()
