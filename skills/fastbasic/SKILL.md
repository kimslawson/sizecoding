---
name: fastbasic
description: >-
  Write, debug, speed up and test FastBasic programs for the Atari 8-bit
  (dmsc's FastBasic 4.7, integer or floating point target, cross-compiler or
  IDE): language rules and traps, toolchain and linking ca65 modules, the
  frame budget and what statements cost, display lists, DLIs, players and
  missiles, POKEY, scrolling and fonts from BASIC, emulator test harnesses,
  and FujiNet networking from BASIC. For character-count golfing and the
  BASIC 10Liner contest, also use fastbasic-sizecoding. For register-level
  hardware detail or 6502 assembly, use atari8bit.
---

# FastBasic on the Atari 8-bit

FastBasic is a compiled, structured BASIC: no line numbers, no GOTO, PROCs and
blocks, 16-bit integers, and a bytecode interpreter fast enough to run a game
at 60 Hz if you respect its costs. It is not Atari BASIC or Turbo-Basic XL,
and the habits from those cause most bugs.

Everything here was measured or checked on FastBasic 4.7 in atari800 (NTSC,
800XL, AltirraOS). Where a fact comes from the grammar, the file under
`src/syntax/` is named so you can check it against your version.

## The traps that bite every program

Check every program you write or review against these before anything else.

1. **`IF C THEN S` guards exactly one statement.** In `IF C THEN A : B`, B runs
   every time. Two or more statements need a block: `IF C` ... `ENDIF` (it can
   sit on one line with colons). There is no one-line `ELSE`.
2. **Bitwise `&` `!` `EXOR` bind tighter than `*` `/` `MOD`**, which bind
   tighter than `+` `-`. `X+1&7` is `X+(1&7)`, which is `X+1`, not a wrap.
   `X*37 EXOR Y` is `X*(37 EXOR Y)`. Parenthesize anything you mean otherwise.
3. **A variable must appear in the source before its first use, top to
   bottom**, including uses inside a PROC body that runs earlier. Order of
   execution doesn't count. Fix with an earlier assignment or a `DIM`.
4. **One name space for every type.** `A`, `A$` and `A()` are the same name.
5. **Every variable is global, PROC parameters too.** A PROC that uses the
   caller's `FOR` variable moves the caller's loop.
6. **`AND` / `OR` always evaluate both sides.** No short-circuit. Nest IFs
   when the second test must not run.
7. **Integers are 16-bit signed and wrap silently.** `FOR Q=$6800 TO $6800+6143`
   overflows; loop over a count. `TIME` wraps from 32767 to -32768.
8. **`&X` is an address.** `&A$` is A$'s length byte, so data starts at `+1`;
   `&"..."+1` is a literal's first byte. A DATA string's element 0 is its length.
9. **Multiply and divide are slow.** Only `*2`, `*4` and `*256` become shifts.
   Every other multiply, every divide (`/2` too) and `MOD` cost about 5.5 units
   of a 131-unit frame. See reference/speed.md.
10. **`DLI name` (enabling a DLI) does a `PAUSE` first**, so it costs a frame.
    Never toggle DLIs in a game loop; change the data they read instead.
11. **FujiNet statements (`NOPEN` etc.) exist only in the floating point
    target**, not `-t:atari-int`. The integer target can still reach FujiNet
    through `SIO`. See reference/fujinet.md.
12. **Keep `POKE 77,0` in the main loop** of anything that uses `DLI SET`
    tables or runs unattended. It resets ATRACT; after about 9 minutes without
    a key, attract mode cycles the colors and makes the OS seed COLRSH (79),
    which `DLI SET` tables use as their line counter, from the clock.

## Where to look

| Task | Read |
|---|---|
| Syntax, precedence, names, strings, DATA, blocks, PROCs | reference/language.md |
| Compiling, targets, linking assembly, labels, ATR images, reading minimized code | reference/toolchain.md |
| Heap, DATA layout, where to put screens, fonts, players; BASIC ROM; alignment | reference/memory.md |
| Frame budget, statement costs, scheduling, lost frames, PAL | reference/speed.md |
| Display lists, scrolling, DLIs, fonts, players/missiles, collisions, sound, input | reference/hardware.md |
| Scripted emulator tests, screenshots, memory reads, profiling inside a frame | reference/testing.md |
| FujiNet `N:` networking, HTTP APIs, real-time links | reference/fujinet.md |
| Setting up the toolchain in a fresh Linux container | scripts/setup.sh |

## How to work

- **Write readable source.** Long keywords, one statement per line, comments,
  a legend of what each variable holds. Minimizers (fbp, `fastbasic -ls`)
  handle spelling; never hand-abbreviate code you will keep editing.
- **Write the hardware first, then the logic.** Right after `PAUSE`, write
  every register and shadow the display reads (scroll, LMS, player positions
  and shapes) from values computed at the end of the previous pass. Game logic
  comes after. This is what stops tearing, not luck.
- **Measure, don't estimate.** Time statements with `fbbench`, count lost
  frames with `fbframes` while a script plays (reference/testing.md). A game
  that "usually fits" its frame stutters: overruns lock onto one frame parity.
- **Don't hardcode** the display list, screen or player memory addresses. They
  move with RAM size and with BASIC or a cartridge. Read `DPEEK(560)`,
  `DPEEK(88)`, `PMADR(0)` once at startup.
- **Ask the atari8bit skill** for register bits, ANTIC/GTIA/POKEY internals and
  assembly. This skill covers how to drive them from FastBasic.

## Related tools

- [FastBasic](https://github.com/dmsc/fastbasic) by dmsc: compiler, IDE, manual.
- [fbp](https://github.com/kimslawson/fastbasic-parser): parser, minimizer and
  pretty-printer. `fbp -l` turns any minimized listing back into readable code;
  `fbp -v` flags every statement that follows `IF ... THEN` on one line.
- [sizecoding](https://github.com/kimslawson/sizecoding): the measured guide
  these numbers come from, and its Python tools (`fbbench`, `fbframes`,
  `fbsize`, `emu.py`).
