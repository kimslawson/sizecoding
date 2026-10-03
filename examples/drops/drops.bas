' DROPS: catch the falling stars. A small example for the sizecoding toolchain.
' Joystick left/right moves the paddle. Each star you catch adds one to the row
' at the top; miss one and the row is cleared.
'
'   S  screen memory          P  player 0 memory      X  paddle position
'   C  star column (0-39)     R  star row (0-21)      K  stars caught in a row
'   J  joystick
GRAPHICS 0
POKE 752, 1                           ' hide the cursor
S = DPEEK(88)                         ' screen memory
PMGRAPHICS 2                          ' players on, double-line resolution
P = PMADR(0)
MOVE & "<~~<" + 1, P + 100, 4         ' paddle: 4 bytes from a string literal, text row 22
POKE 704, 26                          ' gold
X = 120
R = 1
C = RAND(40)
DO
  J = STICK(0)
  IF J & 4 = 0 THEN X = X - 2         ' left
  IF J & 8 = 0 THEN X = X + 2         ' right
  IF X < 48 THEN X = 48
  IF X > 200 THEN X = 200
  IF TIME & 3 = 0                     ' the star falls one row every 4th frame
    POKE S + R * 40 + C, 0            ' erase it
    R = R + 1
    IF R = 22                         ' it reached the paddle's row
      IF ABS(X - C * 4 - 46) < 6      ' paddle centre within 6 color clocks of the star
        K = K + 1
        POKE S + K, 10                ' one more star in the top row
      ELSE
        K = 0
        MSET S, 40, 0                 ' missed: clear the row
      ENDIF
      R = 1
      C = RAND(40)
    ENDIF
    POKE S + R * 40 + C, 10           ' draw it (screen code 10 = '*')
  ENDIF
  PAUSE
  PMHPOS 0, X                         ' move the paddle right after the vertical blank
LOOP
