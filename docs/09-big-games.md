# 9. Big games: an expanded build in parallel

An EXTREME-256 game is 2,500 characters of dense code: too big to keep in your head, too
dense to change safely once it's packed. This chapter is the workflow that got
[HIGHBALL](https://github.com/kimslawson/pinball8) (endless pinball, physics, two players,
60 fps) from nothing to a fitting listing without painting itself into a corner. The numbers
are from that game; its `docs/HISTORY.md` has all of them.

## Two programs, one game

Keep two builds of the same game, from the start:

- **The expanded build**: long names, comments, PROCs wherever they help, data as readable
  `DATA` lists, no size limit at all. This is where every *behaviour* change is made first,
  tested and measured.
- **The ten-liner source**: a Python generator (`gen.py`) that writes a readable listing with
  the data spliced in as raw bytes in strings. The minimizer and packer turn that into the
  entry (see [Workflow](07-workflow.md)).

The rule that keeps them in step: **behaviour changes go to the expanded build first; size
changes may live in the ten-liner alone.** Rewriting row generation from templates to direct
POKEs saves characters and changes nothing a player sees, so it can stay ten-liner-only;
dropping a feature, retuning a kick or fixing a physics bug must be made (or ported back)
in the expanded build, and noted in the history.

Squeezing finds bugs. Four of HIGHBALL's physics bugs turned up while the ten-liner was being
cut down, because cutting means re-reading every statement. Port each fix back the same day.

## Let fbp name things

fbp `-O` renames variables to one or two letters by how often they're used. So the ten-liner
source can keep names like `ballx` and `velx`, which makes it reviewable, and the listing
still gets the shortest names. Two habits help it:

- **Setup temporaries should borrow hot names.** A loop counter used only at start-up costs a
  two-letter name if it's a variable of its own. Call it after a variable the main loop uses
  constantly (`d`, `e`, `j`...) and both share one letter. HIGHBALL had 22 two-letter
  variables at one point.
- **Hoist repeated literals yourself.** fbp doesn't: a 21-byte segment table read in three
  places was in the listing three times. One `G = &"..." + 1` saved about 45 characters.

## Data: where the zeros go

A string literal costs one character per byte, zeros included. When the target memory is
already cleared, order the glyphs so the zero runs fall at the *ends* of the string and start
the MOVE past the leading zeros: `MOVE &"..." + 1, $680C, 73` instead of `$6808, 80`.

## Measure overruns, not totals

`fbframes.py` counts lost frames over ten seconds. When a game has a deliberate pause (a new
level being built) or a few rare overruns, the total doesn't say which pass overran. Log only
the passes that did, with the state that made them slow:

```
PAUSE : T0 = TIME
...
IF TIME - T0 > 1                     ' this pass took more than its frame
  A = $9000 + (N & 127) * 32 : INC N
  DPOKE A, TIME - T0 : DPOKE A + 2, HIT : DPOKE A + 4, BUSY ...
ENDIF
LOOP
```

One IF per pass, so it barely disturbs the timing; read the buffer with the emulator's
monitor (`WRITE 9000 AFFF file`). HIGHBALL's `tools/overruns.py` does this, and
`tools/trace.py` the same for every frame (for debugging physics, not timing). Every
reported overrun in HIGHBALL's development pointed straight at a combination of jobs.

## Scheduling a physics game

- **Alternate by a pass counter, not `TIME & 1`.** With TIME, one overrun puts the next pass
  on the same parity: the heavy job runs again and overruns again (see [Speed](05-speed.md)).
  `INC P : IF P & 1` alternates whatever happens.
- **Defer what can wait.** A score digit to add or a new row to generate can wait a frame.
  A "busy" flag set by the expensive job of a pass (a 128-byte glyph MOVE) postpones them.
- **Hardware registers that latch across frames** (collisions) can be read every other frame
  without missing anything. But the state you react to is then two frames old: undo two
  frames of motion, not one, and expect contacts that cover the whole object.

## Closed forms instead of mirrored code

Left/right pairs tempt you into writing the code twice. HIGHBALL's flipper kick took about
110 characters as two branches and about 60 as one formula: with `H` the ball's column minus the
centre, `SGN H` is the side, `ABS H` the distance from the pivot, and `velx = -H * 32` sends
it towards the middle from either flipper. Look for the variable that makes the two cases one.

## Decide with the user what goes

When the listing doesn't fit, list candidates with their cost in characters and in play
(HIGHBALL's history: slingshots 62 characters, flipper taper 7, a ring clear 16), cut the
ones that change the game least, and write down every cut. Features the user asked for come
last.
