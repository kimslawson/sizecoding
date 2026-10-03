# 1. The contest

The [BASIC 10Liner](https://www.homeputerium.de/) contest runs every year, usually announced
around the turn of the year with a deadline in March. The rules change a little from year to
year, so read the current ones. What follows is the 2026 (15th) edition, summarized in
[this announcement](https://www.callapple.org/programming/15th-annual-basic-10-liner-programming-contest-begins/).

## Categories

| Category | Lines | Characters per logical line | Notes |
|---|---|---|---|
| PUR-80 | 10 | 80 | A game. **Only the BASIC the machine shipped with**, so FastBasic can't enter |
| PUR-120 | 10 | 120 | A game |
| EXTREME-256 | 10 | 256 | A game |
| SCHAU | 10 | 256 | Not a game: a demo, a tool, an application |
| PLUS | 10 | 256 | May load graphics, title images and music from disk |

So a FastBasic entry goes in PUR-120, EXTREME-256, SCHAU or PLUS. Abbreviations are allowed in
all of them.

## The rules that shape the code

- **"The 10 lines must not contain machine programs."** No machine code in strings, no USR
  into DATA. Everything happens in BASIC statements. (A string full of player graphics is
  data, not a machine program.)
- **"Programs may be compiled (source must still be submitted)."** This is what lets FastBasic
  in: you submit the compiled XEX on a disk image and the listing as source.
- **"All code must be visible in the listing: no self-modifying code or hidden
  initializations."** Everything the program needs is in the ten lines. Raw bytes inside a
  string literal are visible; that's fine.
- **"Loading data or program parts from mass storage devices is not allowed"** (except in
  PLUS).
- **"POKEs are allowed."** And that's half of Atari programming.

## What a "line" and a "character" are in FastBasic

FastBasic has no line numbers, so a logical line is simply one line of the listing: everything
up to an ATASCII end of line ($9B). The limit counts the characters on that line as written,
abbreviations and all. Statements are separated by `:`, and a statement can't continue onto
the next line (blocks like IF/ENDIF and DO/LOOP can).

A character is one byte of the listing. Inside a string literal that can be any byte except
`"` (written `""`) and $9B, including control characters and inverse video, each counting as
one. That is why the proof listing (below) is best shown as an image.

The FastBasic IDE edits lines up to 255 characters, so a 256-character EXTREME line needs the
cross-compiler or an editor that doesn't care.

## Measuring

Three numbers describe a listing. `tools/fbsize.py measure` prints all of them:

- **Characters**: the sum of the line lengths. What the contest looks at, line by line.
- **Slack**: what each line has left below the limit.
- **Measure**: the length of the program as if it were one line, with every line break turned
  back into a `:`. It doesn't depend on where the lines break, so it is the number to compare
  when you try an idea. A listing packed into exactly 10 lines has characters = measure − 9.

The ceiling for PUR-120 is 10 × 120 = 1,200 characters, but you never get all of it: a
statement that doesn't fit at the end of a line moves to the next one and leaves a hole. See
[Packing](06-packing.md).

## What to submit

Rule 11 of the 2026 edition asks for a ZIP with:

1. the program on a disk or tape image,
2. a text file with the program description and instructions,
3. a short description of how to start the game in an emulator,
4. a screenshot (JPG or PNG) or an animated GIF,
5. a program listing that proves the program is within the category's limits.

Rule 12a gives up to 0.5 bonus points for program descriptions and code explanations, and 12b
takes up to 0.5 off when something is missing. A commented, readable listing earns its keep.
[Submission](08-submission.md) covers how to make each piece.
