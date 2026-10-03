# Sizecoding in FastBasic&nbsp;&nbsp;🗜️&nbsp;🕹️

How to fit a real game into ten lines of [FastBasic](https://github.com/dmsc/fastbasic) on the
Atari 8-bit, for the [BASIC 10Liner](https://www.homeputerium.de/) contest: what the language
lets you get away with, which tricks actually save characters, how to keep a ten-liner fast
enough to never drop a frame, and a small toolchain that measures all of it so you don't have
to guess.

Everything here was learned the hard way on real PUR-120 entries, then generalized. Every
character count in these pages is checked against the real compiler by
[`tests/tricks.py`](tests/tricks.py), every behavior claim is run in an emulator, and every
timing comes from [`bench/`](bench/). If a number here is wrong, a test should say so.

## The pitch&nbsp;&nbsp;📈

Ten lines. 120 characters each (or 256, if you're feeling EXTREME). No machine code. Go.

## The short version&nbsp;&nbsp;⚡

If you read nothing else:

1. **Never abbreviate by hand.** Write a readable, commented source and let a minimizer do the
   spelling. Use [fbp](https://github.com/kimslawson/fastbasic-parser) with `-O`: on two full
   PUR-120 listings it beat FastBasic's own `-l:min` by 36 and 21 characters, with a
   byte-identical XEX.
2. **Learn the precedence.** `&`, `!` and `EXOR` bind *tighter* than `*` and `/`, which bind
   tighter than `+` and `-`. `I+U&B` is `I+(U&B)`. Most parentheses you'd type in another
   BASIC are dead weight here. (It cuts both ways: `X+1&7` is `X+1`, not a wrap.)
3. **Comparisons are numbers.** True is 1, false is 0, so `F=A>B` replaces a whole
   IF/ELSE/ENDIF (15 characters) and `K=K+(B>9)*7` replaces an IF.
4. **One-letter names, given to the variables you use most.** There are 27 of them: A to Z and
   `_`.
5. **Functions take a bare argument.** `PEEK 712`, `STICK 0`, `RAND 10`.
6. **Strings are your data segment.** Any byte but `"` and $9B fits in a literal, and
   `&"..."` is the address of a literal with no variable at all.
7. **The OS already did the work.** Patch its display list instead of building one; the
   runtime already turned the sound off.
8. **Speed is a budget, not a feeling.** A frame is 131 units of 2 scanlines (NTSC). Measure
   what statements cost, give heavy jobs their own frames, and count lost frames with a
   tool, not your eyes.
9. **Packing is its own problem.** A statement never splits across lines, so the last 10 to
   40 characters of each line are where listings go to die.
10. **Try ideas as variants, not edits**, and keep the ones that measure better.

## The pages&nbsp;&nbsp;📚

| | |
|---|---|
| [1. The contest](docs/01-the-contest.md) | Categories, what counts as a character, what to submit |
| [2. FastBasic for sizecoders](docs/02-fastbasic-for-sizecoders.md) | The language facts every trick leans on: abbreviations, precedence, names, strings, blocks |
| [3. Size tricks](docs/03-size-tricks.md) | The catalogue: before, after, characters saved, and why it works |
| [4. Atari tricks](docs/04-atari-tricks.md) | Display lists, players and missiles, DLIs, sound and input on a budget |
| [5. Speed](docs/05-speed.md) | The frame budget, what each statement costs, scheduling, counting lost frames |
| [6. Packing ten lines](docs/06-packing.md) | Line breaks, reordering, and why the end of a line matters most |
| [7. Workflow](docs/07-workflow.md) | Readable source, variants, measuring, testing: the loop that keeps it honest |
| [8. Submission](docs/08-submission.md) | The ZIP, the proof image, the disk image |
| [Abbreviations](docs/abbreviations.md) | Every keyword's shortest spelling, generated from the grammar |

## The toolchain&nbsp;&nbsp;🧰

Python 3 scripts in [`tools/`](tools/), documented in [tools/README.md](tools/README.md):

| Tool | What it does |
|---|---|
| `fbsize.py` | Measure, minimize, pack into 10 lines (with safe reordering), verify |
| `variants.py` | Try size ideas as named, combinable edits and see what each saves |
| `fbbench.py` | Time statements in the emulator, in units of 2 scanlines |
| `fbframes.py` | Count lost frames in your game while a script plays it |
| `proof.py` | Render a listing as an ATASCII image for the contest's proof |
| `abbrevs.py` | Regenerate the abbreviation table from FastBasic's grammar |

```sh
export FASTBASIC=/path/to/fastbasic   # the cross-compiler
export FBP=/path/to/fbp               # optional, but it's free characters
python3 tools/fbsize.py min game.bas -o GAME.min      # minimize + check the XEX is identical
python3 tools/fbsize.py pack GAME.min -o GAME.BAS     # break into 10 lines of 120
python3 tools/fbsize.py measure GAME.BAS              # what's left on every line
python3 tools/proof.py GAME.BAS -o proof.png          # the listing as the Atari sees it
```

The size tools need only Python and FastBasic. The emulator tools (`fbbench`, `fbframes`,
the behavior half of the tests) need Linux with atari800, Xvfb, xdotool and ImageMagick.

## Colophon&nbsp;&nbsp;🙏

Shoutouts to @dmsc for FastBasic, which makes all of this possible (and fast), and to Gunnar
and the NOMAM crew for running the BASIC 10Liner contest year after year. Timings were measured
in [atari800](https://atari800.github.io/) with its built-in AltirraOS, thanks to Avery Lee's
[Altirra](https://www.virtualdub.org/altirra.html).

## Get in touch&nbsp;&nbsp;📩

  * [OxC0FFEE on AtariAge](https://atariage.com/forums/profile/50996-oxc0ffee/)
  * [@0xC0FFEE@oldbytes.space on Mastodon](https://oldbytes.space/@0xC0FFEE)
  * [ozymandias.lol](https://ozymandias.lol)

Found a trick that isn't here, or a number that's wrong? Open an issue or a PR, ideally with a
`trick(...)` line for `tests/tricks.py` that proves it.
