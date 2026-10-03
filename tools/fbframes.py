#!/usr/bin/env python3
"""fbframes: does every pass of the main loop fit in one frame? Count lost frames.

A game loop that ends in PAUSE should run once per frame. When a pass runs past the vertical
blank, PAUSE waits for the next one: the frame is lost, and TIME moves 2 during that pass
instead of 1. This tool counts those frames in a copy of your program:

  * the only change to the program is `INC Z9_N` just before the loop's PAUSE (0.7 units,
    about half a percent of a frame), so the measurement barely disturbs what it measures;
  * the emulator's monitor stops the program exactly at PAUSE, twice, --seconds apart, and
    reads TIME and Z9_N from memory. Frames lost = jiffies elapsed - passes made.

Your program must have exactly one PAUSE statement (the one in the main loop).

  fbframes.py PROG.bas [--seconds 10] [--keys "xdotool script"] [--runs 3] [--pal]

--keys is a bash script started when the measurement starts, with xdotool and atari800's keys
(see emu.py). Examples:
  "xdotool keydown KP_Up; sleep 11; xdotool keyup KP_Up"
  "for i in $(seq 20); do xdotool keydown Control_R; sleep 0.3; xdotool keyup Control_R; sleep 0.2; done"
--before is a key script that runs (to completion) before the measurement starts: a START
press, say.
"""
import argparse, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu, fblib


def instrument(src_bytes):
    exp = fblib.expand(src_bytes)
    if exp is None:
        raise SystemExit('the program does not compile')
    lines = [l.decode('latin1') for l in exp]
    pauses = [i for i, l in enumerate(lines) if re.match(r'PAUSE\b', l)]
    if len(pauses) != 1:
        raise SystemExit(f'need exactly one PAUSE statement, found {len(pauses)}')
    p = pauses[0]
    return '\n'.join(lines[:p] + ['INC Z9_N'] + lines[p:]) + '\n'


def measure(xex, labels, seconds, keys, before, pal, wait):
    with emu.Session(xex, labels, pal=pal, wait=wait) as s:
        if before:
            s.keys(before, background=False)
        s.sync('EXE_PAUSE')
        n1, t1 = s.var('Z9_N'), s.time()
        s.resume()
        k = s.keys(keys) if keys else None
        time.sleep(seconds)
        s.sync('EXE_PAUSE')
        n2, t2 = s.var('Z9_N'), s.time()
        if k:
            k.kill()
        e, n = (t2 - t1) & 0xFFFF, (n2 - n1) & 0xFFFF
        return e, n, e - n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prog'); ap.add_argument('--seconds', type=float, default=10)
    ap.add_argument('--keys', default=''); ap.add_argument('--before', default='')
    ap.add_argument('--runs', type=int, default=1)
    ap.add_argument('--pal', action='store_true'); ap.add_argument('--wait', type=float, default=2.5)
    ap.add_argument('--source', action='store_true', help='print the instrumented program')
    a = ap.parse_args()
    src = instrument(open(a.prog, 'rb').read())
    if a.source:
        print(src)
    xex, labels = emu.compile_with_labels(src, 'frames')
    lost = []
    for r in range(a.runs):
        e, n, l = measure(xex, labels, a.seconds, a.keys, a.before, a.pal, a.wait)
        lost.append(l)
        print(f'run {r + 1}: {e} jiffies, {n} passes -> {l} frames lost', flush=True)
    print('lost frames per run:', ' '.join(map(str, lost)),
          '(0 in every run = every pass fit in its frame)')


if __name__ == '__main__':
    main()
