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
  more than an add (5.5 against 2.0). `MOD` is a divide too.
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
