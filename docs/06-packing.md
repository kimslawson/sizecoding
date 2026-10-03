# 6. Packing ten lines

Once the program is small enough, it still has to be cut into ten lines, and that's a puzzle
of its own: a statement can't continue onto the next line, so whatever doesn't fit at the end
of a line leaves a hole.

## What a line break is worth

Within a line, statements are separated by `:`. A line break replaces one of those, so a
listing packed into exactly ten lines is 9 characters shorter than the same program on one
line (the "measure", see [The contest](01-the-contest.md#measuring)). Everything else about
packing is about the holes.

## Fixed order: greedy is optimal

If the statement order can't change, the best you can do is fill each line as far as it goes
and start the next statement on a new line. This "first fit" gives the fewest lines and the
shortest last line possible for that order. `fbsize.py pack` does exactly that.

Don't trust a minimizer's own line breaks for this. FastBasic's `-l:min -ls:120` breaks lines
its own way: on one 1,184-character listing it produced 12 lines, where first fit needs 10.

```sh
python3 tools/fbsize.py pack GAME.min -o GAME.BAS
python3 tools/fbsize.py measure GAME.BAS      # slack per line
```

## When it doesn't fit

In rough order of how often they work:

1. **Find a saving near a line end.** The hole at the end of a line is the length of the
   statement that didn't fit, minus one. Shortening that statement, or one just before it, can
   pull a whole statement back up and cascade down the listing. A few characters saved in the
   right place beat twenty saved in the wrong one.
2. **Put long statements where they can't leave a hole.** A 100-character string literal at
   the start of a line is fine; the same string arriving with 60 characters left on a line
   wastes 60. Where the order is free, move it.
3. **Reorder what can be reordered.** Setup code (graphics mode, display list pokes, colors,
   DATA) often runs in any order, so its statements can fill line ends. Inside the main loop,
   statements of the same frame's work can sometimes swap too.
4. **Split a long statement.** `A$ = "...long..."` can become `A$ = "...":A$ =+ "..."`, two
   pieces that each fit a hole. It costs 7 characters (6 if the split lands on a line break),
   so it only pays when the hole is bigger.
5. **Go back to saving characters.** If the measure is more than a few characters above what
   fits, no amount of shuffling will do it.

## Reordering safely

`fbsize.py pack` can reorder statements inside ranges you mark as free, with simulated
annealing, while keeping the order the compiler needs:

```sh
python3 tools/fbsize.py stmts GAME.min | head -30      # number the statements
python3 tools/fbsize.py pack GAME.min -o GAME.BAS --free '0:/^DO$/' --glue 0:3
```

- `--free A:B` lets statements A to B-1 move. A and B are statement numbers or `/regex/`
  matched against the minimized text (`'0:/^DO$/'` is everything before the main loop).
- `--glue A:B` keeps a group together and in order inside a free range.
- Two order rules are kept automatically, from FastBasic's own expansion of the listing: the
  first statement that mentions a name stays before every other statement that mentions it
  (a variable must be defined before it's used), and those first mentions keep their relative
  order (so every variable keeps its address; `--allow-var-reorder` relaxes this).
- **Order that matters without a shared name is yours to protect.** `GRAPHICS 0` must come
  before `D = DPEEK(560)` reads the new display list, a font must be copied before it's
  patched, PMGRAPHICS before PMADR. Glue those.

The packer compiles the result and tells you whether it still compiles. It can't tell you it
still *works*: the code changed. Rerun your tests.

## Keeping the readable source in step

If the commented source is in the same statement order as the packed listing, a reader can
follow one with the other, and a change to one maps straight onto the other. When the packer
reorders, mirror its order in the readable source (it prints the new order as statement
numbers). Or regenerate a readable listing from the packed one with `fbp -l`, which expands
and indents it but can't bring back your comments.
