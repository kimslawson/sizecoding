# Techniques from finished ten-liners

Patterns that shipped (or were measured and rejected) in real FastBasic
ten-liners, described by mechanism. Costs are units of 2 scanlines (131 per
NTSC frame). The register-level how-to for each is in the fastbasic skill's
reference/hardware.md.

The common thread: **BASIC can't do much per frame, so design so the hardware
does the per-frame work** and BASIC only changes a few registers.

## Displays

### A view onto any memory, one DPOKE a frame

Make one line of the OS display list an LMS (`POKE D+6, 98`: mode 2 + LMS +
VSCROL) and the bytes after it become the address of everything below.
`DPOKE D+7, A` points the view anywhere in RAM; VSCROL plus an 8.8 fixed-point
position gives smooth vertical motion. A playfield that shows raw memory needs
nothing else. Mind ANTIC's 4K wrap when mapping a screen
position back to an address: `A & -4096 ! ((A + OFFSET) & 4095)`.

### Two-axis scrolling over a big map

A display list per horizontal coarse position, each in its own page, every map
row with its own LMS; a fixed header JMPs into the cache. One DPOKE picks the
list and row, HSCROL and VSCROL do the fine position: one DPOKE and two POKEs a
frame, values from tables recomputed only when a dead-zone camera moves. Map
rows 64 bytes and 64-aligned keep every fetch inside its row and every line
inside 4K. Verified pixel-exact against map memory at dozens of camera
positions.

### Turning the camera by scrolling a panorama

A free-flying 3D view was measured at 20 to 40 times over a 15 fps budget in
FastBasic (one height sample, about 5.2 units, per column per depth step). If
the camera stays put, everything visible is a cylindrical panorama: ray-cast it
once in BASIC (watch it draw), one column per angle, and turn with HSCROL
across a cache of display lists. Write the list pointer to DLISTL (54274) as
well as its shadow, or every coarse step shows one frame of mismatched fine and
coarse scroll. Players with playfield priority hide behind ridges on their own;
a table maps (object angle - view angle) to a horizontal position so they stay
locked to the terrain while turning.

### Color by line, for free

- DLI tables (`DLI SET X = T INTO 53270`) give a sky gradient, distance fog
  bands, a status line in another hue, without BASIC doing anything per frame.
- Change the *table* for a flash, never toggle the DLI (enabling one costs a
  frame).
- In GTIA mode 10 the border and blank lines show register 704: gradient there
  through 704.
- A road with one LMS per scanline over GTIA pixels shifts each line sideways
  for curves; HSCROL must be even in GTIA modes.

### Lines drawn by moving players per scanline

A DLI on every other line that writes two players' horizontal positions from
DATA tables draws a slanted line in segments, under the text, with no BASIC per
frame. Mirror the second table (`NB(J) = -NA(J)`) for a crossing. Thirteen
interrupts a frame cost about 10% of the BASIC program's speed. A DLI table is
indexed by COLRSH, so `POKE 79, X` from BASIC mid-frame scatters the segments
for the rest of the frame: a glitch effect in one statement.

### Titles and status lines without screen code

- First display list line as mode 7 + LMS pointing at a 20-byte string literal
  of screen codes: a title that never scrolls away.
- Mode 6 status row: color in the top two bits of each byte, digits by
  arithmetic, one digit refreshed per frame.
- Overwrite the OS list's final JVB with a mode line + LMS pointing into the
  data string for a credit line; ANTIC then runs on into zero bytes (blank
  lines) until the vertical blank reloads the list.
- A title down the side, in player 0 at the left margin, from ROM glyphs
  (`c * 8 - 8448`), padded to clear the rest of the player.

### Characters as animation

- Every copy of an object built from the same characters animates with one
  MOVE into the font: all of one kind of flipper, all water tiles.
- Two fonts with the same codes and different art (solid or hollow terrain) are
  one CHBASE POKE apart, with identical collisions.
- Two lines with the same LMS and per-line fonts make tall characters.

## Sprites

- **Equal-height frames, one MOVE**, padded to a common visual center so no
  erase is needed. Nudge frames whose pixel mass is off-center by a color
  clock.
- **Four missiles as one object**, each with its own position and width: a
  sprite that doesn't use a player.
- **Holes in a player** for eyes, windows, cutouts.
- **A state variable as the bitmap** (`POKE Q, K`).
- **Double-buffered PM memory** when shape writes would race the beam: write
  the hidden buffer, flip PMBASE right after PAUSE.
- **Event-driven redraws**: redraw a sprite only when it or the camera moved.

## Physics from collision registers

- **Playfield colors are materials.** Walls in one color register, bouncy
  bumpers in another, one-way surfaces in a third; the collision bits name what
  was hit.
- **A ball of four missiles, one per quadrant**: four PEEKs give the material
  and an 8-direction surface normal, no geometry.
- **Collisions report the frame just displayed.** Undo to the last position and
  reflect if moving into the surface (`v . n < 0`), always nudge out along the
  normal (fixes resting contact and corner pockets). Read every other frame,
  contacts can be two frames deep: undo two frames of velocity.
- **One-way surfaces by contact normal**, not by the velocity's sign.
- **Spin as a phase**: `spin = spin + vx`, phase `(spin / 256) & 7` positions a
  one-pixel mark on the ball; hide it for the far half of the turn.

## Procedural worlds

- **A bijective byte hash.** Build a 256-byte permutation table at boot from the
  seed (two rounds of multiply by an odd number and xor-shift are a bijection
  on bytes). A screen's address plus the table decides everything on it; a new
  seed is a new universe. An LCG whose low nibble repeats every 16 steps put
  pillars in every screen: look at many outputs side by side before trusting a
  generator.
- **Lattice plus marching squares.** Decide rock or space per lattice point;
  fill each cell with a tile for its 4-corner case, drawn from 16 glyphs. Points
  on a screen's right and bottom edges belong to the next screen, so joins are
  exact. Cell shape controls the look: square cells make blobs and caverns,
  wide short cells make ledges and flat landing spots.
- **Mirrored generation** guarantees symmetry and, with the right blocks, no
  dead ends: random dominoes and singles on half a grid, mirrored.
- **Fractal profiles**: three 1D midpoint-displacement profiles, summed and
  warped, make a seamless heightmap.
- **Generate as you go.** One row per frame above the camera, a MOVE of a row
  template plus a DPOKE or two for features, into a ring that wraps with
  `((A + 32) & 4095) ! RING`.
- **Same generator everywhere** for networked games: a cell number means the
  same place on every machine (the fastbasic skill's reference/fujinet.md).

## Loop shapes

- **Fixed tick**: every pass two frames, motion scaled to match; catch up only
  on a rare overrun. A 60 Hz catch-up loop spiraled.
- **Fixed work per pass**: under load the game slows down instead of spiraling.
- **Due-time actors**: each actor has a next-due time, at most one steps per
  pass, and an idle pass costs a comparison per actor. Moving one scrolling game from
  "every actor every pass" to this, plus axis-only camera checks and
  display data prepared only for what moved, took it from 3.15 to about 2.25
  frames per pass.
- **Decisions only where they can change**: mark junctions when the map is
  built and decide directions only there.
- **"Near 30 Hz is enough"** is a design decision. Make it early and write it
  down.

## Sound

- A sound engine computing pitch with divides and multiplies every frame cost
  96 units of 131. Tables at boot and writing every register every frame: 42.
  Tables and writing POKEY only when a value changes: 5 while cruising, 17 on a
  change.
- Gate sound with a mask instead of an IF: `DPOKE 53762, B & 34508`.
- Let one counter be volume and timer: fade, then keep counting silently.

## Big programs in ten lines

- **A trained neural network fits** in EXTREME-256 with its weights as raw
  bytes in DATA: binary weights and activations make dot products into popcount
  lookups, multi-bit weights into bit-planes, and a two-level output keeps the
  per-character cost down. reference/data.md has the arithmetic and packing.
- **Hash the input letters only** (`C = PEEK(A + I) & 95`, keep spaces and
  letters): punctuation the training data never saw stops breaking prompts.
- **Control tokens** below 32 in a generated vocabulary can trigger program
  actions instead of printing; end-of-answer as ATASCII $9B prints a newline for
  free.

## Networked ten-liners

The FujiNet statements need the floating point target (or `SIO` calls from the
integer target), and the rules allow no server code of your own. Design around
asynchronous, relayless play on public services, network I/O only at natural
pauses, and parsing while reading. See the fastbasic skill's
reference/fujinet.md.

## Knowing early that it won't fit

- One full-featured scroller measured 29 lines of 256 against a 10-line limit,
  and 24 with every nice-to-have cut. Measure (fbp `-O` measure / 256 plus
  packing waste) as soon as the core exists, and make a "ladder": the size with
  each feature cut, one at a time.
- Options when it doesn't fit: another category, a smaller design, or a
  non-ten-liner version.
- Some designs need machine code for 60 Hz motion (a vertical blank routine
  playing queued positions). That is not allowed in the contest; redesign
  instead of fighting it.
