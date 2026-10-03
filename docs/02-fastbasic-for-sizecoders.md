# 2. FastBasic for sizecoders

FastBasic 4.7, integer target (`-t:atari-int`), as seen by someone counting characters. Every
trick in the next chapters is one of these facts used on purpose. Where a fact comes from the
grammar, the rule name in FastBasic's `src/syntax/*.syn` is given, so you can check it against
your version.

## Spelling is the minimizer's job

Every keyword has a shortest form, and you should never type it. FastBasic's grammar writes
each keyword with its required part in uppercase and the optional part in lowercase:
`"PMGraphics"` can be typed `PMG.`, `PMGR.` and so on up to `PMGRAPHICS`. The full table is in
[abbreviations.md](abbreviations.md), generated from the grammar. A few things worth knowing:

- **The same abbreviation means different things in different places.** `P.` is POKE as a
  statement and PEEK in an expression. `S.` is SOUND or STICK, `T.` is TIMER, TIME, TO or
  THEN, `E.` is ENDIF or EXOR.
- **Two statements are a single symbol:** `?` is PRINT and `@` is EXEC.
- **Some words have no abbreviation:** `INC`, `DO`, `END`, `CLS`, `CLR`, `CHR$`, `STR$`.
- **Spaces are only needed where a name would run into a word.** `IF A=1 THEN` minimizes to
  `I.A=1T.` with no space, but `IF A THEN` needs one: `I.A T.`, otherwise the parser would read
  a variable called `AT`. The same goes for `A M.8` (MOD) and `A A.B` (AND).
- **Numbers are rewritten in their shortest form.** Decimal is never longer than hex, and any
  value from 32768 up can be written as a negative number: 65535 is `-1`, $FFF0 is `-16`,
  $E000 is `-8192`. So `X&$FFF0` costs `X&-16`.

There are two minimizers, and they are not equal:

| | `fastbasic -l:min` | [fbp](https://github.com/kimslawson/fastbasic-parser) `-O` |
|---|---|---|
| Keywords, numbers, spaces | shortest | shortest |
| Parentheses | keeps every one you wrote, adds them around function arguments | removes the ones precedence makes redundant, and those around a function's argument |
| `IF`/`ENDIF` with one statement | kept as a block | becomes `IF ... THEN` |
| `ELSE` + `IF` block | kept | becomes `ELIF` |
| `IF X<>0` | kept | `IF X` |
| `;` in PRINT | kept | removed where not needed |
| Variable names | kept | one letter for the most used ones (`-f` keeps them) |
| Checks the result | no | compiles it and compares the code |

On two complete PUR-120 games, fbp `-O` came out 31 and 21 characters shorter than `-l:min`,
both with a byte-identical XEX. If you use `-l:min`, write the forms in the right column by
hand; [Size tricks](03-size-tricks.md) gives each one's saving under both tools.

## Expressions

### Precedence

From tightest to loosest (grammar rules `T_EXPR`, `BIT_EXPR_MORE`, `M_EXPR_MORE`,
`INT_EXPR_MORE`, `COMP_EXPR_RIGHT`, `NOT_EXPR`, `AND_EXPR_RIGHT`, `OR_EXPR_RIGHT`):

| | Operators | |
|---|---|---|
| 1 | numbers, variables, `( )`, functions, `&` (address), unary `-` and `+` | a "terminal" |
| 2 | `&` `!` `EXOR` | bitwise AND, OR, XOR, left to right |
| 3 | `*` `/` `MOD` | |
| 4 | `+` `-` | |
| 5 | `=` `<>` `<` `>` `<=` `>=` | result is 1 or 0 |
| 6 | `NOT` | |
| 7 | `AND` | logical |
| 8 | `OR` | logical |

The unusual part is level 2. Bitwise operators bind tighter than multiplication, so:

```
I + U & B       is  I + (U & B)
J & 4 / 4       is  (J & 4) / 4
(R+M) & -8 * 5  is  ((R+M) & -8) * 5
K - B & K       is  K - (B & K)
L ! R < 0       is  (L ! R) < 0
X + 1 & 7       is  X + (1 & 7), which is X + 1. Not a wrap!
```

And unary minus binds tightest of all: `-(B>9)&7` is `(-(B>9))&7`, which is 7 or 0.

### Function arguments are one terminal

A function with one argument takes a terminal, with or without parentheses (grammar rule
`INT_FUNCTIONS`: `"Peek" T_EXPR`). So `PEEK 712`, `STICK 0`, `RAND 10`, `PEEK &X`,
`ABS -X` and even `PEEK PEEK 88` are all fine. But only one terminal: `PEEK &X+1` is
`PEEK(&X)+1`, and `ABS X-1` is `ABS(X)-1`. Functions without arguments lose their parentheses
when abbreviated: `K.` for `KEY()`.

### Comparisons are numbers

A comparison is 1 (true) or 0 (false), and it can go anywhere a number can:

```
F = A > B              ' assignment takes a comparison directly
POKE 712, K > 0        ' so does POKE
K = K + (B > 9) * 7    ' inside arithmetic it needs parentheses (level 5 is loose)
K = -(B > 9) & 7       ' same value: -1 & 7 or 0 & 7
```

### Logical and bitwise

`AND`, `OR` and `NOT` are logical: they treat any nonzero value as true and give 1 or 0.
FastBasic evaluates **both** sides of `AND` and `OR`, always (there is no short-circuit), so a
nested `IF` that fails on its first test is faster than an `AND` (see [Speed](05-speed.md)).
`&`, `!` and `EXOR` are bitwise and work on all 16 bits.

### Integers

Integers are 16-bit signed, -32768 to 32767, and wrap without complaint. `POKE` stores the low
byte, so `POKE A,-1` stores 255 and `POKE A,-1-V` stores 255-V. `TIME` is the 60 Hz (50 on PAL)
jiffy counter and wraps from 32767 to -32768 after about 9 minutes.

## Names

- **There is one name space for variables of every type.** `A`, `A$` and `A()` are the same
  name, so a program can't have a numeric `G` and a string `G$`. There are 27 one-letter names:
  `A` to `Z` and `_`. PROC, DATA and DLI names are labels, in a name space of their own, so
  `DLI SET N = ...` and a variable `N` can coexist (labels can't repeat each other, though).
  Three catches when a DATA label shares a variable's name: `&X` and `ADR(X)` give the DATA
  address, not the variable's; `X(n)` reads an array *variable* X first; and assigning to a
  DATA element (`X(0) = 1`) normally makes the parser create a stray variable named X, which
  doesn't happen if X already exists, so the compiled code changes.
- **A variable exists from its first appearance in the source**, reading top to bottom (not in
  execution order). Assignment, `FOR`, `INC`, `DEC`, `INPUT`, `GET` and `DIM` all create it.
  Reading it before any of those is a compile error ("expected: variable name"), and the fix is
  a `DIM`, which costs characters.
- **Every variable starts at 0.** The runtime clears them all at startup, so a variable that is
  only ever set later can serve as a "first pass" flag for free.
- **First appearance is memory order.** Each variable gets the next slot when it first
  appears in the source, and a DIM is just an early appearance. So `DIM A, B, C` puts the three
  words at consecutive addresses, `&A` is A's address, and one `MSET &A, 6, 0` zeroes all
  three. Reordering statements can change which variable comes first and move them all.

## Strings and data

- **A string literal can hold any byte except `"` and $9B.** A quote is written `""`, and $9B
  (or any byte) can be spliced in with a hex escape after the closing quote:
  `"ABC"$9B"DEF"`. Every other byte counts as one character.
- **`&A$` is the address of A$'s length byte**, so `&A$+1` is its first character. And `&`
  works on a literal too: `&"..."+1` is the address of a constant string's first byte, with no
  variable at all.
- **`$(address)` reads memory as a string** (length byte first).
- **DATA arrays** hold words or bytes: `DATA X() = 1, 2, 3` or `DATA X() BYTE = 1, 2, "AB"`.
  Byte DATA can include strings. `DIM X(9) BYTE` makes a zeroed byte array.
- Strings are at most 255 bytes, and `A$=+B$` appends.

## Statements and blocks

- **`IF ... THEN` takes exactly one statement**, and anything after the next `:` always runs.
  `IF ... THEN IF ... THEN ...` nests. Longer bodies need `IF` / `ELIF` / `ELSE` / `ENDIF`.
- **Blocks can span lines, statements can't.** An IF, a loop or a PROC can start on one line and
  end on another, which is what lets a packer break lines anywhere between statements.
- **Loops:** `DO`/`LOOP` (forever), `REPEAT`/`UNTIL`, `WHILE`/`WEND`, `FOR`/`NEXT` (the
  variable after `NEXT` is optional). `EXIT` leaves the innermost loop.
- **No GOTO, no GOSUB, no line numbers.** `PROC name` ... `ENDPROC`, called with `@name`.
- **Comments** start with `'` anywhere or `.` at the start of a statement. They cost nothing in
  the readable source, because the minimizer drops them.
- **Startup does some work for you.** The runtime turns the sound off before your first
  statement, so a leading `SOUND` is wasted.
- `PAUSE` (same as `PAUSE 0`) waits for the next vertical blank; `PAUSE n` waits n jiffies.
  `TIMER` resets `TIME`.
