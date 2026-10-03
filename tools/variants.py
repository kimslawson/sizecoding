#!/usr/bin/env python3
"""variants: try size ideas as named, combinable edits instead of editing the program.

A variants file is a small Python file:

    BASE = 'game.bas'                       # the readable source, relative to this file
    VARIANTS = {
        'inc':    [('X = X + 1', 'INC X')],
        'nomult': [('(B > 9) * 7', '-(B > 9) & 7'), ('(J & 1) * 15', '-(J & 1) & 15')],
    }

Each edit is an exact (old, new) string replacement on the source text, and `old` must occur
exactly once at the moment it is applied, so a stale variant fails loudly instead of quietly
doing nothing. Variants apply in the order given on the command line.

  variants.py FILE                 every variant alone, sorted by what it saves
  variants.py FILE a b c           the combination a+b+c; writes build/a+b+c.bas
  variants.py FILE a b c --keep    also keep the minimized listing next to it

Sizes are the "measure" (see fbsize.py) of the minimized program, so they don't depend on how
the lines happen to break. A variant that fails to compile is reported, not fatal.
"""
import os, sys, runpy, tempfile, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fblib


def apply(text, names, variants):
    for n in names:
        if n not in variants:
            raise SystemExit(f'unknown variant {n!r}; known: {", ".join(variants)}')
        for old, new in variants[n]:
            k = text.count(old)
            if k != 1:
                raise SystemExit(f'variant {n}: {old!r} occurs {k} times (must be exactly 1)')
            text = text.replace(old, new)
    return text


def size(src_bytes, width):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'v.bas'); open(p, 'wb').write(src_bytes)
        x, err = fblib.compile_xex(src_bytes)
        if x is None:
            return None, err.strip().splitlines()[-3:], None
        out, how = fblib.minimize(p, width)
        L = out.rstrip(fblib.EOL).split(fblib.EOL)
        return fblib.measure(L), how, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file'); ap.add_argument('names', nargs='*')
    ap.add_argument('--width', type=int, default=120)
    ap.add_argument('--keep', action='store_true')
    a = ap.parse_args()
    cfg = runpy.run_path(a.file)
    here = os.path.dirname(os.path.abspath(a.file))
    base = open(os.path.join(here, cfg['BASE']), 'rb').read().decode('latin1')
    V = cfg['VARIANTS']
    m0, how, _ = size(base.encode('latin1'), a.width)
    if m0 is None:
        raise SystemExit('the base does not compile: ' + ' / '.join(how))
    print(f"base: measure {m0['measure']} ({how})")
    if not a.names:
        rows = []
        for n in V:
            try:
                m, info, _ = size(apply(base, [n], V).encode('latin1'), a.width)
            except SystemExit as e:
                rows.append((10**9, n, str(e))); continue
            rows.append((m['measure'] - m0['measure'], n, 'ok') if m else (10**9, n, 'COMPILE FAIL: ' + ' / '.join(info)))
        for d, n, note in sorted(rows):
            print(f'  {n:24s} ' + (f'{d:+5d}' if d < 10**9 else '   --') + ('' if note == 'ok' else '  ' + note))
        return
    src = apply(base, a.names, V)
    m, info, out = size(src.encode('latin1'), a.width)
    tag = '+'.join(a.names)
    os.makedirs(os.path.join(here, 'build'), exist_ok=True)
    dst = os.path.join(here, 'build', tag + '.bas')
    open(dst, 'wb').write(src.encode('latin1'))
    if m is None:
        print(f'{tag}: COMPILE FAIL\n  ' + '\n  '.join(info)); sys.exit(1)
    print(f"{tag}: measure {m['measure']} ({m['measure'] - m0['measure']:+d}), "
          f"{m['lines']} lines as minimized -> {dst}")
    if a.keep:
        open(dst[:-4] + '.min', 'wb').write(out)


if __name__ == '__main__':
    main()
