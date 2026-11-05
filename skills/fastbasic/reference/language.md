# FastBasic language facts

FastBasic 4.7. Grammar rule names refer to `src/syntax/*.syn` in the FastBasic
source, so each fact can be checked against another version.

## Targets

| Target | Flag | Numbers | Notes |
|---|---|---|---|
| Floating point | `-t:atari-fp` (the default) | integers plus FP (`%` suffix variables) | Adds `float.syn` and `fujinet.syn`: the only target with `NOPEN`/`NGET`/... |
| Integer | `-t:atari-int` | 16-bit signed integers only | Smaller runtime; what ten-liners and most games use |
| Cartridge | `atari-cart-int`, `atari-cart-fp` | as above | Output is a cartridge image |
| 5200 | `atari-5200` | integer | Different hardware map |

The IDE on the Atari comes in FP and integer flavors with the same split.

## Precedence

Tightest to loosest (rules `T_EXPR`, `BIT_EXPR_MORE`, `M_EXPR_MORE`,
`INT_EXPR_MORE`, `COMP_EXPR_RIGHT`, `NOT_EXPR`, `AND_EXPR_RIGHT`, `OR_EXPR_RIGHT`):

| Level | Operators |
|---|---|
| 1 | numbers, variables, `( )`, functions, `&` (address-of), unary `-` and `+` |
| 2 | `&` `!` `EXOR` (bitwise AND, OR, XOR, left to right) |
| 3 | `*` `/` `MOD` |
| 4 | `+` `-` |
| 5 | `=` `<>` `<` `>` `<=` `>=` (result 1 or 0) |
| 6 | `NOT` |
| 7 | `AND` (logical) |
| 8 | `OR` (logical) |

Consequences, all real bugs or real savings:

```
I + U & B       is  I + (U & B)
J & 4 / 4       is  (J & 4) / 4
15 - T & 12     is  15 - (T & 12)
X * Y & 15      is  X * (Y & 15)
L ! R < 0       is  (L ! R) < 0
X + 1 & 7       is  X + 1          (NOT a wrap: write (X + 1) & 7)
-(B > 9) & 7    is  (-(B > 9)) & 7, which is 7 or 0
```

## Functions take one terminal

A one-argument function takes a level-1 terminal, with or without parentheses
(rule `INT_FUNCTIONS`): `PEEK 712`, `STICK 0`, `RAND 10`, `PEEK PEEK 88`. Only
one terminal: `PEEK &X+1` is `PEEK(&X)+1`, `ABS X-1` is `ABS(X)-1`. When in
doubt, parenthesize; a minimizer removes what isn't needed.

## Comparisons and logic

- A comparison is a number: 1 true, 0 false. `F = A > B`, `POKE 712, K > 0`,
  `K = K + (B > 9) * 7` all work. Inside arithmetic it needs parentheses (level 5
  is loose).
- `-(c)` is -1 or 0, a mask: `X & -(c)` is X or 0.
- `AND`, `OR`, `NOT` are logical (nonzero is true, result 1 or 0). **Both sides
  of `AND`/`OR` are always evaluated.** `IF I < 40 AND PEEK(A + I)` still reads
  `PEEK(A+I)` when I is 40 or more. Nest instead:
  `IF I < 40 THEN IF PEEK(A + I) THEN S`. That is also faster.
- `&`, `!`, `EXOR` are bitwise over all 16 bits.

## Integers

- 16-bit signed, -32768 to 32767, wrapping without error. A `FOR` whose end is
  above 32767 never ends or never starts; loop over a count instead.
- `POKE` stores the low byte: `POKE A,-1` stores 255, `POKE A,-1-V` stores 255-V.
- Values from 32768 up are negative: `$E000` is -8192, `65535` is -1.
- `TIME` is the jiffy counter (60 Hz NTSC, 50 PAL). It wraps from 32767 to
  -32768 after about 9 minutes. `TIMER` resets it. The runtime reads it
  atomically.
- Signed division truncates; check what `/256` does with negative numbers
  before relying on it in shared logic (two machines computing the same hash,
  for instance).

## Names

- **One name space for all variable types.** `A`, `A$`, `A()` collide. 27
  one-letter names: `A` to `Z` and `_`.
- **Labels are a separate name space.** PROC, DATA and DLI names can reuse a
  variable's letter, with three catches when a DATA label shares a variable's
  name: `&X` and `ADR(X)` give the DATA address; `X(n)` reads an array variable
  X first; assigning to a DATA element (`X(0) = 1`) can create a stray
  variable X and change the compiled code.
- **A variable exists from its first appearance in the source**, top to bottom.
  Assignment, `FOR`, `INC`, `DEC`, `INPUT`, `GET` and `DIM` create it. Reading it
  before that is a compile error ("expected: variable name"), even if a PROC
  that runs first would assign it.
- **Every variable starts at 0**: the runtime clears them at startup. A
  variable that is only set later works as a free "first pass" flag.
- **First appearance is memory order.** `DIM A, B, C` puts three words at
  consecutive addresses, so `MSET &A, 6, 0` clears all three and
  `PEEK(&A+1)` is A's high byte. Moving statements can change the order.

## Strings and data

- A string literal holds any byte except `"` (write `""`) and $9B. Splice
  bytes after the closing quote with hex escapes: `"ABC"$9B"DEF"`, `""$0F$1E`.
- `&A$` is the length byte, `&A$+1` the first character; `&"..."` works on
  literals too, with no variable.
- `$(address)` reads memory as a string (length byte first).
- Strings are at most 255 bytes. `A$ =+ B$` appends. A string expression must be
  assigned before use in some statements (build URLs with `=+` into a variable).
- **Assigning a string variable takes a 256-byte heap buffer**, even for two
  characters. Constant text used through `&"..."` or `ADR("...")` stays in the
  program and takes none.
- `DATA X() = 1, 2, 3` (words) or `DATA X() BYTE = 1, 2, "AB"` (bytes, strings
  allowed). `DIM X(9) BYTE` is a zeroed byte array.
- `DATA X() BYTEFILE "file"` and `WORDFILE "file"` (cross-compiler only) pull a
  binary file in at compile time: no loader code, no disk access at run time.
- DATA statements, `DLI SET` routines and PROC bodies are moved out of the main
  code and laid out **one after another in source order**. Consecutive DATA
  statements therefore form one contiguous table, and anything else declared
  between them (another DATA, a `DLI SET`'s machine code) lands in the middle
  of it.

## Statements and blocks

- `IF C THEN S`: exactly one statement S. Everything after the next `:` is
  unconditional. `IF A THEN IF B THEN S` nests.
- `IF C` ... `ELIF D` ... `ELSE` ... `ENDIF`: blocks may span lines and share
  lines with other statements. An ELIF chain runs exactly one arm.
- Loops: `DO`/`LOOP`, `REPEAT`/`UNTIL`, `WHILE`/`WEND`, `FOR`/`NEXT` (variable
  after NEXT optional). `EXIT` leaves the innermost loop.
- No GOTO, GOSUB or line numbers. `PROC P` ... `ENDPROC`, called with `EXEC P`
  or `@P`. Parameters (`PROC P X`, `@P 5`) assign globals.
- Comments: `'` anywhere, or `.` at the start of a statement.
- `PAUSE` (same as `PAUSE 0`) waits for the next vertical blank; `PAUSE n`
  waits n jiffies.
- The runtime turns sound off before your first statement.
- `USR(address, args...)` calls machine code; `USR(@label, ...)` calls a label
  from a linked assembly module (reference/toolchain.md).

## Input and output

- `PRINT` (`?`) and `POSITION` go through the OS: slow (about 5.9 units for a
  position plus a one-character print). POKE screen codes into screen memory
  for anything per-frame.
- Screen codes are not ATASCII: ATASCII 32-95 is screen code 0-63
  (`C - 32`), 0-31 becomes 64-95, 96-127 stays. Digits 0-9 are 16-25.
- A carriage return on the bottom row of GRAPHICS 0 scrolls the whole screen.
  Use `POSITION` and end `PRINT` with `;`.
- `POKE 752,1` hides the cursor. `POKE 82, n` sets the left margin.
- File I/O: `OPEN #c, mode, aux, "D:FILE"`, `BGET`/`BPUT #c, addr, len`,
  `GET #c, X`, `XIO`, `CLOSE #c`. `ERR()` holds the last I/O error.
