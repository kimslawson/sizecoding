# Size tricks

The **fbp** and **-ls** columns are minimized characters saved under fbp `-O`
and under FastBasic's `-ls`. A 0 under fbp means fbp already does it for you;
with `-ls` you write it that way yourself. The catalogue tables are checked
against the compiler by `tests/tricks.py` in the sizecoding repo (`--run` also
checks behavior in the emulator). Time costs are units of 2 scanlines, 131 per
NTSC frame.

## Let the tools spell

| Trick | Before | After | fbp | -ls |
|---|---|---|---|---|
| Bare function argument | `K = PEEK(712)` | `K = PEEK 712` | 0 | 2 |
| One-statement block | `IF A=1 : B=2 : ENDIF` | `IF A=1 THEN B=2` | 0 | 2 |
| ELIF | `ELSE : IF A=3 ... ENDIF : ENDIF` | `ELIF A=3 ... ENDIF` | 0 | 5 |
| Drop `<>0` | `IF A<>0 THEN B=1` | `IF A THEN B=1` | 0 | 2 |
| Redundant parentheses | `K = (J & 4) / 4` | `K = J & 4 / 4` | 0 | 2 |
| PRINT separators | `PRINT "A="; A` | `PRINT "A=" A` | 0 | 1 |
| Negative constants | `K = X & 65520` | `K = X & -16` | 0 | 0 |

Spacing: a space is needed only where a name would run into a word:
`I.A=1T.` but `I.A T.` (otherwise `AT` is a variable). Numbers are rewritten in
their shortest form; anything from 32768 up is shorter negative.

## Statements

| Trick | Before | After | fbp | -ls |
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

`INC X` is also faster (0.7 against 1.6) and creates the variable. `MSET &A`
needs the variables consecutive: declare them together in one DIM. `C*256` is a
shift, so a DPOKE of a register pair costs about what two POKEs do.

## Conditions as arithmetic

| Trick | Before | After | fbp | -ls |
|---|---|---|---|---|
| Boolean assignment | `IF A>B : F=1 : ELSE : F=0 : ENDIF` | `F = A > B` | 15 | 15 |
| Conditional add | `IF B>9 THEN K=K+7` | `K = K + (B>9)*7` | 1 | 1 |
| Toggle 0/1 | IF/ELSE | `F = 1 - F` | 15 | 15 |
| Toggle 0/-1 | IF/ELSE | `F = -1 - F` | 15 | 15 |
| Count down, stop at 0 | `IF E>0 THEN DEC E` | `E = E - (E>0)` | 2 | 2 |
| Clamp at 0 | `IF E<0 THEN E=0` | `E = E & -(E>0)` | 0 | 0 |
| Mask instead of multiply | `K = (B>9)*7` | `K = -(B>9) & 7` | -1 | -1 |

- **Masks as flags.** A flag that is 0 or -1 selects with `&`: `X & F` is X or
  0. `F - V & F` (that is `F - (V & F)`) is 0 or -1-V, which POKEs as 255-V: one
  expression for "leave it" or "complement it".
- **One mask, several uses.** `B = J & 1 - 1` is -1 when the stick's up bit is
  clear, else 0. Then `I = I + U & B`, `Y = Y + V & B` and
  `DPOKE 53762, B & 34508` add thrust on both axes and switch its sound on or
  off, with no IF at all.
- **Fold two tests into one comparison.** With K a state (3 held, 2 released)
  and B a button bit (1 released), `K & B` is 1 only when held-and-released;
  `K = K - B & K` steps 3 to 2 on release and leaves everything else alone.
  `IF K + B = 0` is "no missile and fire down" when both are 0 in that case.
- The clamp saves nothing alone but removes a branch: constant time per frame.

## Bits instead of comparisons

| Trick | Before | After | fbp | -ls |
|---|---|---|---|---|
| Two signs at once | `IF L<0 OR R<0 THEN K=0` | `IF L ! R < 0 THEN K=0` | 3 | 3 |
| Range 0..2^n-1 | `IF X<0 OR X>127 THEN K=0` | `IF X & -128 THEN K=0` | 4 | 4 |
| Wrap 0..2^n-1 | `INC X : IF X>7 THEN X=0` | `X = (X+1) & 7` | 6 | 6 |
| MOD by a power of 2 | `K = X MOD 8` | `K = X & 7` | 2 | 2 |
| Complement a byte | `POKE J, 255-V` | `POKE J, -1-V` | 1 | 1 |
| Joystick Y, -1/0/+1 | IF/ELIF/ELSE on `S&1`, `S&2` | `DY = S&1 - S&2/2` | 28 | 28 |
| Joystick X, -1/0/+1 | IF/ELIF/ELSE on `S&4`, `S&8` | `DX = S&4/4 - S&8/8` | 26 | 26 |

- `F & -2048` is nonzero exactly when F left 0..2047 in either direction: one
  test for both scroll directions.
- Rotation from two stick bits: `O = (O + (J&8=0) - (J&4=0)) & 7`, or
  `O = (O + J&4/4 - J&8/8) & 7`, 4 characters shorter and about 7.5 units
  slower (two divides). Pick by the frame it runs on.
- The joystick X form uses two divides (about 11 units); `(S&8=0)-(S&4=0)` is 4
  characters longer and fast.

## Speed for characters

The other direction: a few characters more for a lot less time.

| Trick | Before | After | fbp | -ls |
|---|---|---|---|---|
| x8 from shifts | `K = R * 8` | `K = R * 4 * 2` | -2 | -2 |
| x16 from shifts | `K = R * 16` | `K = R * 4 * 4` | -1 | -1 |
| x3 from a shift and an add | `K = R * 3` | `K = R * 2 + R` | -2 | -2 |
| x40 | `K = R * 40` | `K = (R * 4 + R) * 4 * 2` | -7 | -7 |
| Running pointer | `FOR J=0 TO 7 : POKE 1536+J*8,1 : NEXT J` | `A=1536 : FOR J=0 TO 7 : POKE A,1 : A=A+8 : NEXT J` | -6 | -6 |

- `K = PEEK(&F + 1)` instead of `F / 256`: 3 characters more, 4.7 units less.

`K = ((R + M) & -8) * 5` is "row times 40" from a scanline count with one
multiply and no divide: `&-8` rounds down to row times 8, and `*5` makes it row
times 40. Precedence drops the outer parentheses: `(R+M)&-8*5`.

## Data

| Trick | Before | After | fbp | -ls |
|---|---|---|---|---|
| Bytes in a string | `DATA X() BYTE = 24,60,126,...` + `MOVE ADR(X), ...` | `X$ = "..."` + `MOVE &X$+1, ...` | 18 | 18 |
| Literal address | `G$ = "ABCDEFGH" : MOVE &G$+1, 1536, 8` | `MOVE &"ABCDEFGH"+1, 1536, 8` | 6 | 6 |
| Repeated constant | `POKE 53248,A : POKE 53249,B : ...` (4x) | `H = 53248 : POKE H,A : POKE H+1,B : ...` | 2 | 2 |

- One string can hold every table: player frames, a text line, glyphs. Point at
  parts with `&G$+1+offset`.
- **Tables can share entries.** A sine table 2 entries longer gives cosine as
  `-X(h+2)` instead of `X((h+6)&7)` twice: +4 data, -7 code, and faster.
- A constant in a variable pays once it's used often enough: a 5-digit constant
  used 4 times saves 2. fbp `-S` does this when it helps.
- More in reference/data.md.

## Names

- **One letter for the most used names**: a two-letter name costs one character
  per use, so it belongs on a variable used twice, not ten times. fbp `-O`
  renames by frequency.
- **`_` is the 27th letter.**
- **Labels reuse letters.** A DATA table or DLI can share a variable's letter
  (`DATA D()` next to a variable D), freeing a letter for a variable. Mind the
  catches: `&D` and `ADR(D)` give the DATA address, `D(n)` reads an array
  variable first, and `D(0)=` can create a stray variable.
- **Reuse temporaries across phases of a frame**: the stick reading, a target
  address and a status digit can all be J if they're never alive at once. Write
  the legend at the top of the readable source.
- **A numeric G can't sit next to G$**; plan names before the data string takes
  a letter.

## Memory layout as code

- **Consecutive variables are a block.** `DIM C, W, S, A` makes 8 consecutive
  bytes; a hex status line can then print any digit J of four variables with
  one expression over `PEEK(&A + 1 - J / 2)`. Declaring them in reverse order
  makes the byte order big-endian reading downward, which saved 3 characters
  over swapping bytes.
- **Extend the DIM to clear more with one MSET.** Adding I, Y, F to the DIM
  after A let one `MSET &W, 12, 0` zero six variables on restart: 9 characters
  in total, against 12 for `I=0:Y=0:F=0` alone.
- **Never-written zeros.** DIM clears arrays and every variable starts at 0: a
  buffer whose first entries should be "nothing yet" needs no MSET if the
  program never writes them.
- **Accumulators that never reset.** `U = U * 2 + (Z > 128)` stored as a byte
  every 8 steps keeps only its low byte; old bits shift out, so U needs no
  reset between uses.
- **Store offset values.** Biases stored +128 (bytes can't be negative) cost
  nothing if the threshold moves instead: `Z > 128`, not `Z - 128 > 0`.

## Control flow

- **Restart is boot.** Put game setup inside the main loop behind
  `IF (restart key) OR Q = 0`, with Q any variable still 0 on the first pass and
  set by the setup. Pick a Q that can never return to 0: a clock reference that
  wraps can hit 0. `H = TIME ! 1` keeps it odd, and adding an even step keeps it
  odd forever.
- **One loop**: `DO ... PAUSE ... LOOP`, jobs chosen by `TIME`, no separate
  title or game-over loops. A title that accepts any input is one test.
- **ELIF chains** instead of nested IFs: one ENDIF for all arms.
- **PROC only for code called from several places.** `PROC P`, `ENDPROC` and
  `@P` per call cost more than inlining one or two copies.
- **Hide cheap work inside a test you need anyway.** An OPTION-toggle edge test
  inside the "any console key down" test that restart already needs costs one
  store per frame (`OP = J`) when no key is held.
- **Only record what happened.** Compute into a scratch variable and copy to
  the displayed one only in the branch where the event happens, or the display
  shows every intermediate value.
- **One status digit per frame**: `INC QD : J = QD & 15` refreshes a 16-digit
  status line without ever costing more than one digit. A digit from `TIME`
  instead saves a character or two but can starve some digits for 40+ frames.

## Expressions that do two jobs

- **Score from what actually changed**: `POKE J, X : S = S + V - PEEK(J)`. A
  write into ROM does nothing, so it scores 0 with no range check.
- **A BCD clock in one integer**: hold MM:SS as four BCD digits so a hex printer
  shows decimal time:
  `W = W + 1 + (W & 15 = 9) * 6 + (W & 255 = 89) * 160 + (W & 4095 = 2393) * 1536`.
- **One variable as volume and timer**: count it down past 0 to -4 and clamp the
  volume with `E & -(E > 0)`: the sound fades and a 16-frame hold timer comes
  free. It costs a clamp every frame (2.7 units).
- **Color from state**: `POKE 712, PEEK(&S + 1) & 240` makes the background hue
  follow the score's first hex digit: a level indicator with no state.

## When to stop

- A trick that saves characters but loses frames on the frame it lands on is
  rejected, or moved to a quieter frame.
- Twenty characters to fix a timing glitch that only appears when someone
  hammers a key twenty times in ten seconds is usually not worth it. A
  two-character fix for a rare self-restart is. Write the decision down.
