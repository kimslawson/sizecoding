#!/usr/bin/env python3
"""fboverruns: log only the main-loop passes that overran their frame, with context.

  fboverruns.py PROG.bas --vars A,B,C [--keys "xdotool script"] [--seconds 10]
                [--exclude-proc NAME] [--sub "OLD=>NEW" ...]

fbframes.py says how many frames were lost; this says which passes lost them and what the
game was doing. It adds `Z9T = TIME` right after the loop's PAUSE and, before the loop's
`LOOP` (the first one at column 0), an IF that logs a pass whose TIME moved more than 1:
jiffies taken, then the listed variables, into a 128-entry ring at $9000 (BASIC off). One IF
per pass, so the timing barely moves.

--exclude-proc NAME: passes that called PROC NAME aren't logged (for a deliberate pause,
such as building a new level). The PROC's body must sit between `PROC NAME` and the next
`ENDPROC` at column 0.
--sub OLD=>NEW: replace text in a copy of the program first (an autoplayer, say).
"""
import argparse, os, re, sys, tempfile, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('prog'); ap.add_argument('--vars', required=True)
    ap.add_argument('--keys', default=''); ap.add_argument('--seconds', type=float, default=10)
    ap.add_argument('--exclude-proc', default=None)
    ap.add_argument('--sub', action='append', default=[])
    ap.add_argument('--wait', type=float, default=4)
    a = ap.parse_args()
    s = open(a.prog, encoding='latin1').read()
    for r in a.sub:
        o, n = r.split('=>'); assert o in s, 'no match: ' + o; s = s.replace(o, n)
    s = 'Z9C = 0 : Z9M = 0 : Z9T = 0\n' + s
    if a.exclude_proc:
        m = re.search(r'(PROC %s\n)(.*?)(\nENDPROC)' % re.escape(a.exclude_proc), s, re.S | re.I)
        if not m:
            sys.exit(f'PROC {a.exclude_proc} not found')
        s = s[:m.start()] + m.group(1) + m.group(2) + '\n  Z9M = 1' + m.group(3) + s[m.end():]
    names = a.vars.split(',')
    if not re.search(r'^\s*PAUSE\s*$', s, re.M):
        sys.exit('need a PAUSE on a line of its own')
    s = re.sub(r'^(\s*)PAUSE\s*$', r'\1PAUSE\n\1Z9T = TIME : Z9M = 0', s, count=1, flags=re.M)
    log = ['  IF TIME - Z9T > 1 + Z9M * 999', '    Z9A = $9000 + (Z9C & 127) * 32 : INC Z9C',
           '    DPOKE Z9A, TIME - Z9T']
    log += [f'    DPOKE Z9A + {2 + 2*i}, {v}' for i, v in enumerate(names)]
    log += ['  ENDIF']
    if not re.search(r'^LOOP\s*$', s, re.M):
        sys.exit('need the main loop to end with LOOP at column 0')
    s = re.sub(r'^LOOP\s*$', '\n'.join(log) + '\nLOOP', s, count=1, flags=re.M)
    xex, labels = emu.compile_with_labels(s, 'over')
    with emu.Session(xex, labels, wait=a.wait) as ses:
        k = ses.keys(a.keys) if a.keys else None
        time.sleep(a.seconds)
        ses.stop()
        n = ses.var('Z9C')
        out = tempfile.mktemp()
        ses._send([f'WRITE 9000 9FFF {out}']); time.sleep(0.3)
        if k: k.kill()
    d = open(out, 'rb').read()
    print(f'overruns: {n}   (jiffies ' + ' '.join(names) + ')')
    for i in range(max(0, n - 128), n):
        o = (i & 127) * 32
        w = [int.from_bytes(d[o + 2*j:o + 2*j + 2], 'little', signed=True) for j in range(1 + len(names))]
        print('   ', ' '.join(f'{x:6d}' for x in w))


if __name__ == '__main__':
    main()
