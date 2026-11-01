#!/bin/sh
# Runs a command in the fb-sizecoding container with the current directory at /work and a
# virtual display for atari800. From this repo:  tools/docker/run.sh python3 tests/tricks.py --run
exec docker run --rm -v "$PWD":/work -w /work fb-sizecoding sh -c \
  'Xvfb :99 -screen 0 1024x768x24 >/dev/null 2>&1 & sleep 1; export DISPLAY=:99; "$@"' sh "$@"
