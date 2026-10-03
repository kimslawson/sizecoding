# 8. Submission

What goes in the ZIP (rule 11 of the 2026 rules, see [The contest](01-the-contest.md#what-to-submit)),
and how to make each piece with the toolchain.

## The disk image

Judges should be able to boot it and play, with no typing. FastBasic's release includes
`mkatr`, which writes an ATR whose boot sector loads an XEX directly, no DOS needed:

```sh
fastbasic -t:atari-int GAME.BAS          # the packed listing compiles to GAME.xex
mkatr game.atr -b GAME.xex               # -b: load this file at boot
```

Compile the **packed** listing, the one you're submitting, not the readable source. They should
produce the same XEX (`fbsize.py verify --xex` checks), but the packed one is what the proof
shows. Then boot the ATR in an emulator, from scratch, the way a judge will.

## The listings

- **The packed listing** as text (`GAME.BAS`, ATASCII line ends): this is the program.
- **The readable listing** with comments, in the same statement order. It's what earns the
  bonus for code explanations, and it lets a judge check what each of your 1,200 characters
  does.
- **A proof** that the lines are within the limit. A text file can't show the control
  characters and inverse video inside your strings, so make it an image:

```sh
python3 tools/proof.py GAME.BAS -o proof.png                 # black on white, 2x
python3 tools/proof.py GAME.BAS -o proof.png --style atari   # blue and white
python3 tools/proof.py GAME.BAS -o proof.png --wrap 40       # as the 40-column screen wraps it
```

Every byte is drawn as its ATASCII glyph (one glyph, one character), with a column ruler, the
line numbers, each line's length on the right, and a thin red line after the last allowed
column. Anything past the limit is drawn in red. The font is the one the emulator uses; give
`--font` any 1,024-byte Atari font file to use another.

## The description

A text file with what the game is, how to play, and what the keys do. Things judges appreciate:

- how to start it (the emulator, the machine to pick, BASIC off),
- the controls, including the console keys if you use them,
- the goal, or the absence of one if it's a toy,
- anything that isn't obvious from playing: hidden modes, what the numbers on screen mean.

## The screenshot

A PNG from the emulator, or an animated GIF if the game is about motion. atari800 saves a
screenshot with F10; with the harness, `emu.run(xex, keys=...)` returns one after a scripted
key sequence.

## Before you send it

- Boot the ATR on a fresh emulator, NTSC and PAL.
- Check the proof against the packed listing you compiled (same file).
- Read the readable listing once more against the packed one: same order, same statements.
- Read the current year's rules again. They change.
