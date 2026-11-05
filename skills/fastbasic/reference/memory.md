# Memory

## What goes where

From low to high in a typical integer-target program:

1. The runtime and your program (segments listed in reference/toolchain.md).
2. **The heap**, right after the program: DIM arrays and string buffers, in
   the order the statements *run*. Each string variable takes 256 bytes on its
   first assignment.
3. Free RAM up to the OS screen and display list, which sit just below the top
   of RAM (or below a cartridge or BASIC).

Anything you POKE at a fixed address (a screen, a font, player/missile memory,
a table, a display list) must start **above the heap's end**, or the arrays
overwrite it, or it overwrites them. The heap starts at `__HEAP_RUN__` in the
`-g` label file; add your DIMs and strings. A startup guard catches the program
outgrowing it later (as a block: `IF ... THEN ? "HEAP" : END` would always end):

```
IF ADR(LAST) + SIZE > BUFFER    ' LAST: the last array DIMmed, SIZE: its bytes
  ? "HEAP" : END
ENDIF
```

## BASIC and cartridges

- With BASIC enabled (or a cartridge in), $A000-$BFFF is ROM. Tables written
  there silently vanish and the game crashes. Run with BASIC off (hold OPTION on
  boot, or `-nobasic` in atari800), or keep everything below $A000.
- On an XL/XE with BASIC off, RAM runs to $BFFF; the OS puts its screen at the
  top of that. Plan fixed buffers below where `GRAPHICS` will put the screen,
  or above it if you build your own display.

## Alignment rules the hardware imposes

| What | Boundary | Why |
|---|---|---|
| Display list | must not cross a **1K** boundary | ANTIC's display list counter carries only within 10 bits |
| One line's screen data | must not cross a **4K** boundary | the memory scan counter carries only within 12 bits; it wraps to the start of the same 4K block |
| Font, 128 characters (modes 2-5) | 1K aligned | CHBASE holds a page number, low bits ignored |
| Font, 64 characters (modes 6, 7) | 512-byte aligned | |
| Player/missile memory | 1K (double-line) or 2K (single-line) aligned | PMBASE |

Where screen data is allowed to cross a 4K line, compute addresses the way
ANTIC fetches them: `A & -4096 ! ((A + OFFSET) & 4095)` keeps A's 4K block and
wraps the offset inside it. This matters for anything that maps a screen
position back to memory (collision tests, reading what's under a sprite).

## Laying data out on purpose

- **DIM order is memory order.** Variables declared together in one DIM are
  consecutive words. One `MSET &W, 12, 0` clears six of them; a status display
  can read several variables as one block of bytes. Declare them in the order
  you want to read them (reverse order gives big-endian byte order when reading
  downward from the last one's high byte).
- **DATA statements, `DLI SET` routines and PROCs form one block in source
  order.** Split a table across many DATA statements and it is still one table;
  put anything else between them and it lands in the middle.
- **Strings versus DATA for big tables.** A string variable's 256-byte buffer
  means several strings sit 256 bytes apart, not end to end; tables that cross
  a page then need page arithmetic. DATA is contiguous across statements.
- **Power-of-two strides** let a mask replace a multiply: four 8-byte animation
  frames 8 bytes apart start at `ANIM & 24`.
- **`BYTEFILE` / `WORDFILE`** (cross-compiler) embed generated binaries: sprite
  sheets, fonts, precomputed sequences. Generate them with a script so the
  source of truth is editable.

## Double buffering

- **Player/missile memory**: keep two PM areas and point PMBASE (54279, $D407)
  at the one you just finished writing, right after `PAUSE`. Shape writes then
  never race the beam. In one measured game this cost about 0.1 frame per pass
  and removed all sprite tearing.
- **Screens**: two screen buffers and a display list LMS (or two display lists)
  you switch in the vertical blank. Draw into the hidden one.
- **Display list caches**: when scrolling or turning needs a different display
  list for each coarse position, build them all once and switch with one
  DPOKE (reference/hardware.md).
