# DROPS: the toolchain on a small game

`drops.bas` is a deliberately unoptimized little game (catch the falling stars with a paddle),
written readably, to walk through the tools; `DROPS10.BAS` is its packed listing (a different
name, not just different case: on macOS and Windows those would be one file). From the repo
root:

```sh
T=tools; D=examples/drops
python3 $T/fbsize.py min $D/drops.bas -o $D/DROPS.min      # fbp -O: measure 277, -ls: 287
python3 $T/variants.py $D/ideas.py                          # what each idea in ideas.py saves
python3 $T/variants.py $D/ideas.py inc stick clamp          # all three together: 256
python3 $T/fbsize.py pack $D/DROPS.min -o $D/DROPS10.BAS    # 3 lines of 120
python3 $T/fbsize.py verify $D/DROPS.min $D/DROPS10.BAS --xex
python3 $T/proof.py $D/DROPS10.BAS -o $D/proof.png
python3 $T/fbframes.py $D/DROPS10.BAS --seconds 5 \
  --keys "xdotool keydown KP_Left; sleep 2; xdotool keyup KP_Left; xdotool keydown KP_Right; sleep 3; xdotool keyup KP_Right"
fastbasic -t:atari-int $D/DROPS10.BAS && mkatr drops.atr -b $D/DROPS10.xex
```

`ideas.py` holds four size ideas as variants. Two of them change behavior on purpose, which is
the point of trying them as variants: `clamp` makes the screen edges push back instead of
stopping the paddle dead, and `cursor` saves 8 characters by leaving the cursor visible. The
other two (`inc`, `stick`) are free.
