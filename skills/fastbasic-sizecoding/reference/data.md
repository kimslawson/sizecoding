# Data inside the listing

The rules allow no loading from disk (outside PLUS), so every table, glyph,
map and weight has to be in the ten lines. How it's written decides how many
characters it costs.

## Cost per byte

| Form | Cost |
|---|---|
| A byte in a string literal | 1 character (`"` costs 2 as `""`; $9B costs 4 as `"$9B"` inside DATA, or a hex escape after the closing quote) |
| A byte in `DATA X() BYTE = 24,60,...` | its digits plus a comma (2 to 4) |
| Overhead of `A$="..."` | 6 characters per chunk |
| Overhead of `DA.X()B.="..."` | 12 per chunk; a continuation line `DA.B.=` costs 7 |

FastBasic's cross-compiler and fbp both pass raw control characters through a
literal untouched (same XEX).

## Strings or DATA

- **Strings** are cheapest for one or two small tables (player frames, a text
  line, glyphs): `G$` as the data segment, `&G$+1+offset` to point into it, or
  `&"..."+1` with no variable at all.
- **DATA is one contiguous block.** Every DATA statement's bytes follow the
  previous one's, across lines and labels. A string variable instead gets its
  own 256-byte buffer on first assignment, so `A$`, `B$`, `C$` sit 256 bytes
  apart; tables crossing a page then need page arithmetic in code (30 to 40
  characters in one measured case).
- **DATA can split anywhere**, so the packer can end each line's DATA at exactly
  the limit. A string holding a fixed-size table must sit whole on one line and
  leaves holes.
- **Names**: many string variables eat the 27 one-letter names.
- Measured on a 1,425-byte table: DATA's whole overhead was 101 characters
  (statements, quotes, commas, a few bytes written as numbers). Strings would
  save about 50 in keywords and give most of it back in code and holes.

## DATA, `DLI SET` and PROC share one block

FastBasic moves every DATA statement, every `DLI SET` routine and every PROC
out of the main code and lays them out one after another **in source order**.
So a table split over many DATA statements is still one table, and anything
else declared in the middle (another DATA, the machine code `DLI SET`
compiles) lands in the middle of it: the program runs and reads nonsense. Put
every other DATA and `DLI SET` before the big table. A `DLI SET` that reads a
table must come after the table.

## Make the overhead useful

- **The length byte is data.** A DATA string literal includes its length byte.
  Start a literal only where the byte that belongs there is itself a usable
  length, and the length byte *is* that data byte. A dynamic program over the
  data image can choose where literals start, falling back to one plain number
  (`,12,`) to reach a better starting point.
- **Element 0 is the length**: a DATA string of sky colors whose length byte
  happens to be the first color needs no separate entry.
- **Shuffle what doesn't matter.** If table rows (hidden units of a network,
  sprite frames, map tiles) can be renumbered without changing the program, try
  thousands of orders and keep the one that packs shortest. On one table that
  took DATA overhead from 232 characters to about 100.
- **Nudge bytes that need escaping.** If a data byte is `"` or $9B and a tiny
  change to the data (one bit, one step of a weight) changes it with no visible
  effect, make the change: 5 to 10 characters per table.
- **Short DATA in the holes.** A short DATA statement can fill a hole at a line
  end with the next bytes of the table (DATA is one block, wherever the
  statements are), but each pays its own keyword. Try both and keep the shorter
  listing.

## Tables built from themselves

- `FOR I = 0 TO 255 : T(I) = T(I / 2) + (I & 1) : NEXT I` builds a popcount
  table in one statement.
- `X(I) = (I & 15) - 8 : X(I + 256) = I / 16 - 8` decodes two signed 4-bit
  values per byte with a lookup instead of a divide per use.
- Pitch, projection, row-offset and direction tables built once at boot cost a
  loop instead of a long DATA statement, when the formula is shorter than the
  data.

## Arithmetic for packed data

- **Popcount dot products**: with +1/-1 weights and activations, a byte of
  weights times a byte of activations is `T(PEEK(W) & E)` with T a popcount
  table: eight multiply-adds in one term, 4.3 units against 8.1 for one
  `S = S + H(J) * PEEK(W)`.
- **Multi-bit values as bit-planes, combined with Horner**: a 3-bit weight is
  three binary planes worth 4, 2 and 1; `Y = Y * 2 + T(...) + ...` over the
  planes in storage order. `Y * 2` is a shift.
- **Two-level searches**: scoring every class is expensive; score groups, then
  only the classes in the best group, in one loop whose bound is a comparison
  (`3 - (K > 6)`).
- **Fold a constant term into the loop that's already there**: recomputing a
  sum per item inside an existing loop can save a whole separate loop's
  characters for a small time cost.

## Generating it

When the data is large, a script should be the source of truth: compute the
tables, choose literal boundaries, escape what needs escaping, splice them into
the BASIC and pack the result (reference/workflow.md). Keep the generator, the
seed and the packer seed in the repository so the listing is reproducible.
