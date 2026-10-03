# 3. Size tricks

Each trick below is a `trick(...)` entry in [`tests/tricks.py`](../tests/tricks.py), which
compiles the before and after versions, minimizes both, and (with `--run`) runs both in the
emulator to check they leave the same values behind. The **saves** column is the difference in
minimized characters: first with fbp `-O`, then with FastBasic's `-l:min`. A 0 under fbp means
fbp already does it for you; under `-l:min` you have to write it that way yourself.

One trick failed its behavior check while this page was being written: `X=X+1&7` looks like a
wrap to 0..7 and is actually `X+1`, because `&` binds tighter than `+`. The test caught it; the
version below has the parentheses. Run the tests.

```sh
python3 tests/tricks.py          # sizes (FastBasic + fbp)
python3 tests/tricks.py --run    # sizes and behavior (Linux + atari800)
```

## Let the tools spell

| Trick | Before | After | fbp | -l:min |
|---|---|---|---|---|
| Bare function argument | `K = PEEK(712)` | `K = PEEK 712` | 0 | 2 |
| One-statement block | `IF A=1 : B=2 : ENDIF` | `IF A=1 THEN B=2` | 0 | 2 |
| ELIF | `ELSE : IF A=3 ... ENDIF : ENDIF` | `ELIF A=3 ... ENDIF` | 0 | 5 |
| Drop `<>0` | `IF A<>0 THEN B=1` | `IF A THEN B=1` | 0 | 2 |
| Redundant parentheses | `K = (J & 4) / 4` | `K = J & 4 / 4` | 0 | 2 |
| PRINT separators | `PRINT "A="; A` | `PRINT "A=" A` | 0 | 1 |
| Negative constants | `K = X & 65520` | `K = X & -16` | 0 | 0 |

All of these compile to identical code. The minimizer handles the constants either way; fbp
handles the rest. If your pipeline is `-l:min`, adopt them as habits.

## Statements

| Trick | Before | After | fbp | -l:min |
|---|---|---|---|---|
| INC | `X = X + 1` | `INC X` | 1 | 1 |
| INC, two-letter name | `QD = QD + 1` | `INC QD` | 2 | 2 |
| DEC | `X = X - 1` | `DEC X` | 1 | 1 |
| ABS | `IF X<0 THEN X=-X` | `X = ABS X` | 6 | 6 |
| DO/LOOP | `REPEAT ... UNTIL 0` | `DO ... LOOP` | 1 | 1 |
| No startup SOUND | `SOUND` (first statement) | (nothing) | 3 | 3 |
| MOVE instead of a loop | `FOR I=0 TO 8 : POKE 1600+I, PEEK(1536+I) : NEXT I` | `MOVE 1536, 1600, 9` | 18 | 19 |
| MSET a run of variables | `A=0 : B=0 : C=0 : D=0` | `MSET &A, 8, 0` | 6 | 6 |
| One DPOKE for two bytes | `POKE 1536,V : POKE 1537,C` | `DPOKE 1536, C*256+V` | 3 | 3 |

- `INC X` is also faster (0.7 units against 1.6), and like an assignment it creates the
  variable.
- The runtime calls the same sound-off routine as a bare `SOUND` before your first statement,
  so the statement does nothing.
- `MSET &A` needs A, B, C and D at consecutive addresses: declare them together in one DIM
  (see [FastBasic for sizecoders](02-fastbasic-for-sizecoders.md#names)). If the DIM is
  needed anyway, the MSET is nearly free.
- `DPOKE` writes the low byte first. `C*256` compiles to a byte shift, so the DPOKE takes only
  a little longer than the two POKEs (2.5 units against 2.1). It pays off for register pairs:
  POKEY's AUDF/AUDC, two display list bytes, a pointer.

## Conditions as arithmetic

| Trick | Before | After | fbp | -l:min |
|---|---|---|---|---|
| Boolean assignment | `IF A>B : F=1 : ELSE : F=0 : ENDIF` | `F = A > B` | 15 | 15 |
| Conditional add | `IF B>9 THEN K=K+7` | `K = K + (B>9)*7` | 1 | 1 |
| Toggle 0/1 | `IF F=0 : F=1 : ELSE : F=0 : ENDIF` | `F = 1 - F` | 15 | 15 |
| Toggle 0/-1 | `IF F=0 : F=-1 : ELSE : F=0 : ENDIF` | `F = -1 - F` | 15 | 15 |
| Count down, stop at 0 | `IF E>0 THEN DEC E` | `E = E - (E>0)` | 2 | 2 |
| Clamp at 0 | `IF E<0 THEN E=0` | `E = E & -(E>0)` | 0 | 0 |
| Mask instead of multiply | `K = (B>9)*7` | `K = -(B>9) & 7` | -1 | -1 |

- A comparison is 1 or 0, so `(c)*k` is k or 0. `-(c)` is -1 or 0, a mask: `-(c)&k` is the same
  value, one character longer, and almost 3 units faster (no multiply). Use whichever your
  budget is short of.
- **Use masks as flags.** A flag that is 0 or -1 (all bits set) can select with `&`:
  `X & F` is X or 0, `F - V & F` is 0 or -1-V (which POKEs as 255-V). Toggle it with
  `F = -1 - F`.
- The clamp saves nothing on its own but removes a branch, which keeps a frame's timing
  constant. Combined with something else in the same expression it usually wins.

## Bits instead of comparisons

| Trick | Before | After | fbp | -l:min |
|---|---|---|---|---|
| Two signs at once | `IF L<0 OR R<0 THEN K=0` | `IF L ! R < 0 THEN K=0` | 3 | 3 |
| Range 0..2^n-1 | `IF X<0 OR X>127 THEN K=0` | `IF X & -128 THEN K=0` | 4 | 4 |
| Wrap 0..2^n-1 | `INC X : IF X>7 THEN X=0` | `X = (X+1) & 7` | 6 | 6 |
| MOD by a power of 2 | `K = X MOD 8` | `K = X & 7` | 2 | 2 |
| Complement a byte | `POKE J, 255-V` | `POKE J, -1-V` | 1 | 1 |
| Joystick Y, -1/0/+1 | IF/ELIF/ELSE on `S&1`, `S&2` | `DY = S&1 - S&2/2` | 28 | 28 |
| Joystick X, -1/0/+1 | IF/ELIF/ELSE on `S&4`, `S&8` | `DX = S&4/4 - S&8/8` | 26 | 26 |

- `L ! R` has its sign bit set if either has, so one comparison tests both.
- `X & -128` keeps only the bits above 127: it is nonzero exactly when X is outside 0..127,
  negative numbers included (their high bits are set). Any power of two works.
- `X & 7` equals `X MOD 8` for X ≥ 0, and it's also about 3 units faster.
- `STICK` clears bit 0 for up, 1 for down, 2 for left, 3 for right. `S&1-S&2/2` is 0-1 = -1 for
  up, 1-0 = +1 for down and 1-1 = 0 otherwise, diagonals included, with no parentheses thanks
  to precedence. The X version uses two divides (about 11 units together); when that's too
  slow, `(S&8=0)-(S&4=0)` is 4 characters longer and faster.

## Data

| Trick | Before | After | fbp | -l:min |
|---|---|---|---|---|
| Bytes in a string | `DATA X() BYTE = 24,60,126,...` + `MOVE ADR(X), ...` | `X$ = "..."` + `MOVE &X$+1, ...` | 18 | 18 |
| Literal address | `G$ = "ABCDEFGH" : MOVE &G$+1, 1536, 8` | `MOVE &"ABCDEFGH"+1, 1536, 8` | 6 | 6 |
| Repeated constant | `POKE 53248,A : POKE 53249,B : ...` (4 times) | `H = 53248 : POKE H,A : POKE H+1,B : ...` | 2 | 2 |

- A byte in a string literal costs one character; in DATA it costs its digits plus a comma. Only
  `"` and $9B can't be typed into a string; write a `"` as `""` and splice $9B (or a trailing
  zero) in with a `$9B` after the closing quote.
- One string can hold several tables: player shapes, a text line, character glyphs. Point at the
  parts with `&G$+1+offset`. A string used once doesn't even need a name: `&"..."`.
- **Tables can share entries.** A cosine table is a sine table shifted by a quarter turn, so
  `DATA X() = 0,3,3,3,0,-3,-3,-3, 0,3` (8 headings plus 2 repeats) gives the horizontal step as
  `X(h)` and the vertical as `-X(h+2)`, instead of `X((h+6)&7)` twice.
- A constant in a variable pays off once it's used often enough: a 5-digit constant used 4 times
  saves 2. fbp's `-S` does this automatically when it helps.

## Names

- **Give one-letter names to the variables you use most.** A two-letter name costs one
  character at every use, so it belongs on a variable that appears twice (its DIM and one use),
  not one that appears ten times. fbp `-O` renames by frequency for you; with `-l:min`, do it by
  hand.
- **`_` is the 27th one-letter name.** Easy to forget, free to use.
- **Labels don't use up letters.** PROC, DATA and DLI names are a separate name space, so when
  all 27 letters are taken by variables, a DLI or a DATA table can still have a one-letter name
  that a variable also uses (`DLI SET N` next to a variable `N`). Mind the catches in
  [FastBasic for sizecoders](02-fastbasic-for-sizecoders.md#names).
- **Reuse variables across phases of a frame.** A temporary that is dead by the time another job
  runs can be that job's temporary too: the stick reading, the missile target and the status
  digit can all be J. Write down which variable holds what, when, at the top of the readable
  source; you'll need it.

## Control flow

- **Make restart and boot the same code.** Put the start-of-game setup in the main loop, behind
  `IF (restart key pressed) OR Q=0`, where Q is any variable that is still 0 on the first pass
  and set by the setup. Every variable starts at 0, so the first pass runs the setup for free.
  Pick a Q that can never return to 0, or the game will restart on its own. (A clock reference
  that wraps can hit exactly 0 once in a while. `H = TIME ! 1` keeps it odd, and adding an even
  number keeps it odd forever.)
- **One loop.** `DO ... PAUSE ... LOOP` with everything inside, jobs chosen by `TIME` (see
  [Speed](05-speed.md)). Separate title screens and game-over loops cost statements.
- **ELIF chains instead of nested IFs**, when exactly one of several things should happen: an
  ELIF arm needs no ENDIF of its own.
- **PROC only when it's called from several places**: `PROC P` + `ENDPROC` + `@P` per call
  costs more than inlining one or two copies of a short body.

## Readable source, small listing

None of this needs to make the source unreadable. The readable version keeps its comments,
indentation and spaces, and the minimizer strips them. Size work happens in the *statements*
and *expressions*, not in the spelling.
