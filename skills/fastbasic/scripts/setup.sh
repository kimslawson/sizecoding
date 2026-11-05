#!/bin/sh
# Sets up a FastBasic 4.7 toolchain in a fresh Debian/Ubuntu container or VM:
#   FastBasic 4.7 (cross-compiler + mkatr), fbp, the sizecoding tools,
#   atari800 + Xvfb + xdotool + ImageMagick for scripted emulator tests.
# Mirrors tools/docker/Dockerfile in github.com/kimslawson/sizecoding.
#
#   sh setup.sh [PREFIX]          # default PREFIX: /opt
#
# Afterwards:  export FASTBASIC=fastbasic FBP=fbp FB_TARGET=atari-int EMU_DISPLAY=:99
#              Xvfb :99 -screen 0 1024x768x24 &   (the emulator tools start it if needed)
set -eu
PREFIX=${1:-/opt}
SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO=sudo

# The commit every number in the sizecoding guide was measured with ("Update to version 4.7 final").
FB_REPO=https://github.com/kimslawson/fastbasic
FB_COMMIT=55dc52f

$SUDO apt-get update -qq
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
  atari800 xvfb xdotool imagemagick python3 python3-pil python3-numpy \
  git make g++ ca-certificates

if [ ! -x "$PREFIX/fb47src/build/compiler/fastbasic" ]; then
  $SUDO git clone -q "$FB_REPO" "$PREFIX/fb47src"
  (cd "$PREFIX/fb47src" && $SUDO git checkout -q "$FB_COMMIT" && $SUDO make -j"$(nproc)" >/dev/null)
fi
printf '#!/bin/sh\nexec %s/fb47src/build/compiler/fastbasic "$@"\n' "$PREFIX" | $SUDO tee /usr/local/bin/fastbasic >/dev/null
$SUDO chmod +x /usr/local/bin/fastbasic
$SUDO ln -sf "$PREFIX/fb47src/build/bin/mkatr" /usr/local/bin/mkatr

if [ ! -x "$PREFIX/fbp/build/fbp" ]; then
  $SUDO git clone -q --depth 1 https://github.com/kimslawson/fastbasic-parser "$PREFIX/fbp"
  (cd "$PREFIX/fbp" && $SUDO make -j"$(nproc)" >/dev/null)
fi
$SUDO ln -sf "$PREFIX/fbp/build/fbp" /usr/local/bin/fbp

if [ ! -d "$PREFIX/sizecoding" ]; then
  $SUDO git clone -q --depth 1 https://github.com/kimslawson/sizecoding "$PREFIX/sizecoding"
fi

echo "FastBasic: $(fastbasic -v 2>&1 | head -1)"
echo "fbp:       $(command -v fbp)"
echo "tools:     $PREFIX/sizecoding/tools  (fbsize.py, fbframes.py, fbbench.py, proof.py, emu.py)"
echo "atari800:  $(atari800 -v 2>&1 | head -1)"
