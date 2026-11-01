#!/usr/bin/env python3
"""Runs bench/vctime.bas with start delays 0-3 and prints, for every tick of TIME, the
VCOUNT of the last sample before it and the first after it; then the window all the ticks
fall in, and whether any single VCOUNT fits them all (on atari800 5.0 none does: the tick
moves by a few lines inside the vertical blank).

  python3 bench/vctime.py       (Linux, atari800: see tools/README.md)
"""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import emu

src = open(os.path.join(HERE, 'vctime.bas'), encoding='latin1').read()
fits = set(range(131))
span = set()
for delay in range(4):
    xex = emu.compile_bas(src.replace('D = 0', f'D = {delay}', 1), f'vctime{delay}')
    with emu.Session(xex, {}) as s:
        time.sleep(2)
        s.stop()
        if s.mem(0x6400, 1) != [1]:
            raise SystemExit('the program did not finish')
        d = []
        for a in range(0x6000, 0x6000 + 400, 16):
            d += s.mem(a, 16)
    pairs = [(d[i], d[i + 1]) for i in range(0, 400, 2)]
    seen = []
    for (t0, v0), (t1, v1) in zip(pairs, pairs[1:]):
        if t1 != t0:
            seen.append(f'{v0}->{v1}')
            # the tick happened at a VCOUNT in (v0, v1], counting across the wrap 130 -> 0
            here = {v % 131 for v in range(v0 + 1, v1 + 1 + (131 if v1 <= v0 else 0))}
            fits &= here
            span |= here
    print(f'delay {delay}: ticks between VCOUNT', ' '.join(seen))
lo = min(v for v in span if v > 64)
hi = max(v for v in span if v < 64) if any(v < 64 for v in span) else max(span)
print(f'every tick is inside VCOUNT {lo}..{hi} (across the wrap)')
print('a single VCOUNT that fits every tick:', sorted(fits) or 'none')
