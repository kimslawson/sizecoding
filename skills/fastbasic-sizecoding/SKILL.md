---
name: fastbasic-sizecoding
description: >-
  Shrink FastBasic listings for the Atari 8-bit by character count: size
  tricks with measured savings, minimizing with fbp, packing statements into
  ten lines, data and graphics stored in string literals, and the BASIC
  10Liner contest (PUR-120, EXTREME-256, SCHAU, PLUS: rules, counting,
  submission ZIP and proof image). Also proven techniques from finished
  ten-liners: scrolling, sprites, collisions, procedural worlds, sound,
  embedded neural networks, networked games. Use with the fastbasic skill.
  Not for byte-count intros in 6502 assembly (use atari8bit).
---

# Sizecoding FastBasic

Sizecoding here means making a FastBasic **listing** short, usually to fit the
BASIC 10Liner contest: ten lines of 120 (PUR-120) or 256 (EXTREME-256, SCHAU,
PLUS) characters, no machine code. Character count is what's judged, and a
ten-liner still has to run every frame on time, so every trick has two prices:
characters and time.

Load the **fastbasic** skill too. Its traps (one-statement `IF ... THEN`,
precedence, declare-before-use) and its speed numbers are what these tricks
are built on.

## The rules that matter most

1. **Never abbreviate by hand.** Keep a readable, commented source; a minimizer
   spells. `fbp -O` beat FastBasic's own `-ls` by 21 to 33 characters on
   hand-golfed PUR-120 games, with a byte-identical XEX.
2. **Precedence is free characters.** `&` `!` `EXOR` bind tighter than `*` `/`,
   which bind tighter than `+` `-`: `I+U&B` needs no parentheses. It cuts both
   ways: `X+1&7` is `X+1`.
3. **Comparisons are numbers.** `F=A>B` replaces a 15-character IF/ELSE.
   `K=K+(B>9)*7` replaces an IF. `-(c)&k` is the same value as `(c)*k`, one
   character longer and about 3 units faster.
4. **Functions take a bare argument**: `PEEK 712`, `STICK 0`, `RAND 10`.
5. **27 one-letter names** (`A`-`Z`, `_`), given to the most used variables.
   Labels (PROC, DATA, DLI) have their own name space.
6. **Strings are the data segment.** Any byte but `"` and $9B in a literal costs
   one character; `&"..."+1` addresses a literal with no variable.
7. **The OS already did the work.** Patch its display list; the runtime already
   silenced POKEY; every variable already starts at 0.
8. **Speed is a budget.** 131 units per NTSC frame. A saving that loses frames
   isn't a saving: measure with `fbframes`.
9. **Multiply and divide are the frame-killers.** Only `*2`, `*4`, `*256` are
   shifts. Spend characters on shifts and tables where the frame is tight.
10. **Packing is its own problem.** A statement can't split across lines, so
    line ends are where characters die. Measure the one-line length first.
11. **Try ideas as variants, not edits**, keep the ones that measure better, and
    record the ones that didn't, with numbers.

## Where to look

| Task | Read |
|---|---|
| The catalogue: before, after, characters saved under fbp and `-ls` | reference/size-tricks.md |
| Fitting a minimized program into ten lines; reordering safely | reference/packing.md |
| Readable source, variants, generators, measuring, history | reference/workflow.md |
| Contest categories, what counts, the ZIP, the proof image, the disk | reference/tenliner.md |
| Tables, weights, graphics and big data inside a listing | reference/data.md |
| How finished ten-liners did scrolling, sprites, physics, worlds, sound, AI, networking | reference/techniques.md |

## The loop

```sh
python3 tools/fbsize.py min game.bas -o GAME.min      # fbp -O, and check the XEX is identical
python3 tools/fbsize.py measure GAME.min              # the one-line "measure"
python3 tools/fbframes.py game.bas --keys "..."       # 0 lost frames, every scenario
python3 tools/fbsize.py pack GAME.min -o GAME10.BAS   # first-fit into lines
python3 tools/fbsize.py verify GAME.min GAME10.BAS --xex
python3 tools/proof.py GAME10.BAS -o proof.png
```

Tools are in [sizecoding](https://github.com/kimslawson/sizecoding)'s `tools/`
(`scripts/setup.sh` in the fastbasic skill installs everything). Every change:
measure size, measure speed, check behavior, pack, verify, commit with the
numbers in the message.

## Before you start a ten-liner

- **Budget first.** Estimate characters per subsystem (setup, generator, main
  loop, input, display, sound) against 1,200 or 2,560 minus packing waste
  (10 to 40 characters per line). If the core doesn't fit in about two thirds,
  cut scope now, not after polish.
- **Prototype the expensive part first** and measure its frame cost. If the
  idea needs 20 times the frame budget, find a design that lets the hardware do
  the per-frame work (reference/techniques.md has several).
- **Decide priorities**: frame-perfect, or small. A good default is "every
  frame on time, then as small as possible," with any exception written down.
