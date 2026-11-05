# FujiNet networking from FastBasic

FujiNet is an SIO peripheral that gives an Atari network access through its
`N:` device: HTTP(S), TCP, UDP and more, addressed by URL. This page covers
reaching it from FastBasic and designing games around its latency. For the CIO
handler, SIO protocol details and assembly, see the atari8bit skill
(exotics/fujinet.md).

## The statements

The floating point target (`-t:atari-fp`, the default) includes `fujinet.syn`:

| Statement | Short | Does |
|---|---|---|
| `NOPEN unit, mode, trans, url$` | `NO.` | open network unit 1-8 on a URL |
| `NSTATUS unit` | `NS.` | status into DVSTAT ($02EA) |
| `NGET unit, addr, len` | `NG.` | read len bytes to addr |
| `NPUT unit, addr, len` | `NP.` | write len bytes from addr |
| `NCLOSE unit` | `NC.` | close |
| `SERR()` | | the last SIO status (DSTATS, $0303) |

- Modes: 4 read (HTTP GET), 6 directory, 8 write (PUT), 12 read/write (TCP,
  UDP), 13 POST.
- Translation: 0 none, 1 CR to EOL, 2 LF to EOL, 3 CR and LF to EOL. With 0 you
  parse LF (byte 10) yourself.
- After `NSTATUS`: `DPEEK($2EA)` bytes waiting, `PEEK($2EC)` connected (0 =
  closed), `PEEK($2ED)` last error.
- **Never `NGET` more than NSTATUS reported waiting**: asking for more is an SIO
  error. Asking for exactly what is waiting returns at once.
- Build URLs in a string variable with `=+` (`U$ = "N:HTTPS://host/" : U$ =+ "path"`).
  The FastBasic manual limits constant URL strings to 127 characters.
- FujiNet reads the URL up to an end of line or a zero byte. `NOPEN` sends 256
  bytes starting at the string's first character, so make sure a terminator
  follows the URL (append `$9B` if in doubt). Not yet confirmed on hardware
  whether a string buffer's leftover bytes can break this.

### These are SIO calls, so the integer target can use them too

Each statement just fills the SIO device control block for device $71
(FujiNet's network device) and calls SIOV ($E459); no `N:` CIO handler is
involved. The `SIO` statement, which the integer target has, does the same:

```
SIO ddevic, dunit, dcomnd, dstats, dbuf, dtimlo, dbyt, daux1, daux2
```

| Floating point | Integer equivalent |
|---|---|
| `NOPEN N, M, T, S$` | `SIO $71, N, $4F, $80, &S$ + 1, $1F, 256, M, T` |
| `NSTATUS N` | `SIO $71, N, $53, $40, $2EA, $1F, 4, 0, 0` |
| `NGET N, A, L` | `SIO $71, N, $52, $40, A, $1F, L, L & 255, PEEK(&L + 1)` |
| `NPUT N, A, L` | `SIO $71, N, $57, $80, A, $1F, L, L & 255, PEEK(&L + 1)` |
| `NCLOSE N` | `SIO $71, N, $43, 0, 0, $1F, 0, 0, 0` |

(N is the unit; a variable N and a string N$ would collide, so the URL is S$.)

This mapping is read from `fujinet.syn` and `sio.syn` in the FastBasic 4.7HF
release, where `sio.syn` is part of the base target (`a800.tgt`) and
`fujinet.syn` is added only by `atari-fp.tgt`. Confirm the table on FujiNet
hardware or FujiNet-PC before relying on it.

## Blocking versus non-blocking

SIO calls block the CPU while the transfer runs, and the OS skips the second
stage of its vertical blank while SIO is busy (CRITIC is set), so DLI tables
indexed by COLRSH and the CHBAS shadow aren't refreshed: the display can glitch.

- **Turn-based or session-based games**: do network I/O only at natural pauses
  (start of a run, death, a level change, a "descending..." screen). The
  transition hides the latency.
- **Real-time games**: never wait on the network inside the frame. Each frame,
  `NSTATUS`; if at least one packet is waiting, `NGET` exactly that much (it
  returns immediately). Send on a slower schedule (every 3rd frame is about
  20 Hz).

## Real-time design (from ballblazer-mp)

[ballblazer-mp](https://github.com/kimslawson/ballblazer-mp) links two Ataris
over FujiNet for a 60 Hz action game. Its netcode is assembly, but the design
transfers directly to FastBasic:

- **Not lockstep.** Exchanging inputs and simulating identically makes every
  machine stall until the other's input arrives; one round trip is many
  frames.
- **Local authority plus dead reckoning.** Each machine owns its own player and
  simulates it from the local joystick with zero added latency. It sends its
  true state; the other machine mirrors it and extrapolates from the last
  velocity every frame, snapping (or easing) to the truth when a packet lands.
  Your own craft feels native; only the remote one is ever slightly behind.
- **One authority for shared objects.** A ball or a score can't be owned by
  both machines. The host simulates it and broadcasts it; the client accepts it
  only from a packet flagged as the host's.
- **Fixed-size packets.** 16 bytes: magic/version, sequence number, ack, flags,
  position (8.8 fixed point), velocity, heading, the shared object's state, an
  event field, an XOR checksum. Fixed size means no framing: read whole
  multiples of the packet length, and the newest wins.
- **UDP snapshots.** Every packet is a full snapshot, so a lost one costs one
  stale tick and nothing retransmits. At 20 Hz, 16 bytes is about 320 bytes a
  second each way.
- **Detect a dead link** from DVSTAT's connected byte going to 0, or a long gap
  in incoming sequence numbers. Ignore packets older than the newest applied.
- **Test without two machines**: a PC program speaking the same packet format
  over UDP stands in for the other player.

In FastBasic: keep the packet in a DIMmed byte array, `NGET` straight into it,
check the magic byte and checksum, and copy fields with `PEEK`/`DPEEK`. Keep the
per-frame parsing to a few statements; dead reckoning is two adds per axis.

## Relayless HTTP designs

When a program can use only public, keyless services (the BASIC 10Liner rules
allow no code or configuration outside the listing), shared state has to live
in something like a public message topic reached by plain HTTP GET.

Patterns that work:

- **Asynchronous multiplayer.** Players never meet. Each one's actions leave
  traces others find later (a failure leaves a marker, a success leaves a
  message). Latency becomes part of the fiction.
- **Shared generator plus event replay.** Every machine runs the same
  procedural generator from the same seed, so a cell number means the same
  place everywhere. The network carries only events (`K517`: something at cell
  517 was killed). Replaying events onto the generated level doubles as
  validation: an event applies only if the generated cell holds what it names,
  so junk falls through every rule. Moving monsters break this (a cell no
  longer names a spawn); keep shared things static.
- **Server time as the clock.** The Atari has no real-time clock. A service
  whose publish response includes the server time gives a day number for a
  daily seed.
- **Digits-only payloads** need no URL encoding on the Atari.
- **Parse while reading.** Read fixed chunks (256 bytes) into a state machine
  (letter = opcode, digits accumulate, LF applies) rather than buffering the
  whole response. A full buffer drops the newest events, which is the wrong end
  to lose.
- **Queue and flush** writes at natural pauses rather than per action.
- **Accept eventual consistency.** No atomicity: two players can take one
  chest. Public topics mean anyone can read or forge them; nothing in a public
  listing can be secret.
- **Real-world data** (keyless weather, tide or buoy feeds) can seed a level.
  FujiNet's JSON channel mode can extract one value without a BASIC parser.

## Service limits to design around

For ntfy.sh, a public pub/sub service reachable by GET (checked live with curl
in late 2026; limits change, recheck them):

- Publish: `https://ntfy.sh/TOPIC/publish?message=517`. The response is JSON
  including the server time.
- Poll: `https://ntfy.sh/TOPIC/raw?poll=1` returns one message body per line,
  LF-terminated, **oldest first**. Messages live 12 hours.
- Anonymous limits: 250 messages per day per IP, a request bucket of 60
  refilling one per 5 seconds (polls count), 4,096-byte bodies.
- **Shared IPs share the quota**: everyone on one convention or party Wi-Fi
  shares one 250-message budget. Plan demos around that.
- **Read-after-write lag**: a poll right after publishing has come back empty
  and been correct about 3 seconds later. Don't rely on reading your own post
  at once.
- Scheduled delivery (a delay of 10 seconds to 3 days) exists as a header;
  whether it works as a query parameter on a GET publish was not yet verified.

## Open questions to settle on real hardware

Recorded as unverified; test with FujiNet hardware or Altirra plus FujiNet-PC:

1. Whether a read loop that stops when `NSTATUS` reports 0 bytes waiting can
   exit before an HTTP body arrives (possible fix: also loop while the
   connected byte at $2EC is set).
2. Whether `NOPEN` followed by `NCLOSE` sends an HTTP GET by itself, or an
   `NSTATUS` is needed between them.
3. Whether a long-lived HTTP stream stays open so that `NSTATUS` each frame
   gives real-time push without a server of your own.
4. For UDP, whether your firmware sends to the address in the open URL or needs
   a separate "set destination" command.
