# Size ideas for drops.bas, as variants (see tools/variants.py)
BASE = 'drops.bas'
VARIANTS = {
    'inc':   [('R = R + 1', 'INC R'), ('K = K + 1', 'INC K')],
    'stick': [("  IF J & 4 = 0 THEN X = X - 2         ' left\n"
               "  IF J & 8 = 0 THEN X = X + 2         ' right\n",
               "  X = X + J & 4 / 2 - J & 8 / 4       ' left -2, right +2\n")],
    # not an exact clamp: past an edge the paddle is pushed back 2 per frame
    'clamp': [("  IF X < 48 THEN X = 48\n  IF X > 200 THEN X = 200\n",
               "  X = X + (X < 48) * 2 - (X > 200) * 2\n")],
    # costs a visible feature: the cursor shows in the top left corner
    'cursor': [('POKE 752, 1                           \' hide the cursor\n', '')],
}
