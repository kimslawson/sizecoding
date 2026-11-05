# The BASIC 10Liner contest

The [BASIC 10Liner](https://www.homeputerium.de/) contest runs every year,
usually announced around the turn of the year with a deadline in March. Rules
change a little each year: **read the current ones**. This is the 2026 (15th)
edition.

## Categories

| Category | Lines | Characters per line | Notes |
|---|---|---|---|
| PUR-80 | 10 | 80 | A game, only the BASIC the machine shipped with: FastBasic can't enter |
| PUR-120 | 10 | 120 | A game |
| EXTREME-256 | 10 | 256 | A game |
| SCHAU | 10 | 256 | Not a game: a demo, a tool, an application |
| PLUS | 10 | 256 | May load graphics, title images and music from disk |

A FastBasic entry goes in PUR-120, EXTREME-256, SCHAU or PLUS. Abbreviations
are allowed everywhere.

## Rules that shape the code

- **No machine programs in the ten lines.** No machine code in strings, no USR
  into DATA. A string of player graphics is data, not a machine program. This
  also rules out a vertical blank routine, so anything needing per-frame work
  beyond what a BASIC pass can do must be done by the hardware.
- **Compiled programs are allowed** (source must still be submitted): you submit
  the XEX on a disk image and the listing as source.
- **All code visible in the listing**: no self-modifying code or hidden
  initialization. Raw bytes inside a string literal are visible.
- **No loading from mass storage** (except PLUS). For networked entries, the
  same spirit means no code or configuration outside the listing: only public,
  keyless services the listing itself calls.
- **POKEs are allowed.**

## What counts

- FastBasic has no line numbers: a logical line is everything up to an ATASCII
  end of line ($9B), counted as written, abbreviations and all.
- A character is one byte of the listing. Inside a string literal any byte but
  `"` (written `""`) and $9B counts as one, control and inverse characters
  included.
- The FastBasic IDE edits lines up to 255 characters; a 256-character line
  needs the cross-compiler or an editor that doesn't care.
- `fbsize.py measure` prints characters, slack per line, and the one-line
  measure.

## The submission (rule 11, 2026)

A ZIP with:

1. the program on a disk or tape image,
2. a text file with the description and instructions,
3. how to start it in an emulator,
4. a screenshot (JPG or PNG) or an animated GIF,
5. a listing that proves the program is within the category's limits.

Rule 12a gives up to 0.5 bonus points for descriptions and code explanations;
12b takes up to 0.5 off for anything missing. A commented readable listing
earns its keep.

### The disk image

```sh
fastbasic -t:atari-int GAME10.BAS        # compile the PACKED listing
mkatr game.atr -b GAME10.xex             # boots the XEX directly, no DOS
```

Compile the packed listing you submit (it should match the readable source's
XEX; `fbsize.py verify --xex` checks). Boot the ATR from scratch, NTSC and PAL,
with BASIC off and on, the way a judge will.

### The listings

- **Packed listing** as text with ATASCII line ends. Name it differently from
  the readable source by more than case: macOS and Windows treat `game.bas` and
  `GAME.BAS` as one file, so packing to `GAME.BAS` overwrites your source. Use
  `GAME10.BAS`.
- **Readable listing** with comments, same statement order.
- **Proof image**: text can't show control characters and inverse video, so
  render the bytes as ATASCII glyphs:

  ```sh
  python3 tools/proof.py GAME10.BAS -o proof.png                 # black on white
  python3 tools/proof.py GAME10.BAS -o proof.png --style atari   # blue and white
  python3 tools/proof.py GAME10.BAS -o proof.png --wrap 40       # as the screen wraps it
  ```

  It draws a column ruler, line numbers, each line's length and a red line after
  the last allowed column; anything past the limit is red.

### The description

What the game is, how to start it (emulator, machine, BASIC off), the controls
including console keys, the goal, and anything not obvious from playing
(hidden modes, what the numbers on screen mean).

### Before sending

- Boot the ATR fresh, NTSC and PAL.
- Check the proof against the exact packed file you compiled.
- Read the readable listing against the packed one: same order, same
  statements.
- Reread the current year's rules.
