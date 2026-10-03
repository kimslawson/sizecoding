# 4. Atari tricks

The hardware is half the game. These are the ways a ten-liner gets ANTIC, GTIA and POKEY to do
work for free, written for FastBasic. Addresses are given in decimal as you'd type them, with
the hex and the register name alongside.

## The display

### Patch the OS display list instead of building one

`GRAPHICS 0` makes the OS build a standard display list and screen. Building your own costs a
DATA statement and a few POKEs; editing the OS's costs one or two POKEs. The GR.0 list at
`D = DPEEK(560)` is:

| Offset | Bytes | Meaning |
|---|---|---|
| D+0 to D+2 | `$70 $70 $70` | 24 blank scanlines |
| D+3 to D+5 | `$42` + address | mode 2 (40-column text) with LMS: the screen address |
| D+6 to D+28 | 23 × `$02` | 23 more text lines |
| D+29 to D+31 | `$41` + address | jump and wait for vertical blank |

Useful edits:

- **Change a line's mode** by POKEing its byte. Mode 6 (`$06`, 20 columns, 4 colors from the top
  2 bits of each character) makes a big status line: `POKE D+3, 70` ($46 = mode 6 + LMS).
- **Point part of the screen anywhere in memory.** Turn a line into an LMS instruction (add
  `$40`) and the next two bytes become its address: `POKE D+6, 66` ($42), then
  `DPOKE D+7, A` shows memory from A down. The two `$02` lines whose bytes became the address
  are gone, so the screen has two fewer lines.
- **Fine scroll** by adding `$20` (VSCROL) to a run of lines (`MSET D+9, 19, 34` sets 19 lines to
  `$22`) and writing 0 to 7 into VSCROL (`POKE 54277, M`, $D405). Combined with an LMS you can
  scroll anything smoothly: LMS moves whole rows, VSCROL moves scanlines.
- **Add a display list interrupt** by setting bit 7 on a line (`$82` instead of `$02`).

### Where things are, without asking

In GRAPHICS 0 the OS puts the display list at an address ending in $20 and the screen 32
bytes later, at an address ending in $40, so the screen starts at `D+32` and row 1 at `D+72`. That replaces `DPEEK(88)`
(SAVMSC) once you already have D. Don't hardcode absolute addresses, though: where the screen
and display list end up depends on the RAM size and on BASIC or a cartridge being present.

### One fixed-point variable for coarse and fine scroll

```
F = F + Y                     ' F: scroll position, 8.8 fixed point (high byte = scanline)
IF F & -2048                  ' left 0..2047 up or down:
  A = A + (F > 0) * 80 - 40   '   move the LMS address one row, +40 or -40
  F = F & 2047                '   and wrap
ENDIF
POKE 54277, PEEK(&F + 1)      ' VSCROL = high byte, 0..7, without a /256
```

`F & -2048` is nonzero exactly when F is negative or above 2047, so one test covers both
directions. `PEEK(&F+1)` reads the high byte in 2.2 units where `F/256` takes 6.9.

### ANTIC's 4K boundary

ANTIC's display address counter only carries within its low 12 bits. When screen data runs
past an address ending in $FFF, ANTIC continues at the start of the *same* 4K block, not the
next one. The OS deals with this for its own screens: a GRAPHICS 8 screen (7,680 bytes) can't
fit in one 4K block, so the OS gives its display list a second LMS where the screen crosses the
boundary. Your own code has to deal with it whenever the memory it displays crosses a $x000
address:

- a custom display list needs an LMS on the first line past the boundary;
- coarse scrolling (moving an LMS address) can carry the displayed area across one;
- code that turns a screen position into a memory address (plotting, collision tests, reading
  what's under a player) must agree with what ANTIC actually shows.

Either keep screen data inside one 4K block, or, where it's allowed to cross, compute
addresses the way ANTIC fetches them: `A & -4096 ! ((A + offset) & 4095)` keeps A's 4K block
and wraps the offset inside it.

### Text on screen without PRINT

PRINT is slow (it goes through the OS) and needs a cursor position. POKE screen codes straight
into screen memory instead. Screen codes are not ATASCII: digits 0 to 9 are 16 to 25, letters
A to Z are 33 to 58. A hex digit B (0 to 15) is `B + 16 + (B > 9) * 7`. In mode 6 and 7, add 64,
128 or 192 to pick the color register. Hide the cursor with `POKE 752, 1`.

### A different font, or color, for part of the screen

FastBasic's DLI statement writes constants (or one DATA BYTE value per line) into hardware
registers when a display list interrupt fires:

```
DLI SET N = 4 INTO 54281      ' CHBASE ($D409) = page 4: a RAM font at $0400
POKE D + 28, 130              ' the line before gets the DLI bit ($82)
DLI N                         ' enable it
```

The OS's vertical blank copies the color and CHBASE shadows (708-712, 756) back into the
hardware every frame, so a DLI only has to change things for the lines below it and never has
to change them back. A copied ROM font needs `MOVE -8192, address, 1024` (the ROM font is at
$E000), or only 512 bytes for modes 6 and 7, which use 64 characters. Fonts must start on a 1K
boundary (512 bytes for modes 6 and 7).

A DLI without `WSYNC` can land a scanline late. If the first scanline of the changed line still
shows the old value, design for it: a glyph whose top row is blank in both fonts hides the
switch.

## Players and missiles

- `PMGRAPHICS 2` turns on double-line players (128 bytes each, every byte 2 scanlines tall);
  `PMGRAPHICS 1` single-line (256 bytes). `PMADR(n)` is player n's memory, `PMADR(-1)` the
  missiles'. In double-line mode the missiles sit 128 bytes below player 0.
- `PMHPOS n, x` is `POKE 53248 + n, x`, and 3 characters shorter. Missiles are 4 to 7.
- **Draw a shape with one MOVE** from a string: `MOVE &G$ + 1 + O * 9, P, 9` copies frame O of a
  set of 9-byte frames into the player. Pad all frames to the same height and center so one
  MOVE draws any of them without erasing.
- **A state variable can be the bitmap.** A missile byte of 3 is two pixels wide, 2 is one, 0 is
  none, so `POKE Q, K` draws the missile in whatever state K says.
- Colors are shadows: players at 704 to 707, playfield at 708 to 712 (712 is the background
  and border). POKE the shadow; the OS copies it every frame.

## Sound

- POKEY's frequency and control registers are pairs: AUDF1/AUDC1 at 53760/53761 ($D200), then
  53762/53763 and so on. `DPOKE 53760, C * 256 + F` sets both, where C's high nibble is the
  distortion (160 = $A0 pure tone, 128 = $80 noise) and its low nibble the volume.
- `SOUND voice, pitch, distortion, volume` does the same through a routine; it is about 3.7
  units against 2.1 for the DPOKE, and longer to write.
- A mask silences a sound with no IF: `DPOKE 53762, B & 34508` is the sound when B is -1 and
  silence when B is 0.
- The runtime turns sound off at startup.

## Input

- `STICK(0)` (`S.0`): bits 0 to 3 clear for up, down, left, right. 15 is centered.
  `S & 1 - S & 2 / 2` is -1, 0 or +1 vertically.
- `STRIG(0)`: 0 while the button is down.
- `PEEK(53279)` ($D01F, CONSOL): bits 0, 1, 2 clear while START, SELECT, OPTION are down. 7 is
  none. `J & 4 < OP & 4` detects OPTION going down since the last read OP.
- `KEY()` (`K.`) is nonzero when a key has been pressed.

## Housekeeping

- **Attract mode.** After about 9 minutes without a key press the OS starts cycling the colors.
  `POKE 77, 0` now and then (once a second is plenty) keeps the screen honest.
- **PAL or NTSC.** `PEEK(53268) & 10 + 50` is 50 on PAL and 60 on NTSC: GTIA's PAL register
  ($D014) reads 1 on PAL and 15 on NTSC. Use it for anything that counts seconds in jiffies.
- **Don't hardcode** the display list, screen or player addresses: they move with RAM size
  and with BASIC or a cartridge. Read them (`DPEEK(560)`, `PMADR(0)`) once, at startup.
