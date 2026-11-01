# 5. Speed

A ten-liner is small, but it still has to run once per frame, every frame. FastBasic is fast
for a BASIC, and a ten-line game can still overrun a frame without anyone noticing until it
stutters. This chapter is about knowing, not guessing.

## The frame budget

- An NTSC frame is 262 scanlines. VCOUNT ($D40B) counts them in pairs, so the natural unit is
  **2 scanlines: 131 units per frame** on NTSC, 156 on PAL. A unit is 228 machine cycles of
  wall time.
- Wall time is what matters, and it includes ANTIC's DMA (text modes steal a lot of cycles on
  every character line, players steal a few) and the OS's interrupts. All the numbers below
  were measured on a GRAPHICS 0 screen; a blank screen is faster, a text screen with players
  slower.
- `PAUSE` waits for the next vertical blank. A pass that ends after the blank has already
  happened waits for the one after it: the frame is lost, and `TIME` moves by 2 during that pass.

## Why "usually fits" isn't good enough

Games share out heavy work by frame number (below). Suppose the missile moves on even frames,
and a busy missile frame overruns by a few cycles. The next pass starts two jiffies later, on
an even frame again, so it's a missile frame again, and if it's just as busy it overruns
again. The overruns lock onto one parity: the jobs scheduled on odd frames stop running and
the game visibly stutters. A pass that overruns by a few cycles costs much more than a few
cycles.

So the rule is: **every pass, every frame, every scenario.** A size saving that loses frames
isn't a saving.

## What statements cost

Measured with [`tools/fbbench.py`](../tools/README.md) (FastBasic 4.7, atari800, NTSC, GRAPHICS
0); the bench files and raw results are in [`bench/`](../bench/). Resolution is about 0.13
units, so treat the second decimal as noise.

| Statement | Units |
|---|---|
| `INC K` | 0.7 |
| `K = 3` | 1.1 |
| `K = R` | 1.2 |
| `K = R + B` | 2.0 |
| `K = K + 1` | 1.6 |
| `K = R * 2` | 1.6 |
| `K = R * 4` | 1.8 |
| `K = R * 256` | 1.4 |
| `K = R * 8`, `K = R * 40` | 5.4 to 5.5 |
| `K = R / 2`, `K = R / 8`, `K = R MOD 8` | 5.4 to 5.6 |
| `K = R & 7` | 2.2 |
| `K = T / 256` | 6.9 |
| `K = PEEK(&T + 1)` | 2.2 |
| `K = (R > 9) * 7` | 6.2 |
| `K = -(R > 9) & 7` | 3.3 |
| `K = PEEK(1536)`, `K = DPEEK(1536)` | 1.4 |
| `K = X(3)` (word or byte array) | 2.0 to 2.1 |
| `K = TIME` | 0.9 |
| `K = STICK(0)`, `K = STRIG(0)` | 1.3 to 1.4 |
| `K = RAND(10)` | 3.7 |
| `K = ABS(R)`, `K = SGN(R)` | 1.4 to 1.6 |
| `POKE 1536, R` | 1.1 |
| two POKEs | 2.1 |
| `DPOKE 1536, B * 256 + R` | 2.5 |
| `DPOKE 53760, 168 * 256 + R` | 2.1 |
| `SOUND 0, R, 10, 8` | 3.7 |
| `PMHPOS 0, R` | 1.2 |
| `MOVE 1536, 1600, 9` | 3.7 |
| `MSET 1536, 12, 0` | 3.0 |
| `IF R = 5 THEN K = 3`, false | 1.7 |
| `IF R = 100 THEN K = 3`, true | 2.8 |
| `IF R THEN K = 3`, true | 2.1 |
| `IF R = 5 AND B = 7 THEN ...` | 3.7 |
| `IF R = 5` / `IF B = 7 THEN ...` nested, first false | 1.7 |
| `EXEC P` (empty PROC) | 0.8 |
| `EXEC Q R` (one parameter) | 2.8 |
| `POSITION 2, 2` | 1.2 |
| `POSITION 2, 2 : PRINT "A";` | 5.9 |
| `POKE` one screen byte | 0.9 |
| `IF A$ = "HELLO" THEN K = 1` | 4.5 |
| `FOR J = 1 TO 10 : NEXT J` | 17.0 |

### Rules of thumb

- **Only ×2, ×4 and ×256 are cheap.** FastBasic's optimizer turns those into shifts. Every
  other multiply, including ×8 and ×16, and *every* divide, including /2, costs 3 to 4 units
  more than an add (5.5 against 2.0). `MOD` is a divide too. They are the frame-killers: see
  [below](#multiply-and-divide-the-frame-killers) for what to use instead.
- **Read a high byte with `PEEK(&X+1)`**, never `X/256`: 4.7 units cheaper, 3 characters
  longer.
- **`-(c)&k` instead of `(c)*k`**: the same value, one character longer, about 3 units cheaper.
- **AND evaluates both sides.** When the first condition is usually false, a nested IF skips
  the second test. Order IF and ELIF tests so the common case is decided first.
- **Every failing IF or ELIF test costs about 1.7 units** on every frame that reaches it. In a
  long ELIF chain, put the arm that runs on the tightest frame first.
- **The OS is slow, memory is fast.** PRINT goes through the OS; a POKE into screen memory is
  0.9 units.
- **Loops inside a frame add up fast.** A FOR loop costs about 1.7 units per pass before its
  body does anything. MOVE and MSET do the same work in one statement.

### Real statements cost more than these rows

The table times single, simple statements. A game's statements read arrays, do address
arithmetic and call functions: `K = PEEK(ADR(X) + J * 2 + 1)` is 3.27 units, `K = A + J * 40`
6.42 ([`bench/muldiv.txt`](../bench/muldiv.txt)). Profiling a whole game section by section,
its statements averaged 2.5 to 3 units each. So a 60 fps frame holds roughly 45 of them, and a
30 fps pass (262 units) about 90, before anything you didn't count. Count the statements on
your busiest pass and multiply before you write them.

## Multiply and divide: the frame-killers

The 6502 has no multiply and no divide instruction. FastBasic turns ×2, ×4 and ×256 into
shifts and calls a routine for everything else, so every other multiply, every divide (/2 too)
and every `MOD` costs about 5.5 units, almost three adds. On a busy pass they are usually the
biggest cost there is, and most of them can go. Measured in
[`bench/muldiv.bench`](../bench/muldiv.bench) ([results](../bench/muldiv.txt)):

| Instead of | Units | Use | Units |
|---|---|---|---|
| `K = R * 8` | 5.50 | `K = R * 4 * 2` | 2.10 |
| `K = R * 16` | 5.37 | `K = R * 4 * 4` | 2.36 |
| `K = R * 3` | 5.50 | `K = R * 2 + R` | 2.23 |
| `K = R * 40` | 5.50 | `K = (R * 4 + R) * 4 * 2` | 3.27 |
| `K = R * 40` | 5.50 | `K = W(R)`, a table filled at startup | 2.62 |
| `K = A + J * 40`, each pass of a loop | 6.42 | `A = A + 40`, a running pointer | 1.70 |
| `K = R MOD 3`, on a counter | 5.37 | `INC C : IF C = 3 THEN C = 0` | 2.62 |
| `K = T / 256` | 6.94 | `K = PEEK(&T + 1)` | 2.23 |
| `K = PEEK(ADR(T) + 1)` | 2.23 | `K = PEEK(AT)`, with `AT = ADR(T) + 1` kept | 1.57 |
| `W = (TIME - T1) * 131 + V` | 8.12 | `W = F((TIME - T1) & 7) + V`, F a table | 6.29 |

The ways out, roughly in the order they apply:

- **Build constants from shifts and adds.** ×8 is ×4×2, ×5 is ×4 plus itself, ×40 is ×5×8.
  `(R * 4) * 2` has no constant to fold, so both FastBasic and fbp keep the two shifts. (They
  cost characters: [Size tricks](03-size-tricks.md#speed-for-characters) has the counts.)
- **Walk, don't index.** In a loop over rows, cells or slots, keep an address and add the
  stride each pass instead of multiplying the index; one pointer per level of a nested loop.
  The same goes for anything that counts along: a counter that wraps beats `MOD`.
- **Tables, made once.** Row offsets (`W(R) = R * 40` for 24 rows), slot numbers for a ring
  of buffers, an address for each array element you PEEK often. Fill them at startup or when
  the thing they depend on changes, never in the frame.
- **No divides in the frame.** There is no cheap one. Keep values in the unit you need (the
  high byte of an ×256 fixed-point value is a PEEK away), divide once when something changes,
  or keep a second variable in the other unit.
- **Let the bits pick.** Lay data out on power-of-two strides and a mask does what a divide or
  a multiply would: four 8-byte animation frames 8 bytes apart start at `ANIM & 24`, which is
  `(ANIM / 8 & 3) * 8` without either.
- **Hoist what only changes with settings.** `60 / FPS` or a speed scaled by the frame rate
  belong in the code that runs when the setting changes.

## Idle frames should be cheap

The most expensive frame can be the one where nothing happens. Code that *looks* for work
pays full price every frame, finding something or not: checking 9 slots for one that needs
rebuilding, with 2 multiplies, 2 `MOD`s and a few tests per slot, is about
9 × (1.7 + 4 × 5.5 + 5) ≈ 260 units: a whole 30 fps pass, spent finding nothing.

- **Set a flag where the work is created** (a flip, a finished job, a setting changed) and only
  look when it's up; let the search clear it when it comes back empty.
- **Skip what can't change.** A ship sitting on a landing pad doesn't need gravity, collisions,
  movement or a sprite redraw. A loop over shots doesn't need to run with no shots in flight.
- **Write the hardware only when the value changes.** A sound register, a player's position or
  its shape.

## Timing inside your program

`fbframes` and `fbbench` time from the outside. To see where a running game's frame goes, take
VCOUNT snapshots: one `POKE RING + 32 * K + P, PEEK(54283)` at each point K, with P the pass
number & 31, costs 2.23 units. A section's cost is the difference between two snapshots modulo
131, as long as no section is longer than a frame; read the ring from the emulator's monitor
(`emu.Session.mem` in [tools/emu.py](../tools/emu.py)) and take medians and maxima over the
32 passes.

Don't build a stopwatch from TIME and VCOUNT together. TIME ticks somewhere between VCOUNT 122
and 3, and the exact line moves from frame to frame ([`bench/vctime.py`](../bench/vctime.py),
[results](../bench/vctime.txt)), so a sample taken near the vertical blank can be a whole frame
off; and each mark costs 6 to 8 units. If you use one anyway, trust averages, not maxima: the
maximum will eventually catch a sample a frame off.

## Scheduling: give heavy jobs their own frames

Most of a game doesn't need to run every frame. Use the jiffy counter to decide what runs:

```
DO
  ' every frame: input, thrust, scrolling, sound
  IF TIME & 3 = 0
    ' rotation, 15 times a second
  ELIF TIME & 1
    ' the missile, on odd frames (30 Hz)
  ELIF TIME & 7 = 6
    ' the once-in-8-frames job: drag, clock, colors
  ELSE
    ' something cheap: one digit of the status line
  ENDIF
  PAUSE
  ' write everything the hardware reads, here, right after PAUSE
LOOP
```

- **One job per frame.** An ELIF chain runs exactly one arm, so the cost of a frame is the
  every-frame work plus the most expensive single job, not the sum. It's also cheaper in
  characters than separate IFs, which each need an ENDIF and a condition.
- **The status line is a good filler.** Printing one digit per frame keeps it current without
  ever costing more than one digit's work.
- **Write the hardware right after PAUSE.** Compute positions during the pass and write
  VSCROL, the LMS address and player positions at the top of the next one. They all change
  inside the vertical blank, together, and nothing is ever seen half-updated.
- **Watch for "on top of" work.** Anything that runs on *any* frame when some condition is true
  (a key held down, a collision) lands on top of whatever job that frame already has. Either
  make it cheap or decide, with numbers, that the rare overrun is acceptable.

## Counting lost frames

[`tools/fbframes.py`](../tools/README.md) answers "does every pass fit?" for your actual game,
with your actual input:

```sh
python3 tools/fbframes.py game.bas --seconds 10 --runs 3 \
  --keys "xdotool keydown KP_Up; for i in \$(seq 16); do xdotool keydown Control_R; sleep 0.3; xdotool keyup Control_R; sleep 0.25; done; xdotool keyup KP_Up"
```

It adds one `INC` before your loop's PAUSE (0.7 units), then uses the emulator's monitor to stop
the program exactly at PAUSE twice, ten seconds apart, and reads `TIME` and the pass counter
from memory. Jiffies elapsed minus passes made is the number of frames lost. The count is in
emulated time, so a slow host can't fake a lost frame; it can only shift when the key presses
land.

Make a few scenarios: idle, the busiest thing a player can do, and the worst case you can
think of. A change that saves characters gets kept only if every scenario still reads 0, or if
you've decided, knowingly, that a scenario doesn't matter.

## When size and speed disagree

They often will: a division is shorter than a mask, a multiply shorter than an AND. Decide your
priority up front and measure every trade. A good default: **keep every frame on time, then
make it small.** When a saving costs time, look for the time somewhere else (a cheaper
expression on the same frame, a job moved to a quieter frame) before giving up the saving. And
when a speed fix costs a lot of characters for a case nobody will hit in play, it's fine to
leave it out. Write down why.
