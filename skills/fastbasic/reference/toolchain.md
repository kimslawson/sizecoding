# Toolchain

## The cross-compiler

```sh
fastbasic -t:atari-int game.bas          # integer target: writes game.xex
fastbasic game.bas                       # default target: atari-fp
fastbasic -t:atari-int -g game.bas       # also write game.lbl (labels, segments)
fastbasic -t:atari-int -S:$2000 game.bas # start address of the program
fastbasic -t:atari-int game.bas blit.asm # link a ca65 module
```

- Build 4.7 from source: [dmsc/fastbasic](https://github.com/dmsc/fastbasic)
  at its 4.7 release (the measurements here used commit `55dc52f`, "Update to
  version 4.7 final"), then `make`; the Makefile builds the cc65 tools it
  needs. The compiler is `build/compiler/fastbasic`; `mkatr` is in `build/bin/`.
  `scripts/setup.sh` does all of this.
- If a copied release stops right after `LINK` with `can't assemble file`, set
  `FASTBASIC_HOME` to the folder holding the compiler: it looks for its linker
  configuration and libraries there.
- `-ls:120` writes FastBasic's own minimized listing (120-character lines);
  `-l` writes a long, readable listing. For minimizing, fbp `-O` does better
  (fastbasic-sizecoding).

## The label file (`-g`)

`fastbasic -g` writes a `.lbl` file with every segment's start and size and
every label. Use it to:

- find the end of the program and the heap start (`__HEAP_RUN__`),
- stop the emulator at a label from a test script (reference/testing.md),
- check that the program plus heap stays below fixed buffers (reference/memory.md).

## Linking assembly (ca65)

Machine code is not allowed in ten-liners, but in an ordinary program a short
ca65 routine is the standard way past BASIC's speed limit (a masked sprite
blitter, a sound player, a vertical blank routine).

- Pass the `.asm` file on the compiler's command line after the `.bas`. The
  compiler assembles and links it with the runtime.
- Export a label from the module and call it with `USR(@LABEL, a, b, c)`.
  `IF USR(@REDRAW, ADR(ST), B, Q) THEN ...` passes three words and tests the
  returned value. Pass a whole parameter block as one address (`ADR(ST)` of a
  WORD array) rather than many arguments.
- Assembly modules are ca65 syntax (FastBasic is built on cc65), not MADS.
- Segments in the linked program, in order: JUMPTAB, RUNTIME (the interpreter,
  about 1.3 KB for the integer target), DATA (all DATA arrays), BYTECODE (your
  program), CODE (assembly modules), then BSS and the heap. The link region runs
  up to the configured top; **the linker will not stop you from running into
  player or screen memory you placed by hand.** Check the `.lbl` sizes against
  your memory map after every build that adds data.

## Disk images

FastBasic's `mkatr` writes a bootable ATR that loads one XEX with no DOS:

```sh
mkatr game.atr -b game.xex
```

Boot it in a fresh emulator, NTSC and PAL, the way a user would.

## Reading other people's code

Minimized FastBasic (`P.`, `D.`, `I.`, `E.`, statements packed with `:`) is
unreadable by eye. `fbp -l LISTING.BAS` expands it: one statement per line,
indentation, all keywords spelled out, parentheses around function arguments,
the variable name after `NEXT`. Read that, not the packed text. `fbp -a`
produces an annotated long listing that keeps your source's comments and marks
where each short line starts.

## fbp

[fbp](https://github.com/kimslawson/fastbasic-parser) parses FastBasic with
FastBasic's own grammar files and verifies every output against the compiler.

| Flag | Output |
|---|---|
| `-l` | long, readable listing (ASCII line ends) |
| `-s` | short listing (the default): abbreviations, short names, Atari line ends |
| `-O` / `-S` | short listing with all size optimizations, verified equivalent |
| `-n N` | maximum short-listing line length (default 120) |
| `-f` | keep full variable and PROC names (needed when assembly uses the names) |
| `-v` | notes, including every statement after a one-line `IF ... THEN` |

Run `fbp -v` on readable source after edits: each note is either intended or a
bug from trap 1 in SKILL.md.

## IDE versus cross-compiler

- The Atari IDE edits lines up to 255 characters. Longer lines need the
  cross-compiler or an outside editor.
- `BYTEFILE`/`WORDFILE` and assembly linking are cross-compiler only.
- Listings for the Atari use ATASCII line ends ($9B). fbp's `-e` writes ASCII
  ends instead; most editors need that.

## A reproducible environment

`scripts/setup.sh` builds FastBasic 4.7, fbp and the sizecoding tools, and
installs atari800, Xvfb, xdotool and ImageMagick for scripted tests. Record the
exact commits you built in the project's docs, so a fresh container produces
identical XEX files.
