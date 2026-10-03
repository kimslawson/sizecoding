#!/usr/bin/env python3
"""fbbench: what does a statement cost? Time FastBasic code blocks in the emulator.

A bench file has sections:

    [setup]          runs once: GRAPHICS, PMGRAPHICS, your display list, variables...
    GRAPHICS 0
    A = 5 : B = 7 : R = 100
    [pre]            optional: runs in every loop pass, including the empty baseline
    [block mul]      one section per block to time
    K = R * 40
    [block shift]
    K = R * 32

Each block runs N times inside a FOR loop; an empty loop (with [pre]) runs N times too, and the
difference, in jiffies, becomes the block's cost per pass in units of 2 scanlines (what VCOUNT
counts): a frame is 131 units on NTSC, 156 on PAL. That is wall time with DMA and interrupts
included, so do the setup your game does: text mode with players on costs more than a blank
screen. Resolution is 131/N units (N = 1000: 0.13).

  fbbench.py FILE [-n N] [--pal] [--source]

The emulator runs in turbo mode; the timing is in emulated jiffies, so the host's speed
doesn't matter.
"""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import emu


def parse(path):
    sec, cur, blocks, setup, pre = None, None, [], [], []
    for line in open(path, encoding='latin1'):
        line = line.rstrip('\n')
        m = re.match(r'\s*\[(setup|pre|block\s+(.*?))\]\s*$', line)
        if m:
            sec = m.group(1).split()[0]
            if sec == 'block':
                cur = [m.group(2), []]; blocks.append(cur)
            continue
        if sec == 'setup':
            setup.append(line)
        elif sec == 'pre':
            pre.append(line)
        elif sec == 'block':
            cur[1].append(line)
    if not blocks:
        raise SystemExit('no [block ...] sections')
    if len(blocks) > 20:
        raise SystemExit('at most 20 blocks per file')
    return setup, pre, blocks


def program(setup, pre, blocks, n):
    L = list(setup)
    L.append(f'DIM Z9_R({len(blocks)})')
    def loop(body):
        return [f'Z9_T=TIME', f'FOR Z9_I=1 TO {n}', *pre, *body, 'NEXT Z9_I']
    L += loop([]) + ['Z9_E=TIME-Z9_T']
    for k, (name, body) in enumerate(blocks):
        L += loop(body) + [f'Z9_R({k})=TIME-Z9_T']
    L += emu.readout_code()
    L.append('? Z9_E')
    L += [f'? Z9_R({k})' for k in range(len(blocks))]
    L.append('DO : LOOP')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('file'); ap.add_argument('-n', type=int, default=1000)
    ap.add_argument('--pal', action='store_true')
    ap.add_argument('--source', action='store_true', help='print the generated program')
    a = ap.parse_args()
    setup, pre, blocks = parse(a.file)
    src = program(setup, pre, blocks, a.n)
    if a.source:
        print(src)
    xex = emu.compile_bas(src, 'bench')
    want = len(blocks) + 1
    png, nums = emu.run(xex, wait=1.0, turbo=True, pal=a.pal, timeout=300,
                        until=lambda p: (lambda r: r if r and len(r) == want else None)(emu.read_numbers(p)))
    if not nums:
        raise SystemExit(f'could not read the results from the screen: {png}')
    upf = 156 if a.pal else 131
    base = nums[0]
    print(f'empty loop: {base} jiffies for {a.n} passes; resolution {upf / a.n:.2f} units')
    w = max(len(b[0]) for b in blocks)
    for (name, _), j in zip(blocks, nums[1:]):
        u = (j - base) * upf / a.n
        print(f'  {name:{w}s} {u:7.2f} units  ({u / upf * 100:5.2f}% of a frame)')


if __name__ == '__main__':
    main()
