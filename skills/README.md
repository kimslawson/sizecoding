# Agent skills for FastBasic

Two [Agent Skills](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
that teach an AI assistant what this guide teaches people: how to write FastBasic for the
Atari 8-bit that runs on time, and how to make it small enough for the BASIC 10Liner contest.

| Skill | Use it for |
|---|---|
| [`fastbasic`](fastbasic/SKILL.md) | Any FastBasic program: language traps, toolchain and linking ca65, memory, the frame budget and statement costs, display lists, DLIs, players, collisions, POKEY, emulator test harnesses, FujiNet networking |
| [`fastbasic-sizecoding`](fastbasic-sizecoding/SKILL.md) | Character-count golfing: the size-trick catalogue, packing ten lines, data in listings, workflow, the contest rules and submission, and techniques from finished ten-liners |

`fastbasic-sizecoding` builds on `fastbasic`; install both. For register-level hardware
detail and 6502 assembly, pair them with ilmenit's
[atari-800-skills](https://github.com/ilmenit/atari-800-skills), which these defer to.

## Install

- **Claude apps**: zip each skill folder (the folder itself, with `SKILL.md` at its top) and
  upload it under Settings > Capabilities > Skills.
- **Claude Code**: copy or symlink both folders into `~/.claude/skills/` (or a project's
  `.claude/skills/`).
- **Other agents**: each `SKILL.md` is a router; point the agent at it and let it open the
  `reference/` files it needs.

`fastbasic/scripts/setup.sh` sets up FastBasic 4.7, fbp, this repo's tools and atari800 in
a fresh Debian or Ubuntu machine, so an agent can compile, measure and test what it writes.

## Where the facts come from

The numbers are this repo's measurements ([`bench/`](../bench/), [`tests/`](../tests/)) and
those of finished FastBasic games, generalized. [`tests/skills.py`](../tests/skills.py) checks
the claims the skills add beyond `docs/` against the compiler and, with `--run`, in atari800:
what must and mustn't compile per target, values of the precedence and expression tricks, and
that every integer `SIO` equivalent of a FujiNet statement leaves the same SIO control
block. If a skill and a page in [`docs/`](../docs/) disagree, the page (with its test) wins;
open an issue.

## License

The skill text is [CC BY 4.0](../LICENSE-docs), like the rest of the writing here;
`setup.sh` is [MIT](../LICENSE).
