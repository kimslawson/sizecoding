# Tools

Python 3 scripts for measuring, minimizing, packing, timing and proving FastBasic ten-liners.

## Requirements

| For | You need |
|---|---|
| everything | Python 3.8+, [FastBasic](https://github.com/dmsc/fastbasic) (the cross-compiler) |
| shorter listings | [fbp](https://github.com/kimslawson/fastbasic-parser) (optional; used automatically when found) |
| `proof.py`, the emulator tools | Pillow and numpy (`pip install pillow numpy`) |
| `fbbench.py`, `fbframes.py`, `fontgrab.py`, `tests/tricks.py --run` | Linux with atari800 5.x, Xvfb, xdotool and ImageMagick |

Environment variables: `FASTBASIC` (path to the compiler, default `fastbasic` on the PATH),
`FBP` (path to fbp, default `fbp`), `FB_TARGET` (default `atari-int`), `EMU_DISPLAY` (the
virtual display, default `:99`).

On a Mac, the size tools run natively; run the emulator tools in a Linux VM or container.

## fbsize.py

```
fbsize.py measure FILE [--cat pur120|extreme256|pur80] [--width W --lines N]
fbsize.py min SRC [-o OUT] [--tool auto|fbp|fb] [--keep-names]
fbsize.py stmts FILE
fbsize.py pack MIN -o OUT [--free A:B ...] [--glue A:B ...] [--iters N] [--seed S] [--allow-var-reorder]
fbsize.py verify A B [--xex]
```

- **measure**: lines, longest line, characters, measure, and the slack on each line.
- **min**: minimizes a readable source with fbp `-O` if it's available, else FastBasic's `-ls`,
  then compiles the source and the result with your FastBasic and says whether the XEX is
  identical. With fbp it also prints what `-ls` would have given.
- **stmts**: numbers every statement (for `--free` and `--glue`).
- **pack**: breaks a minimized listing into lines, first fit. With `--free`, statements inside
  the range may be reordered (simulated annealing) to make it fit, keeping definition-before-use
  and variable creation order automatically, and any `--glue` groups together. Ranges are
  statement numbers or `/regex/` (first match). See [Packing](../docs/06-packing.md).
- **verify**: same statements in both listings (as a multiset); `--xex` also compares the
  compiled code.

## variants.py

```
variants.py FILE                 each variant alone, sorted by saving
variants.py FILE a b c [--keep]  the combination, written to build/a+b+c.bas
```

`FILE` is a Python file with `BASE` (the readable source) and `VARIANTS` (name: list of exact
`(old, new)` replacements, each of which must match exactly once). See
[Workflow](../docs/07-workflow.md) and [`examples/drops/ideas.py`](../examples/drops/ideas.py).

## fbbench.py

```
fbbench.py FILE.bench [-n 1000] [--pal] [--source]
```

Times code blocks in the emulator: `[setup]` runs once, each `[block name]` runs N times in a
FOR loop, and the empty loop is subtracted. Prints units of 2 scanlines (131 per NTSC frame)
per pass. Examples in [`bench/`](../bench/).

## fbframes.py

```
fbframes.py PROG.bas [--seconds 10] [--keys "script"] [--before "script"] [--runs N] [--pal]
```

Counts frames lost by the main loop while a key script plays the game. The program must have
exactly one `PAUSE`. Adds `INC Z9_N` before it (0.7 units), stops the program at PAUSE through
the emulator's monitor twice, `--seconds` apart, and reads TIME and the counter from memory.

## proof.py

```
proof.py LISTING [-o proof.png] [--width 120] [--scale 2] [--style paper|atari] [--wrap N] [--font F.fnt] [--no-ruler]
```

Draws the listing with ATASCII glyphs, one per byte, with a ruler, line numbers, line lengths
and the column limit.

## fontgrab.py

Captures the emulator's character set (AltirraOS) as a standard 1,024-byte `.fnt`, into
`tools/.cache/`. The screen reader and `proof.py` run it automatically the first time.

## abbrevs.py

```
abbrevs.py SYNTAX_DIR [--target atari-int|atari-fp] > docs/abbreviations.md
```

Regenerates the abbreviation table from FastBasic's grammar files (`src/syntax/` in the source
tree, `syntax/` next to a release's compiler).

## emu.py and fblib.py

The libraries the tools share.

- `emu.run(xex, keys=...)` runs a program, sends a key script and takes a screenshot.
- `emu.read_screen(png)` reads a GRAPHICS 0 screen back as text.
- `emu.Session` drives atari800's monitor: `sync('EXE_PAUSE')` stops at a label from
  `fastbasic -g`, then `var('X')`, `mem(addr, n)` and `time()` read memory exactly.

atari800 always runs as an 800XL with AltirraOS, BASIC off, artifacting off and its own config
file, so a personal atari800 setup can't change the results. Joystick on the numeric keypad,
fire on Right Ctrl, START/SELECT/OPTION on F4/F3/F2.
