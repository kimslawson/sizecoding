# Packing ten lines

A statement can't continue onto the next line, so whatever doesn't fit at the
end of a line leaves a hole. Blocks (IF/ENDIF, DO/LOOP, PROC) can span lines;
statements can't.

## Measure first

- **Measure**: the minimized program as one line, every line break counted as a
  `:`. It doesn't depend on where lines break, so it's the number to compare
  between ideas.
- A listing packed into exactly 10 lines has characters = measure - 9.
- Expect 10 to 40 characters of waste per line. If the measure is more than a
  few characters above what fits, no shuffling will save it: go back to size
  tricks.

## Fixed order: first fit is optimal

If statement order can't change, filling each line as far as it goes and
starting the next statement on a new line gives the fewest lines and the
shortest last line. `fbsize.py pack` does that. Don't trust a minimizer's own
line breaks: FastBasic's `-ls:120` produced 12 lines for a listing that first
fit packs into 10.

## When it doesn't fit, in order of how often it works

1. **Save near a line end.** The hole is the length of the statement that
   didn't fit, minus one. Shortening that statement or one just before it can
   pull a statement up and cascade. A few characters in the right place beat
   twenty in the wrong one.
2. **Put long statements where they can't leave holes.** A long string literal
   at the start of a line is fine; arriving with 60 characters left, it wastes
   60.
3. **Reorder what can be reordered.** Setup code (graphics mode, display list
   pokes, colors, DATA) usually runs in any order and fills line ends. The main
   loop is mostly fixed.
4. **Split a long statement.** `A$="...":A$=+"..."` costs 7 characters (6 if the
   split lands on a line break); worth it only for bigger holes.
5. **Back to saving characters.**

## Reordering safely

```sh
python3 tools/fbsize.py stmts GAME.min | head -30
python3 tools/fbsize.py pack GAME.min -o GAME10.BAS --free '0:/^DO$/' --glue 0:3
```

- `--free A:B` lets statements A to B-1 move (numbers or `/regex/`).
  `'0:/^DO$/'` frees everything before the main loop.
- `--glue A:B` keeps a group together and in order.
- Kept automatically: the first statement mentioning a name stays before every
  other one mentioning it, and first mentions keep their relative order (so
  every variable keeps its address; `--allow-var-reorder` relaxes this).
- **Order without a shared name is yours to protect**: `GRAPHICS 0` before
  `D = DPEEK(560)`, a font copy before patching it, `PMGRAPHICS` before `PMADR`.
  Glue those.
- The packer checks the result compiles, not that it works. Rerun the tests.
- A packer that keeps the input order whenever it already fits guarantees a
  size-only change can't reorder the program.
- Annealing is random: try more than one seed and keep the best.

## Big data and line ends

- **DATA can split anywhere**, so a DATA stream can end each line at exactly the
  limit. When DATA runs onto the next line, end the line with a comma and start
  the next with `DA.B.=...` instead of `DA.X()B.=...`: 7 characters instead of 9
  per continuation, and code can follow after a colon.
- A string holding a fixed-size table must sit whole on one line, so it leaves
  holes; DATA doesn't.
- Everything you change moves where lines break and where DATA starts, so
  savings in code don't map one to one onto savings in the packed listing.

## Keeping the readable source in step

Keep the commented source in the packed listing's statement order, so a reader
can follow one with the other and the commented submission listing is free.
When the packer reorders, mirror its order. `fbp -l` regenerates a readable
listing from a packed one (without comments); `fbp -a` writes an annotated long
listing that keeps the source's comments, uses the short listing's names and
marks where each packed line starts with its length.
