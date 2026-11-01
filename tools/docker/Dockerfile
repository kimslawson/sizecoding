# The emulator half of the toolchain in a container, for a Mac or anywhere without
# atari800 5.0 + Xvfb + xdotool: FastBasic 4.7, fbp, atari800, ImageMagick, Pillow, numpy.
#   docker build -t fb-sizecoding tools/docker
#   tools/docker/run.sh python3 tools/fbbench.py bench/arith.bench
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
      atari800 xvfb xdotool imagemagick python3 python3-pil python3-numpy \
      git make g++ ca-certificates >/dev/null && rm -rf /var/lib/apt/lists/*
# FastBasic 4.7 (tag commit 55dc52f), the version every number in this repo was measured with
RUN git clone -q https://github.com/kimslawson/fastbasic /opt/fb47src \
 && cd /opt/fb47src && git checkout -q 55dc52f && make -j8 >/dev/null 2>&1 \
 && printf '#!/bin/sh\nexec /opt/fb47src/build/compiler/fastbasic "$@"\n' > /usr/local/bin/fastbasic \
 && chmod +x /usr/local/bin/fastbasic && fastbasic -v
RUN git clone -q --depth 1 https://github.com/kimslawson/fastbasic-parser /opt/fbp \
 && cd /opt/fbp && make -j8 >/dev/null 2>&1 && ln -s /opt/fbp/build/fbp /usr/local/bin/fbp
ENV FASTBASIC=/usr/local/bin/fastbasic FBP=/usr/local/bin/fbp FB_TARGET=atari-int EMU_DISPLAY=:99
WORKDIR /work
