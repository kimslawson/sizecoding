# 7. Workflow

Ten lines invite editing the packed listing directly. Don't. The packed listing is a build
product; the program lives in a readable source, and every change goes through a loop that
measures it.

## The readable source is the program

- **One statement per line, indented, with comments.** The minimizer throws all of that away,
  so it costs nothing. FastBasic's `-l:lst` or fbp's `-l` expand a packed listing into this
  form if you're starting from one.
- **Same statement order as the packed listing.** Then one maps onto the other line by line,
  the submission's commented listing is free, and a judge reading it sees the real program.
- **A legend at the top**: what every variable holds, and when. With 27 one-letter names doing
  several jobs each, this is the most useful comment in the file.
- **Comments say why**, not what: `' -(B>9)&7, not (B>9)*7: 3 units cheaper on the busy frame`
  is worth more than `' add 7 if B>9`.

## Try ideas as variants

Most size ideas are small, and they interact. Instead of editing the source and remembering
what you changed, write each idea as a named variant: a list of exact text replacements on the
readable source. [`tools/variants.py`](../tools/README.md) builds any combination and reports
its measure:

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
python3 tools/variants.py ideas.py              # every variant alone, sorted by what it saves
python3 tools/variants.py ideas.py inc nosound  # the combination; writes build/inc+nosound.bas
```

Each replacement must match exactly once when it's applied, so a variant that no longer fits
the source fails loudly instead of silently doing nothing. Once a combination measures well and
passes the tests, apply it to the source for real and delete the variants.

## The loop

Every change, however small:

1. **Measure the size.** The measure of the minimized program (`fbsize.py min`), not the packed
   character count, which jumps around with line breaks.
2. **Measure the speed.** `fbframes.py` with your scenarios: 0 lost frames, or a decision you
   wrote down.
3. **Check the behavior.** Play it, and for anything subtle, script it: a key sequence plus a
   screenshot or a memory read (the emulator harness in `tools/emu.py` does both).
4. **Pack and verify.** `fbsize.py pack`, then `fbsize.py verify` that the packed listing holds
   exactly the statements of the minimized one.
5. **Commit**, with the size and the test results in the message.

Changes that should not change the program at all (renames, parentheses, reordering an
expression) have a stronger check: the compiled XEX must be byte-identical. `fbsize.py min`
reports it, and `fbsize.py verify --xex` checks two listings.

## Keep a history, including the failures

A table with every version, its size and what changed turns out to be the best documentation
the code has. Keep the rejected ideas too, with the reason: "saves 4, loses 3 frames per 10 s
on rotation frames" stops you from trying it again next month, and explains to a reader why
the obvious shorter form isn't there.

## Bisect when savings add up to a loss

Several savings that each measure clean can lose frames together: small costs on the same tight
frame add up. When a batch fails, apply them one at a time, measure each, and keep the ones
that fit. The variants file makes this one command per variant.

## Decide what's worth it

Not every problem deserves characters. A two-character fix for a rare bug that would restart
the game is cheap insurance. Twenty characters to keep frame-perfect timing while someone
hammers a key twenty times in ten seconds is not, if nobody plays that way. Write down the
decision either way.
