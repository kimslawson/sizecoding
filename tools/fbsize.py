#!/usr/bin/env python3
"""fbsize: measure, minimize, pack and verify FastBasic ten-liner listings.

  fbsize.py measure FILE [--width W --lines N]
      Lines, longest line, chars, measure, and the slack left on every line.

  fbsize.py min SRC [-o OUT] [--tool auto|fbp|fb] [--keep-names] [--width W]
      Minimize a readable source. With fbp available it is used (it is shorter); either way the
      result is compiled with your FastBasic and compared with the source's XEX.

  fbsize.py stmts FILE
      Number every statement, for choosing --free and --glue ranges.

  fbsize.py pack MIN -o OUT [--width W --lines N] [--free A:B ...] [--glue A:B ...]
                            [--iters N --seed S]
      Break a minimized listing into lines. Statement order is kept, except inside --free
      ranges, where statements (or --glue groups, which stay together and in order) may be
      reordered to make the listing fit. A and B are statement numbers from `stmts`
      (B exclusive) or /regex/ matched against the statement text (first match).

  fbsize.py verify A B [--xex]
      Check that two listings hold the same statements (as a multiset). With --xex, also
      compile both and compare the XEX files (only meaningful when the order is the same).

Categories: --cat pur120 (default: 10 lines x 120), extreme256 (10 x 256), pur80 (10 x 80).
"""
import argparse, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fblib

CATS = {'pur80': (80, 10), 'pur120': (120, 10), 'extreme256': (256, 10)}


def limits(a):
    w, n = CATS[a.cat]
    return a.width or w, a.lines or n


def report(name, lines, width, nlines):
    m = fblib.measure(lines)
    ok = m['lines'] <= nlines and m['max'] <= width
    print(f"{name}: {m['lines']} lines, longest {m['max']}, {m['chars']} chars, "
          f"measure {m['measure']}, {m['statements']} statements -> "
          f"{'FITS' if ok else 'DOES NOT FIT'} {nlines} x {width}")
    return m, ok


def cmd_measure(a):
    width, nlines = limits(a)
    lines = fblib.read_lines(a.file)
    m, ok = report(a.file, lines, width, nlines)
    for i, l in enumerate(lines):
        print(f'  {i + 1:2d}  {len(l):4d}  slack {width - len(l):4d}')
    print(f"  room left if packed perfectly: {nlines * width - (m['measure'] - (nlines - 1))} chars"
          f" (always less in practice: a statement never splits across lines)")
    return 0 if ok else 1


def cmd_stmts(a):
    for i, s in enumerate(fblib.statements(a.file)):
        print(f'{i:4d} {len(s):4d}  {fblib.show(s)}')


def cmd_min(a):
    width, nlines = limits(a)
    src = open(a.src, 'rb').read()
    out, how = fblib.minimize(a.src, width, tool=a.tool, keep_names=a.keep_names)
    dst = a.output or os.path.splitext(a.src)[0] + '.min'
    open(dst, 'wb').write(out)
    report(f'{dst} ({how})', fblib.read_lines(dst), width, nlines)
    if a.tool == 'auto' and how.startswith('fbp'):
        fbm = fblib.fb_minimize(a.src, width)
        L = fbm.rstrip(fblib.EOL).split(fblib.EOL)
        mm = fblib.measure(L)['measure']; m2 = fblib.measure(fblib.read_lines(dst))['measure']
        print(f'  for comparison, fastbasic -l:min: measure {mm} ({mm - m2:+d} vs fbp)')
    x1, e1 = fblib.compile_xex(src)
    x2, e2 = fblib.compile_xex(out)
    if x2 is None:
        print('  COMPILE FAILED with your FastBasic:\n' + e2); return 1
    if x1 is None:
        print('  (source did not compile, cannot compare)\n' + e1); return 1
    print('  XEX identical to the source: yes' if x1 == x2 else
          '  XEX DIFFERS from the source (expected only for optimizations that change code)')
    return 0


def resolve(spec, stm):
    a, b = spec.split(':', 1) if not spec.startswith('/') else re.match(r'(/.*?/):(.*)', spec).groups()

    def one(x, default):
        if x == '':
            return default
        if x.startswith('/') and x.endswith('/') and len(x) > 1:
            rx = re.compile(x[1:-1].encode('latin1'))
            for i, s in enumerate(stm):
                if rx.search(s):
                    return i
            raise SystemExit(f'no statement matches {x}')
        return int(x)
    return one(a, 0), one(b, len(stm))


def greedy(stm, order, width):
    """Fixed order, first fit: the fewest lines, and the shortest last line."""
    lines, cur = [], b''
    for i in order:
        s = stm[i]
        if len(s) > width:
            return None
        if cur and len(cur) + 1 + len(s) <= width:
            cur += b':' + s
        else:
            if cur:
                lines.append(cur)
            cur = s
    if cur:
        lines.append(cur)
    return lines


def cost(lines, width):
    # where the listing ends, as if all lines were full: smaller is better
    return (len(lines) - 1) * width + len(lines[-1])


def dependencies(path, n):
    """Names each statement mentions, from FastBasic's own expansion of the listing.

    Returns a list of name sets aligned with the statements, or None if the expansion does
    not line up one statement per line.
    """
    exp = fblib.expand(open(path, 'rb').read())
    if exp is None or len(exp) != n:
        return None
    return [fblib.names(e) for e in exp]


def cmd_pack(a):
    width, nlines = limits(a)
    stm = fblib.statements(a.min)
    free = [resolve(f, stm) for f in a.free]
    glue = [resolve(g, stm) for g in a.glue]
    # units: glue groups are one unit, every other statement is its own unit
    unit_of = {}
    for g0, g1 in glue:
        for i in range(g0, g1):
            unit_of[i] = (g0, g1)
    seq, i = [], 0          # seq: list of segments; a free segment is a list of units
    while i < len(stm):
        fr = next(((f0, f1) for f0, f1 in free if f0 == i), None)
        if fr:
            units, j = [], fr[0]
            while j < fr[1]:
                g = unit_of.get(j, (j, j + 1))
                if g[1] > fr[1]:
                    raise SystemExit(f'glue {g} crosses the end of free range {fr}')
                units.append(list(range(g[0], g[1]))); j = g[1]
            seq.append(('free', units)); i = fr[1]
        else:
            seq.append(('fixed', [[i]])); i += 1

    # Order rules found automatically, inside each free range:
    #  1. the first statement (in the original order) that mentions a name stays before every
    #     other statement that mentions it: FastBasic needs a variable defined before use.
    #  2. unless --allow-var-reorder, those first mentions keep their relative order, so the
    #     variables are created in the same order and sit at the same addresses.
    rules = []              # (earlier statement, later statement)
    if free:
        deps = dependencies(a.min, len(stm))
        if deps is None:
            print('  warning: could not line up the expansion; no automatic order rules')
        else:
            first = {}
            for k, ns in enumerate(deps):
                for v in ns:
                    first.setdefault(v, k)
            for f0, f1 in free:
                for k in range(f0, f1):
                    for v in deps[k]:
                        if first[v] != k and f0 <= first[v] < f1:
                            rules.append((first[v], k))
                if not a.allow_var_reorder:
                    defs = sorted({first[v] for v in first if f0 <= first[v] < f1})
                    rules += list(zip(defs, defs[1:]))
    rules = sorted(set(rules))

    def order_of(state):
        return [k for kind, units in state for u in units for k in u]

    def valid(order):
        pos = {k: i for i, k in enumerate(order)}
        return all(pos[x] < pos[y] for x, y in rules)

    state = [(k, [list(u) for u in us]) for k, us in seq]
    if not valid(order_of(state)):
        raise SystemExit('the original order breaks the order rules (bug?)')
    lines = greedy(stm, order_of(state), width)
    if lines is None:
        raise SystemExit('a statement is longer than the line width')
    best, bestc = [list(map(list, us)) for _, us in state], cost(lines, width)
    frees = [i for i, (k, us) in enumerate(state) if k == 'free' and len(us) > 1]
    if frees and a.iters:
        rnd = random.Random(a.seed)
        cur_c, T = bestc, 30.0
        for it in range(a.iters):
            si = rnd.choice(frees); us = state[si][1]
            x, y = rnd.sample(range(len(us)), 2)
            swap = rnd.random() < 0.5
            if swap:
                us[x], us[y] = us[y], us[x]
            else:
                u = us.pop(x); us.insert(y, u)
            order = order_of(state)
            ok = valid(order)
            c = cost(greedy(stm, order, width), width) if ok else None
            if ok and (c <= cur_c or rnd.random() < pow(2.718, (cur_c - c) / T)):
                cur_c = c
            elif swap:
                us[x], us[y] = us[y], us[x]
            else:
                us.pop(y); us.insert(x, u)
            if cur_c < bestc:
                bestc = cur_c; best = [list(map(list, us2)) for _, us2 in state]
            T = max(0.05, 30.0 * (1 - it / a.iters))
        state = [(k, us) for (k, _), us in zip(state, best)]
    order = order_of(state)
    lines = greedy(stm, order, width)
    fblib.write_listing(a.output, lines)
    m, ok = report(a.output, lines, width, nlines)
    if order != list(range(len(stm))):
        print(f'  statement order changed inside the free ranges ({len(rules)} order rules kept):')
        print('  ' + ' '.join(map(str, order)))
        x, err = fblib.compile_xex(open(a.output, 'rb').read())
        print('  compiles: yes' if x else '  DOES NOT COMPILE:\n' + err)
        print('  The compiled code changed with the order: rerun your tests. Order that matters '
              'without a shared variable (GRAPHICS before reading the display list, say) is '
              'yours to protect with --glue.')
    return 0 if ok else 1


def cmd_verify(a):
    from collections import Counter
    sa, sb = fblib.statements(a.a), fblib.statements(a.b)
    same = Counter(sa) == Counter(sb)
    print('same statements' if same else 'DIFFERENT statements')
    if not same:
        for s in (Counter(sa) - Counter(sb)):
            print('  only in A:', fblib.show(s))
        for s in (Counter(sb) - Counter(sa)):
            print('  only in B:', fblib.show(s))
    if a.xex:
        xa, ea = fblib.compile_xex(open(a.a, 'rb').read())
        xb, eb = fblib.compile_xex(open(a.b, 'rb').read())
        print('XEX identical' if xa and xa == xb else 'XEX differs (or a compile failed)')
        same = same and xa is not None and xa == xb
    return 0 if same else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    def lim(sp):
        sp.add_argument('--cat', choices=CATS, default='pur120')
        sp.add_argument('--width', type=int)
        sp.add_argument('--lines', type=int)
    s = sub.add_parser('measure'); s.add_argument('file'); lim(s)
    s = sub.add_parser('stmts'); s.add_argument('file')
    s = sub.add_parser('min'); s.add_argument('src'); s.add_argument('-o', '--output'); lim(s)
    s.add_argument('--tool', choices=['auto', 'fbp', 'fb'], default='auto')
    s.add_argument('--keep-names', action='store_true', help='fbp -f: do not rename variables')
    s = sub.add_parser('pack'); s.add_argument('min'); s.add_argument('-o', '--output', required=True); lim(s)
    s.add_argument('--free', action='append', default=[])
    s.add_argument('--glue', action='append', default=[])
    s.add_argument('--iters', type=int, default=50000)
    s.add_argument('--seed', type=int, default=1)
    s.add_argument('--allow-var-reorder', action='store_true',
                   help='let variables be created in a different order (changes their addresses)')
    s = sub.add_parser('verify'); s.add_argument('a'); s.add_argument('b')
    s.add_argument('--xex', action='store_true')
    a = p.parse_args()
    sys.exit({'measure': cmd_measure, 'stmts': cmd_stmts, 'min': cmd_min, 'pack': cmd_pack,
              'verify': cmd_verify}[a.cmd](a) or 0)


if __name__ == '__main__':
    main()
