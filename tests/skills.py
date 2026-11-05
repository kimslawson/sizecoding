#!/usr/bin/env python3
"""Checks claims the agent skills in skills/ make beyond docs/, against the real compiler.

Three kinds of check:

  compiles(id, src, target, ok)   the source must (ok=True) or must not (ok=False) compile
  value(id, src, expect)          run in the emulator; each 'NAME' or '@addr:n' must read as
                                  expected after the program reaches its PAUSE
  dcb(id, fp_stmt, int_stmt)      the SIO device control block ($0300-$030B, minus DSTATS,
                                  which SIO overwrites with the result) left by a FujiNet
                                  statement (floating point target) equals the one left by
                                  its SIO equivalent (integer target)

  python3 tests/skills.py           compile checks only (needs FASTBASIC)
  python3 tests/skills.py --run     also the emulator checks (Linux + atari800)
"""
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
os.environ.setdefault('PYTHONDONTWRITEBYTECODE', '1')
import fblib

C, V, D = [], [], []


def compiles(id, src, target='atari-int', ok=True):
    C.append((id, src, target, ok))


def value(id, src, expect, target='atari-int'):
    V.append((id, src, expect, target))


def dcb(id, fp_stmt, int_stmt, ctx_fp='', ctx_int=''):
    D.append((id, fp_stmt, int_stmt, ctx_fp, ctx_int))


# --- fastbasic/SKILL.md traps and reference/language.md ------------------------------------
compiles('fujinet-not-in-int', 'S$="N:HTTP://X/"\nNOPEN 1,4,0,S$', 'atari-int', ok=False)
compiles('fujinet-in-fp', 'S$="N:HTTP://X/"\nNOPEN 1,4,0,S$\nNSTATUS 1\nNCLOSE 1', 'atari-fp')
compiles('sio-in-int', 'SIO $71, 1, $53, $40, $2EA, $1F, 4, 0, 0\nK = SERR()', 'atari-int')
compiles('one-name-space', 'G$ = "AB"\nG = 1', ok=False)
compiles('declare-before-use', 'K = Q + 1\nQ = 2', ok=False)
compiles('declare-before-proc-use', 'PROC P\n K = T0\nENDPROC\nT0 = 1\n@P', ok=False)
compiles('one-line-if-ok', 'A = 1\nIF A THEN B = 1')
compiles('no-one-line-else', 'A = 1\nIF A THEN B = 1 ELSE B = 2', ok=False)
compiles('bare-fn-args', 'K = PEEK PEEK 88 + STICK 0 + RAND 10')
compiles('label-shares-letter', 'DATA D() BYTE = 1, 2\nD = DPEEK(560)\nK = D(1)')
compiles('dli-set-forms', 'DATA CS() BYTE = 224, 4\nDATA PF() BYTE = 0, 15\n'
         'DLI SET N = 4 INTO 54281\nDLI SET T = CS INTO 54281, PF INTO 53270\nDLI T\nDLI')

value('prec-not-a-wrap', 'X = 7\nK = X + 1 & 7', {'K': 8})
value('prec-minus-and', 'T = 13\nK = 15 - T & 12', {'K': 3})
value('prec-mul-and', 'X = 3 : Y = 13\nK = X * Y & 15', {'K': 39})
value('pal-ntsc-60', 'K = PEEK(53268) & 10 + 50', {'K': 60})
value('if-then-one-statement', 'A = 0 : B = 0\nIF A THEN C = 1 : B = 5', {'B': 5})
value('mask-from-compare', 'B = 12\nK = -(B > 9) & 7\nL = (B > 9) * 7', {'K': 7, 'L': 7})
value('poke-low-byte', 'V = 10\nPOKE 1536, -1 - V', {'@1536:1': (245,)})
value('literal-length-byte', 'K = PEEK(&"HELLO")\nL = PEEK(&"HELLO" + 1)', {'K': 5, 'L': 72})
value('data-element-0-is-length', 'DATA X() BYTE = "ABC"\nK = X(0)\nL = X(1)', {'K': 3, 'L': 65})
value('dim-order-is-memory-order', 'DIM A, B, C\nK = &B - &A\nL = &C - &A', {'K': 2, 'L': 4})
value('string-takes-256', 'DIM P(3) BYTE\nA$ = "XY"\nDIM Q(3) BYTE\nK = ADR(Q) - ADR(P)',
      {'K': 260})
value('high-byte-peek', 'F = 1280 + 77\nK = PEEK(&F + 1)\nL = F / 256', {'K': 5, 'L': 5})
value('variables-start-at-0', 'DIM Q9\nK = Q9', {'K': 0})
value('dli-enable-costs-a-frame',
      'DLI SET N = 0 INTO 53274\nPAUSE\nT = TIME\nDLI N\nU = TIME - T\nDLI', {'U': 1})
value('time-or-1-is-odd', 'PAUSE 6\nH = TIME ! 1\nK = H & 1', {'K': 1})

# --- fastbasic-sizecoding/reference/size-tricks.md, beyond tests/tricks.py ------------------
value('fold-two-tests', 'K = 3 : B = 1\nX = K & B\nK = K - B & K\n'
      'J = 2 : Y = J & B\nJ = J - B & J\nM = 3 : B2 = 0\nM = M - B2 & M',
      {'X': 1, 'K': 2, 'Y': 0, 'J': 2, 'M': 3})
value('scroll-range-test', 'A = 2048 & -2048\nB = -1 & -2048\nC = 2047 & -2048\n'
      'D = (2048 > 0) * 80 - 40\nE = (-1 > 0) * 80 - 40',
      {'A': 2048, 'B': -2048, 'C': 0, 'D': 40, 'E': -40})
value('row-times-40', 'R = 37 : M = 3\nK = (R + M) & -8 * 5\nL = (R + M) / 8 * 40', {'K': 200, 'L': 200})
value('rotation-forms-agree',
      'O = 2 : J = 11\nA = (O + (J & 8 = 0) - (J & 4 = 0)) & 7\nB = (O + J & 4 / 4 - J & 8 / 8) & 7\n'
      'J = 7\nC = (O + (J & 8 = 0) - (J & 4 = 0)) & 7\nD = (O + J & 4 / 4 - J & 8 / 8) & 7\n'
      'J = 15\nE = (O + (J & 8 = 0) - (J & 4 = 0)) & 7\nF = (O + J & 4 / 4 - J & 8 / 8) & 7',
      {'A': 1, 'B': 1, 'C': 3, 'D': 3, 'E': 2, 'F': 2})
BCD = 'W = W + 1 + (W & 15 = 9) * 6 + (W & 255 = 89) * 160 + (W & 4095 = 2393) * 1536'
value('bcd-clock', '\n'.join(f'W = ${w:04X}\n{BCD}\n{n} = W' for w, n in
                             ((0x0009, 'A'), (0x0059, 'B'), (0x0959, 'C'), (0x1234, 'D'))),
      {'A': 0x0010, 'B': 0x0100, 'C': 0x1000, 'D': 0x1235})
value('mask-flag-complement', 'F = -1 : V = 10\nK = F - V & F\nF = 0\nL = F - V & F',
      {'K': -11, 'L': 0})
value('glyph-address', 'K = 65 * 8 - 8448\nL = K - 57344', {'L': 264})
value('screen-code-from-atascii', 'C = 65\nK = C - 32 * (C < 96)\nC = 97\nL = C - 32 * (C < 96)',
      {'K': 33, 'L': 97})

# --- fastbasic/reference/fujinet.md: the SIO equivalents ------------------------------------
URL_FP = 'DIM P(1)\nS$ = "N:HTTP://EXAMPLE.COM/"'
URL_INT = URL_FP
dcb('nopen', 'NOPEN 2, 12, 3, S$', 'SIO $71, 2, $4F, $80, &S$ + 1, $1F, 256, 12, 3', URL_FP, URL_INT)
dcb('nstatus', 'NSTATUS 3', 'SIO $71, 3, $53, $40, $2EA, $1F, 4, 0, 0',
    'DPOKE $30A, 0', 'DPOKE $30A, 0')
dcb('nget', 'L = 300\nNGET 4, 1600, L', 'L = 300\nSIO $71, 4, $52, $40, 1600, $1F, L, L & 255, PEEK(&L + 1)')
dcb('nput', 'L = 300\nNPUT 5, 1600, L', 'L = 300\nSIO $71, 5, $57, $80, 1600, $1F, L, L & 255, PEEK(&L + 1)')
dcb('nclose', 'NCLOSE 6', 'SIO $71, 6, $43, 0, 0, $1F, 0, 0, 0',
    'DPOKE $304, 0 : DPOKE $30A, 0', 'DPOKE $304, 0 : DPOKE $30A, 0')


def compile_ok(src, target):
    x, err = fblib.compile_xex((src + '\n').encode('latin1'), target=target)
    return x is not None, err


def run_values(src, names, target):
    import emu
    old = fblib.TARGET
    fblib.TARGET = target
    try:
        xex, labels = emu.compile_with_labels(src + '\nDO\nPAUSE\nLOOP\n', 'sk')
    finally:
        fblib.TARGET = old
    out = {}
    with emu.Session(xex, labels, wait=1.5) as s:
        s.sync('EXE_PAUSE')
        for n in names:
            if n.startswith('@'):
                a, _, k = n[1:].partition(':')
                out[n] = tuple(s.mem(int(a), int(k or 1)))
            else:
                out[n] = s.var(n)
    return out


def dcb_of(ctx, stmt, target):
    """The DCB after stmt, minus DSTATS. A buffer that is a string's address differs between
    targets, so when the context defines S$, DBUF is checked against &S$+1 and then masked."""
    src = (ctx + '\n' if ctx else '') + stmt + '\nMOVE $300, 1536, 12'
    names = ['@1536:12']
    if 'S$' in ctx:
        src += '\nK = &S$ + 1'
        names.append('K')
    got = run_values(src, names, target)
    v = list(got['@1536:12'])
    if 'S$' in ctx:
        k = got['K'] & 0xFFFF
        v[4], v[5] = ('ok', 'ok') if (v[4], v[5]) == (k & 255, k >> 8) else ('BAD', 'BAD')
    del v[3]                      # DSTATS ($0303): SIO writes the result there
    return tuple(v)


def main():
    run = '--run' in sys.argv
    bad = n = 0
    for id, src, target, ok in C:
        n += 1
        got, err = compile_ok(src, target)
        good = got == ok
        bad += not good
        print(f"{'ok  ' if good else 'FAIL'} {id:28} {target:10} "
              f"{'compiles' if got else 'rejected'} (expected {'compiles' if ok else 'rejected'})")
        if not good and err:
            print('     ' + err.strip().splitlines()[-1][:120])
    if run:
        for id, src, expect, target in V:
            n += 1
            got = run_values(src, list(expect), target)
            want = {k: (tuple(v) if isinstance(v, tuple) else v) for k, v in expect.items()}
            good = got == want
            bad += not good
            print(f"{'ok  ' if good else 'FAIL'} {id:28} {got}" + ('' if good else f'  expected {want}'))
        for id, fp, it, cfp, cit in D:
            n += 1
            a = dcb_of(cfp, fp, 'atari-fp')
            b = dcb_of(cit, it, 'atari-int')
            good = a == b
            bad += not good
            hexs = lambda t: ' '.join(x if isinstance(x, str) else '%02X' % x for x in t)
            print(f"{'ok  ' if good else 'FAIL'} dcb-{id:24} {hexs(a)}" +
                  ('' if good else f'\n     SIO gives               {hexs(b)}'))
    print(f'{n - bad}/{n} claims hold')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
