# Workflow

The packed listing is a build product. The program lives in a readable source,
and every change goes through a loop that measures it.

## The readable source is the program

- One statement per line, indented, commented. The minimizer drops all of it.
- Same statement order as the packed listing.
- **A legend at the top**: what every variable holds, and when. With 27 names
  doing several jobs each, it's the most useful comment in the file.
- Comments say why: `' -(B>9)&7, not (B>9)*7: 3 units cheaper on the busy frame`.
- Run `fbp -v` after every edit: it flags each statement after a one-line
  `IF ... THEN`.

## When the source is a generator

For ten-liners carrying a lot of data (tables, maps, fonts, weights), make a
script the real source: it computes the tables, writes them as byte strings
(with hex escapes for `"` and $9B), splices them into the BASIC, and emits the
readable listing. Then:

- Edit the generator, never the generated listing.
- Byte tables can be written in the readable source as `""$xx$xx...` hex
  escapes (readable, same bytes); fbp turns each into a raw character. Remember
  indexes and addresses shift by one for the length byte.
- The generator can search: shuffle orderings that don't change the program
  (hidden units, table rows) until the result packs shortest, or nudge data
  bytes that would need escaping.

## Try ideas as variants

```python
# ideas.py
BASE = 'game.bas'
VARIANTS = {
    'inc':     [('QD = QD + 1', 'INC QD')],
    'mask':    [('(B > 9) * 7', '-(B > 9) & 7')],
    'nosound': [('SOUND\n', '')],
}
```

```sh
python3 tools/variants.py ideas.py              # each variant alone, sorted by saving
python3 tools/variants.py ideas.py inc nosound  # the combination, written to build/inc+nosound.bas
```

Each replacement must match exactly once, so a stale variant fails loudly.
Once a combination measures well and passes the tests, apply it for real.

## The loop, for every change

1. **Size**: the measure of the minimized program (`fbsize.py min`), not the
   packed count, which jumps with line breaks.
2. **Speed**: `fbframes.py` in every scenario: 0 lost frames, or a decision you
   wrote down.
3. **Behavior**: play it; for anything subtle, script it (keys plus a
   screenshot or a memory read).
4. **Pack and verify**: `fbsize.py pack`, then `fbsize.py verify` (same
   statements) and `--xex` (same code).
5. **Commit** with the size and test results in the message.

Changes that must not change the program (renames, parentheses, reordering an
expression) must give a **byte-identical XEX**. `fbsize.py min` reports it.

## Bisect when savings add up to a loss

Savings that each measure clean can lose frames together: small costs on the
same tight frame add up. Apply them one at a time, measure each, keep the ones
that fit. Variants make this one command each.

## Keep a history, including failures

A table with every version, its size, frames lost per scenario and what changed
becomes the best documentation the code has. Keep the rejected ideas with their
reason and number: "saves 4, loses 3 to 7 frames per 10 s on rotation frames."
Real examples from finished games:

| Idea | Characters | Rejected because |
|---|---|---|
| status digit from `TIME` instead of a counter | -1 to -3 | some digits waited 43 to 57 frames between refreshes instead of 26 |
| shorter rotation with two divides | -4 | 3 to 7 frames lost per 10 s |
| `F/256` instead of `PEEK(&F+1)` | -3 | about 5 units slower: no byte read for `/256` |
| hardcoding the display list or PMADR address | -2 | addresses depend on RAM size and BASIC |
| a true toggle for a rarely used key | +19 | lost 2 to 4 frames per 10 s; a restart-into-mode did the job for nothing |
| key handling moved into status slots | +24 | fixed a lag only seen when hammering keys; nobody plays that way |

## Project conventions that kept AI-assisted sessions honest

Ten-liner projects built with an AI assistant went best with a few files that
every session reads first:

- **DEVELOPING.md**: goals, what the author has decided ("don't relitigate"),
  the exact toolchain commits, the memory map, the tests to run after every
  change, and a list of pitfalls that each cost time.
- **HISTORY.md**: every variant tried, with its numbers.
- **DECISIONS.md**: date, context, decision, consequences.
- A short **CLAUDE.md / AGENTS.md** that points at those and states the hard
  rules: "0 lost frames after every change", "the packed listing must fit and
  compile to the same XEX as the readable one", "edit the generator, never the
  generated listing".
- A **contest builder** script that assembles the submission folder from a
  README template and the build outputs, so the ZIP is always in step with the
  source, plus a boot check (BASIC off, BASIC on, PAL).
- **Small spikes** for each risky idea (a timing test, a display test) before
  it goes into the game, kept in a `spikes/` folder with their results.
