#!/usr/bin/env python3
"""Checks the toolchain itself. Size checks need FastBasic (and fbp); --emu adds the emulator.

  python3 tests/selftest.py [--emu]
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '..', 'tools')
emu = '--emu' in sys.argv
fails = 0


def run(args, expect):
    global fails
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True)
    ok = expect(r)
    print(('ok    ' if ok else 'FAIL  ') + ' '.join(os.path.basename(a) for a in args))
    if not ok:
        print(r.stdout[-1500:], r.stderr[-1500:]); fails += 1


drops = os.path.join(HERE, '..', 'examples', 'drops')
run([os.path.join(TOOLS, 'fbsize.py'), 'min', os.path.join(drops, 'drops.bas'), '-o', '/tmp/selftest.min'],
    lambda r: 'XEX identical to the source: yes' in r.stdout)
run([os.path.join(TOOLS, 'fbsize.py'), 'pack', '/tmp/selftest.min', '-o', '/tmp/selftest.BAS'],
    lambda r: 'FITS' in r.stdout)
run([os.path.join(TOOLS, 'fbsize.py'), 'verify', '/tmp/selftest.min', '/tmp/selftest.BAS', '--xex'],
    lambda r: r.returncode == 0)
run([os.path.join(HERE, 'tricks.py')] + (['--run'] if emu else []), lambda r: r.returncode == 0)
if emu:
    run([os.path.join(TOOLS, 'fbframes.py'), os.path.join(HERE, 'fits.bas'), '--seconds', '3'],
        lambda r: 'lost frames per run: 0 ' in r.stdout)
    run([os.path.join(TOOLS, 'fbframes.py'), os.path.join(HERE, 'overruns.bas'), '--seconds', '3'],
        lambda r: 'lost frames per run: 0 ' not in r.stdout and 'frames lost' in r.stdout)
    run([os.path.join(TOOLS, 'proof.py'), '/tmp/selftest.BAS', '-o', '/tmp/selftest.png'],
        lambda r: r.returncode == 0)
print('all ok' if not fails else f'{fails} failed')
sys.exit(1 if fails else 0)
