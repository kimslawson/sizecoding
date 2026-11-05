# Testing in an emulator

Play-testing catches what you look for. Scripted tests catch regressions,
lost frames and bugs that only show on one frame in fifty. The sizecoding
repo's `tools/` (Python 3) implement everything here; `scripts/setup.sh`
installs them.

## The harness

atari800 under a virtual X display, keys sent with xdotool, screenshots with
ImageMagick. `tools/emu.py` wraps it:

- `emu.run(xex, keys=...)` runs a program, plays a key script, returns a
  screenshot.
- `emu.read_screen(png)` reads a GRAPHICS 0 screen back as text.
- `emu.Session` drives atari800's monitor: `sync('EXE_PAUSE')` stops at a label
  from `fastbasic -g`, then `var('X')`, `mem(addr, n)` and `time()` read memory
  exactly.

Fix the machine so a personal configuration can't change results: 800XL,
AltirraOS, BASIC off, artifacting off, its own config file.

### Keys

- **Hold every key for at least a frame.** atari800 reads the keyboard once a
  frame, so a bare `xdotool key h` can come and go between reads:
  `xdotool keydown h; sleep 0.1; xdotool keyup h`.
- Joystick on the numeric keypad: KP_8 up, **KP_5 down** (not KP_2), KP_4 left,
  KP_6 right, **Control_R** fire. START/SELECT/OPTION on F4/F3/F2.
- After a crash, a stale X lock blocks the next run:
  `rm -f /tmp/.X99-lock /tmp/.X11-unix/X99`.

### Screenshots

- atari800's default window crops a few scanlines at the top (the border strip
  where `POKE 712` shows with DMA on) and the bottom of a tall display. Check
  inside the visible area.
- Player pixels over lit text take a different luminance; a silhouette check
  must accept both.

## Lost frames: `fbframes`

```sh
python3 tools/fbframes.py game.bas --seconds 10 --runs 3 \
  --keys "xdotool keydown KP_8; sleep 5; xdotool keyup KP_8"
```

The program needs exactly one `PAUSE` in its main loop. The tool adds one
`INC` before it (0.7 units), stops the program at that PAUSE twice through the
monitor, `--seconds` apart, and reads TIME and the counter. Jiffies elapsed
minus passes made is frames lost, in emulated time, so a slow host can't fake
one.

Write scenarios: idle, the busiest thing a player can do, the worst case you
can think of (fire held, keys hammered, everything on screen at once). A change
is kept only if every scenario reads 0, or you have written down why a
scenario doesn't matter.

## Statement timing: `fbbench`

```
[setup]
R = 7
[block mul8]
K = R * 8
[block shifts]
K = R * 4 * 2
```

`fbbench.py FILE.bench -n 1000` runs each block N times in a FOR loop,
subtracts the empty loop, and prints units of 2 scanlines (131 per NTSC frame)
per pass. `--pal` for PAL.

## Where a frame goes: VCOUNT stamps

`POKE RING + 32 * K + P, PEEK(54283)` at point K (P the pass number & 31)
costs about 2.2 units. A section's cost is the difference of two stamps modulo
131 (as long as no section exceeds a frame). Read the ring from the monitor and
take medians, p90 and maxima over many passes. Don't build a stopwatch from
TIME and VCOUNT together: TIME ticks somewhere between VCOUNT 122 and 3,
varying frame to frame, so a sample near the blank can be a frame off.

Profile with stamps, then **remove them** before counting lost frames.

## Autoplayers by substitution

Make the game play itself by substituting an input expression in the source
before compiling the test build: replace `STRIG(0)` with an expression that
fires when the ball is near a flipper, or `STICK(0)` with one that steers
toward the nearest dot. The shipped source stays untouched, and long soak runs
(thousands of frames) exercise rare paths.

## Gotchas

- **An emulated frame ends after the vertical blank**, and PAUSE returns inside
  it, so when a frame step returns, the next pass's display writes have already
  run. Variables and registers read then belong to the next frame. Judge only
  frames whose state didn't change across the step.
- Tracing, probes and stamps add cost. Never read lost frames from an
  instrumented build.
- Test boot three ways: BASIC off, BASIC on, PAL. `$A000-$BFFF` is ROM with
  BASIC on.
- Real hardware starts with random RAM; the emulator may start with zeros.
  Clear what you use.

## Regression discipline

- Changes that must not change the program (renames, reordering an expression,
  removing parentheses) have the strongest test: **the compiled XEX is
  byte-identical**. Compare hashes.
- Keep a history table: version, size, frames lost per scenario, what changed.
  Keep rejected ideas with the measurement that rejected them.
