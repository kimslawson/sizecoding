# Driving the hardware from FastBasic

Addresses in decimal as you'd type them, with hex and register names. For what
each register bit means, see the atari8bit skill (hardware/antic.md,
gtia.md, pokey.md).

## Display lists

### Patch the OS list instead of building one

`GRAPHICS 0` builds this list at `D = DPEEK(560)`:

| Offset | Bytes | Meaning |
|---|---|---|
| D+0 to D+2 | `$70 $70 $70` | 24 blank scanlines |
| D+3 to D+5 | `$42` + address | mode 2 with LMS: the screen address |
| D+6 to D+28 | 23 x `$02` | 23 more text lines |
| D+29 to D+31 | `$41` + address | jump and wait for vertical blank (JVB) |

- In GRAPHICS 0 the list starts at an address ending in $20 and the screen 32
  bytes later, so the screen is `D+32` and row 1 is `D+72`, without asking
  SAVMSC (88).
- **Change a line's mode** by POKEing its byte: `POKE D+3, 70` ($46, mode 6 +
  LMS) turns the first row into 20 big colored characters; `71` ($47) mode 7.
- **Point a line anywhere**: make it an LMS (`POKE D+6, 66`, $42); the next two
  bytes become its address (`DPOKE D+7, A`), so two text lines disappear.
- **Fine scroll** by adding $20 (VSCROL) or $10 (HSCROL) to a run of lines
  (`MSET D+9, 19, 34`) and writing VSCROL (54277, $D405) or HSCROL (54276,
  $D404).
- **DLI**: set bit 7 of a line's byte ($82 for mode 2).
- **No JVB needed**: if the list runs off the bottom into zero bytes, each `$00`
  is one blank scanline, and the OS vertical blank reloads the list pointer
  from its shadow (560) every frame anyway. Overwriting the JVB with two more
  instructions is legal.
- `GRAPHICS` builds a new list and resets CHBAS (756) to $E0. Disable any DLI
  first and redo your patches afterwards.

### Scrolling

- **8.8 fixed point for coarse plus fine.** Keep one position F where the high
  byte is the scanline offset:

  ```
  F = F + Y
  IF F & -2048                  ' left 0..2047 in either direction
    A = A + (F > 0) * 80 - 40   '   move the LMS one row (+40 or -40)
    F = F & 2047
  ENDIF
  POKE 54277, PEEK(&F + 1)      ' VSCROL = high byte, no divide
  ```

- **A display list per coarse position (a cache).** For two-axis scrolling over
  a big map, give every map row its own LMS line, and build one display list per
  horizontal coarse position, each in its own 256-byte page. A short fixed
  header ends in a JMP ($01 + address) into the cache; one `DPOKE` of that
  address picks both the list (horizontal coarse position) and the row in it
  (vertical coarse position). Fine scroll is HSCROL and VSCROL. Per frame that's
  one DPOKE and two POKEs, and the values come from tables, recomputed only when
  the camera moves.
- **Write the list pointer into ANTIC too.** When switching between lists,
  `DPOKE 54274, X` (DLISTL, $D402) as well as `DPOKE 560, X`. The OS copies the
  shadow only at the next vertical blank, while HSCROL changes at once, so
  writing only the shadow shows one frame of new fine scroll with old coarse
  scroll: a jitter each time the view crosses a coarse step.
- **Turning a static view is scrolling.** If the camera never moves, all it can
  see is a cylindrical panorama: render it once (slowly, in BASIC) with one
  column per angle, and turning becomes horizontal scrolling across a cache of
  display lists. Hardware does the per-frame work.
- **Boundaries** (reference/memory.md): no display list across 1K, no line's
  data across 4K. With HSCROL on, ANTIC fetches 48 bytes per normal-width line,
  so plan row strides for that.
- In GTIA modes (9 to 11), **HSCROL must be even**: an odd value regroups the
  4-bit pixels and the colors come out wrong.

## Text and fonts

- **Screen memory beats PRINT.** POKE screen codes (digits 16-25, letters 33-58)
  straight into the screen: 0.9 units against about 5.9 for POSITION + PRINT.
- **Mode 6 and 7 color** comes from the top 2 bits of each byte: add 64, 128 or
  192 to pick a color register. A hex digit B is `B + 16 + (B > 9) * 7`.
- **A title from a string literal**: make the first list line mode 7 + LMS and
  point it at `&"..."+1` (20 bytes of screen codes). No screen writes at all.
- **Text in a player**: a player at normal width is 2 text columns wide, and the
  OS's left margin leaves the first 2 columns empty. Copy ROM glyphs into player
  memory: the glyph of ATASCII character c in the ROM font ($E000) is at
  `c * 8 - 8448` (that is (c - 32) * 8 + 57344, written as a negative number).
- **A RAM font**: `MOVE -8192, ADDR, 1024` copies the ROM font ($E000), or 512
  bytes for modes 6 and 7 (64 characters). Point CHBAS (756) at its page, or
  CHBASE (54281, $D409) from a DLI for part of the screen.
- **Tall characters**: give two consecutive text lines the *same* LMS address,
  and switch CHBASE between them with a DLI, to a font holding the glyphs' top
  rows and then one holding their bottom rows. Write a character once, it shows
  two lines tall. Three or four slices make taller text.
- **Animate many characters with one MOVE**: if every copy of an object on
  screen uses the same characters, one MOVE into the font animates all of them
  at once. Cheaper than players for anything that scrolls with the playfield.

## Display list interrupts with `DLI SET`

```
DLI SET N = 4 INTO 54281              ' a constant into CHBASE
DATA CS() BYTE = 224, 4, 6, 224
DLI SET T = CS INTO 54281             ' element k on the k-th DLI of the frame
DLI SET U = CS INTO 54281, PF INTO 53270   ' several stores per DLI
DLI T                                 ' enable (does a PAUSE first: costs a frame)
DLI                                   ' disable
```

- The table form counts lines in COLRSH (79, $4F), which the OS sets to 0 each
  vertical blank. **In attract mode the OS sets COLRSH from the clock instead**,
  so the count starts at the wrong place and the DLI reads past its table.
  Reset the attract timer ATRACT (77, $4D) with `POKE 77, 0` in the main loop.
- The other way round, on purpose: `POKE 79, X` from BASIC mid-frame shifts the
  table index for the lines below the beam until the next frame, a cheap
  "shatter" effect, and `POKE 77, 128` forces attract mode now.
- **During SIO transfers** the OS sets CRITIC and skips the second stage of the
  vertical blank, so COLRSH and CHBAS aren't refreshed. The display can glitch
  while loading or networking; disable the DLI around blocking I/O if it
  matters.
- The OS vertical blank copies the color and CHBAS shadows (704-712, 756) to the
  hardware every frame, so a DLI only changes things for the lines below it and
  never has to change them back.
- **Enabling a DLI costs a frame** (the statement compiles to `PAUSE 0` first,
  `dli.syn`). Never toggle in the loop; change the table it reads (a hit flash
  is a table write).
- In 4.7 a `DLI SET` routine loads its first value, does `STA WSYNC`, then
  stores (`dli.syn`), so the first store lands at the start of the next
  scanline; further stores on the same DLI follow right after. Glyphs whose
  top row is blank in both fonts are cheap insurance against a switch that
  lands a line off.
- `DLI SET` routines are laid out among DATA and PROCs in source order
  (reference/language.md), and a `DLI SET` that reads a table must come after it.
- A DLI on a JMP line fires.

## Players and missiles

- `PMGRAPHICS 2`: double-line (128 bytes per player, each byte 2 scanlines);
  `PMGRAPHICS 1`: single-line (256 bytes). `PMADR(n)` is player n's memory,
  `PMADR(-1)` the missiles'. In double-line mode the missiles sit 128 bytes
  below player 0. `PMGRAPHICS` doesn't clear player memory, and real hardware
  powers up with random RAM.
- `PMHPOS n, x` sets horizontal position (missiles are 4 to 7). One
  `MOVE ADDR, 53248, 8` sets all eight positions at once from a table.
- **One MOVE draws any frame** of a set of equal-height frames from a string:
  `MOVE &G$ + 1 + O * 9, P, 9`. Pad frames to the same height and visual center
  (compute centroids when designing them) so no erase is needed.
- **A state variable can be the bitmap**: missile byte 3 is two pixels wide, 2
  one pixel, 0 nothing, so `POKE Q, K` draws whatever state K holds.
- **Missiles as one sprite**: four missiles side by side make a 4-color-clock,
  per-missile-positioned object; two widths per missile give a shape.
- **Holes in a player** read as the background: eyes, windows, cutouts without
  extra characters or sprites.
- **PRIOR** (623 shadow, 53275 $D01B): set playfield priority above players and
  sprites hide behind terrain on their own.
- **Fifth player** (PRIOR bit 4): missiles draw in PF3's color, so the four
  missiles become one more player-colored object.
- Colors are shadows: players 704-707, playfield 708-711, background/border 712.
- In ANTIC mode 2, a set text pixel takes COLPF1's luma over whatever is under
  it, players included, so text shows through a black player.

## Collisions

- GTIA's collision registers (missile-to-playfield $D000-$D003, player-to-
  playfield $D004-$D007, and so on) latch until `POKE 53278, 0` (HITCLR). They
  report **the frame just displayed**, not where your variables are now.
- **Colors as collision classes.** Draw walls in PF0, bumpers in PF1, one-way
  surfaces in PF2: the collision bits then say *what* was hit, with no lookup.
- **A ball of four missiles, one per quadrant**: which quadrants touched gives an
  8-direction surface normal, with four PEEKs and no geometry. Reflect when
  moving into the surface (`v . n < 0`), always nudge out along n.
- **Two frames of contact**: if collisions are read every other frame, an object
  can be two frames deep and both halves can light up. Undo two frames of
  velocity and resolve ambiguity with the velocity.
- **One-way surfaces by normal, not velocity sign**: decide by which side the
  contact is on, or an object under the surface gets trapped when it starts to
  fall.

## GTIA modes

- GTIA mode 10 (GRAPHICS 10): blank lines and the border show register 704, not
  COLBK. A sky gradient there is DLIs writing 704.
- ANTIC mode 2 under GTIA 10 shows each character as 2 fat pixels in any of the
  9 colors.
- One LMS per scanline is allowed and works; players draw over GTIA pixels.

## Sound

- POKEY frequency and control registers are pairs: AUDF1/AUDC1 at 53760/53761
  ($D200), then 53762/53763 and so on. `DPOKE 53760, C * 256 + F` sets both in
  2.1 units; `SOUND` takes 3.7. C's high nibble is the distortion ($A0 = 160
  pure tone, $80 = 128 noise), its low nibble the volume.
- **A mask silences without an IF**: `DPOKE 53762, B & 34508` is the sound when
  B is -1 and silence when B is 0.
- **POKEY keeps playing what it was told.** Write registers only when a value
  changes; precompute pitch tables at boot. The per-frame part of a sound
  engine should be counters and compares.
- AUDCTL (53768, $D208) joins channels for 16-bit pitch and picks clocks.
- The runtime silences POKEY at startup.

## Input

- `STICK(0)`: bits 0 to 3 clear for up, down, left, right; 15 centered.
  `S & 1 - S & 2 / 2` is -1, 0, +1 vertically. `(S & 8 = 0) - (S & 4 = 0)` is
  the faster horizontal form (no divides).
- `STRIG(0)`: 0 while the button is down.
- CONSOL `PEEK(53279)`: bits 0, 1, 2 clear for START, SELECT, OPTION; 7 none.
  Edge detection: `J & 4 < OP & 4` is OPTION going down since the last read OP.
- `KEY()` is nonzero after a key press. Hold OPTION at power-on to disable BASIC.

## Housekeeping

- `POKE 77, 0` regularly (attract mode).
- Read `DPEEK(560)`, `DPEEK(88)`, `PMADR(0)` once at startup; never hardcode.
- Test NTSC and PAL (reference/speed.md).
