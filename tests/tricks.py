#!/usr/bin/env python3
"""Checks every size claim in docs/03-size-tricks.md against the real compiler.

Each trick is a `before` and an `after` snippet in readable FastBasic, plus a `ctx` that
defines what the snippets need. The checker builds `ctx + before` and `ctx + after`, makes
sure both compile, minimizes both with fbp (keeping names, so only the trick changes) and with
FastBasic's own -ls, and compares the saving with the number the docs claim.

`same` = the trick must compile to identical code (a pure spelling change). Otherwise the
behavior is checked by `check`: FastBasic statements that run after the snippet and must
leave the same values in the listed variables (compared through the emulator, see --run).

  python3 tests/tricks.py            sizes only (needs FASTBASIC, FBP)
  python3 tests/tricks.py --run      also run the behavior checks in the emulator (Linux)
"""
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import fblib

T = []


def trick(id, before, after, saves, ctx='', same=False, check=None, fbmin=None):
    T.append(dict(id=id, before=before, after=after, saves=saves, ctx=ctx, same=same,
                  check=check, fbmin=fbmin))


# --- let the tools spell -------------------------------------------------------------------
trick('fn-parens', 'K = PEEK(712)', 'K = PEEK 712', (0, 2), same=True)

# --- statements ----------------------------------------------------------------------------
trick('inc', 'X = X + 1', 'INC X', (1, 1), ctx='X = 5', check='X')
trick('inc-2letter', 'QD = QD + 1', 'INC QD', (2, 2), ctx='QD = 5', check='QD')
trick('dec', 'X = X - 1', 'DEC X', (1, 1), ctx='X = 5', check='X')
trick('if-then', 'IF A = 1\n B = 2\nENDIF', 'IF A = 1 THEN B = 2', (0, 2), ctx='A = 1 : B = 0',
      check='B')
trick('elif', 'IF A = 1\n B = 2\nELSE\n IF A = 3\n  B = 4\n ENDIF\nENDIF',
      'IF A = 1\n B = 2\nELIF A = 3\n B = 4\nENDIF', (0, 5), ctx='A = 3 : B = 0', check='B')
trick('cmp-zero', 'IF A <> 0 THEN B = 1', 'IF A THEN B = 1', (0, 2), ctx='A = 7 : B = 0', same=False,
      check='B')
trick('sound-off', 'SOUND\nK = 1', 'K = 1', (3, 3))
trick('dpoke-pair', 'POKE 1536, V : POKE 1537, C', 'DPOKE 1536, C * 256 + V', (3, 3),
      ctx='V = 100 : C = 168', check='@1536:2')
trick('mset-vars', 'A = 0 : B = 0 : C = 0 : D = 0', 'MSET & A, 8, 0', (6, 6),
      ctx='DIM A, B, C, D\nA = 1 : B = 2 : C = 3 : D = 4', check='A B C D')
trick('move-loop', 'FOR I = 0 TO 8\n POKE 1600 + I, PEEK(1536 + I)\nNEXT I',
      'MOVE 1536, 1600, 9', (18, 19), ctx='DPOKE 1536, 4660 : DPOKE 1544, 22136', check='@1600:9')
trick('abs', 'IF X < 0 THEN X = -X', 'X = ABS X', (6, 6), ctx='X = -5', check='X')

# --- expressions ---------------------------------------------------------------------------
trick('prec-and-div', 'K = (J & 4) / 4', 'K = J & 4 / 4', (0, 2), ctx='J = 13', check='K', same=True)
trick('prec-add-and', 'I = I + (U & B)', 'I = I + U & B', (0, 2), ctx='I = 1 : U = 12 : B = -1',
      check='I', same=True)
trick('prec-and-mul', 'K = ((R + M) & -8) * 5', 'K = (R + M) & -8 * 5', (0, 2),
      ctx='R = 37 : M = 3', check='K', same=True)
trick('stick-y', 'IF S & 1 = 0\n DY = -1\nELIF S & 2 = 0\n DY = 1\nELSE\n DY = 0\nENDIF',
      'DY = S & 1 - S & 2 / 2', (28, 28), ctx='S = STICK(0)', check='DY')
trick('stick-x', 'IF S & 4 = 0\n DX = -1\nELIF S & 8 = 0\n DX = 1\nELSE\n DX = 0\nENDIF',
      'DX = S & 4 / 4 - S & 8 / 8', (26, 26), ctx='S = 11', check='DX')
trick('cond-add', 'IF B > 9 THEN K = K + 7', 'K = K + (B > 9) * 7', (1, 1),
      ctx='B = 12 : K = 1', check='K')
trick('cond-assign', 'IF A > B\n F = 1\nELSE\n F = 0\nENDIF', 'F = A > B', (15, 15),
      ctx='A = 5 : B = 3', check='F')
trick('cond-mask', 'K = (B > 9) * 7', 'K = -(B > 9) & 7', (-1, -1), ctx='B = 12', check='K')
trick('or-negative', 'IF L < 0 OR R < 0 THEN K = 0', 'IF L ! R < 0 THEN K = 0', (3, 3),
      ctx='L = 5 : R = -3 : K = 1', check='K')
trick('range-pow2', 'IF X < 0 OR X > 127 THEN K = 0', 'IF X & -128 THEN K = 0', (4, 4),
      ctx='X = 130 : K = 1', check='K')
# Not 'X = X + 1 & 7': & binds tighter than +, so that is X + 1. The behavior check caught it.
trick('wrap-pow2', 'INC X\nIF X > 7 THEN X = 0', 'X = (X + 1) & 7', (6, 6), ctx='X = 7', check='X')
trick('mod-and', 'K = X MOD 8', 'K = X & 7', (2, 2), ctx='X = 21', check='K')
trick('toggle-01', 'IF F = 0\n F = 1\nELSE\n F = 0\nENDIF', 'F = 1 - F', (15, 15), ctx='F = 1',
      check='F')
trick('toggle-mask', 'IF F = 0\n F = -1\nELSE\n F = 0\nENDIF', 'F = -1 - F', (15, 15), ctx='F = 0',
      check='F')
trick('clamp-zero', 'IF E < 0 THEN E = 0', 'E = E & -(E > 0)', (0, 0), ctx='E = -3', check='E')
trick('count-down-stop', 'IF E > 0 THEN DEC E', 'E = E - (E > 0)', (2, 2), ctx='E = 3', check='E')
trick('complement', 'POKE J, 255 - V', 'POKE J, -1 - V', (1, 1), ctx='J = 1536 : V = 7', check='@1536')
trick('negative-const', 'K = X & 65520', 'K = X & -16', (0, 0), ctx='X = 1234', check='K', same=True)

trick('const-var', 'POKE 53248, A : POKE 53249, B : POKE 53250, C : POKE 53251, D',
      'H = 53248 : POKE H, A : POKE H + 1, B : POKE H + 2, C : POKE H + 3, D', (2, 2),
      ctx='A = 1 : B = 2 : C = 3 : D = 4')
trick('do-loop', 'REPEAT\n INC K\n IF K > 9 THEN EXIT\nUNTIL 0', 'DO\n INC K\n IF K > 9 THEN EXIT\nLOOP',
      (1, 1), ctx='K = 0', check='K')
trick('print-sep', 'PRINT "A="; A', 'PRINT "A=" A', (0, 1), ctx='A = 3')

# --- data ----------------------------------------------------------------------------------
trick('literal-addr', 'G$ = "ABCDEFGH"\nMOVE & G$ + 1, 1536, 8', 'MOVE & "ABCDEFGH" + 1, 1536, 8',
      (6, 6), check='@1536:8')
trick('data-to-string', 'DATA X() BYTE = 24, 60, 126, 255, 126, 60, 24, 0\nMOVE ADR(X), 1536, 8',
      'X$ = "' + '\x18<~\xff~<\x18' + '"$00\nMOVE & X$ + 1, 1536, 8', (18, 18), check='@1536:8')


def build(t, which):
    return (t['ctx'] + '\n' if t['ctx'] else '') + t[which] + '\n'


def sizes(src):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 't.bas'); open(p, 'wb').write(src.encode('latin1'))
        x, err = fblib.compile_xex(src.encode('latin1'))
        if x is None:
            return None, None, None, err
        a = fblib.fbp_minimize(p, 255, keep_names=True)
        b = fblib.fb_minimize(p, 255)
        ma = fblib.measure(a.rstrip(fblib.EOL).split(fblib.EOL))['measure']
        mb = fblib.measure(b.rstrip(fblib.EOL).split(fblib.EOL))['measure']
        return ma, mb, x, ''


def behavior(t):
    """Run before and after in the emulator; return (values before, values after)."""
    import emu
    out = []
    for which in ('before', 'after'):
        src = build(t, which) + 'DO\nPAUSE\nLOOP\n'
        xex, labels = emu.compile_with_labels(src, 'trick')
        vals = []
        with emu.Session(xex, labels, wait=1.5) as s:
            s.sync('EXE_PAUSE')
            for item in t['check'].split():
                if item.startswith('@'):
                    a, _, n = item[1:].partition(':')
                    vals.append(tuple(s.mem(int(a), int(n or 1))))
                else:
                    vals.append(s.var(item))
        out.append(vals)
    return out


def main():
    run = '--run' in sys.argv
    bad = 0
    for t in T:
        ma0, mb0, x0, e0 = sizes(build(t, 'before'))
        ma1, mb1, x1, e1 = sizes(build(t, 'after'))
        if x0 is None or x1 is None:
            print(f"FAIL {t['id']}: does not compile\n{e0}{e1}"); bad += 1; continue
        got = (ma0 - ma1, mb0 - mb1)
        ok = got == tuple(t['saves'])
        if t['same'] and x0 != x1:
            ok = False; note = ' (code differs, expected identical)'
        else:
            note = ' (same code)' if x0 == x1 else ''
        print(f"{'ok  ' if ok else 'FAIL'} {t['id']:18s} saves {got[0]:+3d} with fbp -O, "
              f"{got[1]:+3d} with -ls (claimed {t['saves'][0]:+d}, {t['saves'][1]:+d}){note}")
        if run and t['check'] and ok:
            b, a = behavior(t)
            if b != a:
                ok = False
            print(f"     behavior {'same' if b == a else 'DIFFERENT'}: {t['check']} = {b} / {a}")
        bad += not ok
    print(f'{len(T) - bad}/{len(T)} claims hold')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
