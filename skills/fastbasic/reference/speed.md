# Speed

## The unit and the budget

- An NTSC frame is 262 scanlines. VCOUNT (54283, $D40B) counts them in pairs,
  so the unit is **2 scanlines: 131 per NTSC frame, 156 per PAL frame**. One
  unit is 228 machine cycles of wall time.
- Wall time includes ANTIC's DMA (text modes steal heavily on every character
  line; players a little) and the OS interrupts. The numbers below were measured
  on a GRAPHICS 0 screen with `fbbench` (FastBasic 4.7, atari800, NTSC).
  Resolution is about 0.13 units.
- `PAUSE` waits for the next vertical blank. A pass that ends after the blank
  waits for the following one: a lost frame, and `TIME` moves by 2.
- A pass that starts right after `PAUSE` starts about 10 scanlines into the
  vertical blank, so a two-frame pass has about 514 scanlines, not 524.

## What statements cost (units)

| Statement | Units |
|---|---|
| `INC K` | 0.7 |
| `K = 3` | 1.1 |
| `K = R` | 1.2 |
| `K = K + 1` | 1.6 |
| `K = R + B` | 2.0 |
| `K = R * 2` / `* 4` / `* 256` | 1.6 / 1.8 / 1.4 |
| `K = R * 8`, `K = R * 40` | 5.4 to 5.5 |
| `K = R / 2`, `R / 8`, `R MOD 8` | 5.4 to 5.6 |
| `K = R & 7` | 2.2 |
| `K = T / 256` | 6.9 |
| `K = PEEK(&T + 1)` | 2.2 |
| `K = (R > 9) * 7` | 6.2 |
| `K = -(R > 9) & 7` | 3.3 |
| `K = PEEK(1536)`, `DPEEK(1536)` | 1.4 |
| `K = X(3)` (word or byte array) | 2.0 to 2.1 |
| `K = TIME` | 0.9 |
| `K = STICK(0)`, `STRIG(0)` | 1.3 to 1.4 |
| `K = RAND(10)` | 3.7 |
| `POKE 1536, R` | 1.1 |
| `DPOKE 1536, B * 256 + R` | 2.5 |
| `SOUND 0, R, 10, 8` | 3.7 |
| `PMHPOS 0, R` | 1.2 |
| `MOVE 1536, 1600, 9` | 3.7 |
| `MSET 1536, 12, 0` | 3.0 |
| `IF R = 5 THEN K = 3`, false | 1.7 |
| `IF R = 100 THEN K = 3`, true | 2.8 |
| `IF R = 5 AND B = 7 THEN ...` | 3.7 |
| nested `IF R = 5` / `IF B = 7`, first false | 1.7 |
| `EXEC P` (empty PROC) / with one parameter | 0.8 / 2.8 |
| `POSITION 2, 2 : PRINT "A";` | 5.9 |
| `IF A$ = "HELLO" THEN K = 1` | 4.5 |
| `FOR J = 1 TO 10 : NEXT J` | 17.0 (about 1.7 per pass) |

Bulk operations: `MOVE` copies about 9 bytes per unit, so copying a
2,000-byte screen costs about 1.7 frames.

**Real statements cost more than these rows.** Statements that read arrays and
compute addresses ran 2.5 to 3 units each when a whole game was profiled
section by section. A 60 fps frame holds roughly 45 of them, a 30 fps pass about
90. Count the statements on your busiest pass before writing them.

## Multiply and divide

The 6502 has neither. FastBasic's peephole optimizer turns `*2`, `*4` and `*256`
into shifts and calls a routine for every other multiply, every divide (`/2`
too) and every `MOD`: about 5.5 units, nearly three adds.

| Instead of | Units | Use | Units |
|---|---|---|---|
| `K = R * 8` | 5.50 | `K = R * 4 * 2` | 2.10 |
| `K = R * 16` | 5.37 | `K = R * 4 * 4` | 2.36 |
| `K = R * 3` | 5.50 | `K = R * 2 + R` | 2.23 |
| `K = R * 40` | 5.50 | `K = (R * 4 + R) * 4 * 2` | 3.27 |
| `K = R * 40` | 5.50 | `K = W(R)`, a table filled at startup | 2.62 |
| `K = A + J * 40` in a loop | 6.42 | `A = A + 40`, a running pointer | 1.70 |
| `K = R MOD 3` on a counter | 5.37 | `INC C : IF C = 3 THEN C = 0` | 2.62 |
| `K = T / 256` | 6.94 | `K = PEEK(&T + 1)` | 2.23 |
| `K = PEEK(ADR(T) + 1)` | 2.23 | `K = PEEK(AT)`, `AT = ADR(T) + 1` kept | 1.57 |

- Build constants from shifts and adds; `(R * 4) * 2` has no constant to fold,
  so the compiler keeps both shifts.
- Walk pointers instead of indexing. Counters that wrap instead of `MOD`.
- Tables, filled once: row offsets, pitch tables, projection tables. Divide
  once when an input changes, not every frame.
- Keep values in the unit you need: 8.8 fixed point gives the integer part as
  `PEEK(&X + 1)`.
- `(c) * k` is 6.2 units; `-(c) & k` is 3.3 for the same value.

## Rules from games that had to fit

- **Write the hardware first.** All display writes (scroll registers, LMS,
  player positions, PM shapes, display-list jumps) in one block right after
  `PAUSE`, from values computed at the end of the previous pass. In one game,
  doing the frame maths first pushed the sprite writes to scanline 100 and tore
  the sprites on the top rows; moving the writes first finished them by
  scanline 10 and removed every torn frame.
- **Overruns lock onto a parity.** If jobs are scheduled by `TIME & 1` and a
  busy job overruns, the next pass starts two jiffies later, on the same parity,
  runs the same job, and overruns again. The jobs on the other parity stop.
  Either guarantee every pass fits, or schedule from your own pass counter.
- **Don't catch up.** Moving objects once per elapsed frame after an overrun
  makes the next pass heavier: a spiral. Do **fixed work per pass** and let the
  game slow down under load, or run a fixed tick (every pass two frames, motion
  scaled to match) and only catch up on rare overruns.
- **Idle frames should be cheap.** Code that looks for work pays full price
  every frame. Set a flag where work is created and look only when it's up;
  skip what can't change (a parked ship needs no gravity, collisions or redraw);
  write a register only when its value changes. A sound engine that wrote POKEY
  every frame from formulas cost 96 units; tables plus writes only on change
  cost 5 to 17.
- **Step things by due time.** For several actors at different speeds, keep a
  "next due" time per actor and step at most one per pass (`IF TM >= N0`). An
  idle pass then costs a comparison per actor, and actors never all land on the
  same pass.
- **Dead zones.** A camera that moves only when the player nears the view's
  edge costs nothing on most passes and recomputes nothing when still.
- **One job per frame.** An ELIF chain on `TIME` runs exactly one heavy job;
  the frame costs the every-frame work plus the largest single job, not the sum.
  Put the arm for the tightest frame first: every failing test costs about 1.7.
- **Watch "on top of" work.** Anything triggered by input or collisions lands on
  top of that frame's scheduled job. Make it cheap, or decide with numbers that
  the rare overrun is acceptable.
- **Probes cost time.** A timing stamp costs about 2.2 units; a traced or
  instrumented build runs slower. Never read lost frames from an instrumented
  build.

## Scheduling skeleton

```
DO
  PAUSE
  ' display writes, from values computed last pass
  ' every-frame work: input, motion, sound changes
  IF TIME & 3 = 0
    ' a 15 Hz job
  ELIF TIME & 1
    ' a 30 Hz job
  ELIF TIME & 7 = 6
    ' a once-in-8 job
  ELSE
    ' a cheap filler, e.g. one status digit
  ENDIF
  ' compute next pass's display values
LOOP
```

## PAL

- Detect with `PEEK(53268)`: GTIA's PAL register ($D014) reads 1 on PAL, 15 on
  NTSC. `PEEK(53268) & 10 + 50` is 50 or 60 (precedence makes it `(P & 10) + 50`).
- A PAL frame has 156 units of time and 50 frames a second, so per-second
  throughput is about the same as NTSC.
- To run at the same wall-clock speed on both, count time in a unit both divide
  evenly, e.g. ticks of 1/120 s: `U = (TIME - T0) * 2` on NTSC,
  `U = (TIME - T0) * 12 / 5` on PAL, and show each picture at the first frame
  where U reaches its due tick. Games that run 60 Hz logic once per PAL frame
  play 17% slow.
- A clock that advances by exactly one second's jiffies per second (50 or 60)
  never drifts; never resynchronize it to TIME.

## Measuring

See reference/testing.md: `fbbench` for statements, `fbframes` for lost frames
while a script plays, VCOUNT stamps for where a frame goes.
