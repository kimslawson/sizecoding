' Where in the frame does TIME tick? Logs 200 (TIME low byte, VCOUNT) pairs as fast as
' it can into $6000, then sets a flag at $6400. bench/vctime.py runs it with a few start
' delays D (so the samples fall at different points) and finds the VCOUNT every tick fits.
D = 0
PAUSE
FOR W = 1 TO D : NEXT
FOR K = 0 TO 199
  POKE $6000 + K * 2, PEEK(20) : POKE $6001 + K * 2, PEEK(54283)
NEXT
POKE $6400, 1
DO : LOOP
