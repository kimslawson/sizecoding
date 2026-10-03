"""Shared helpers for the FastBasic sizecoding tools.

Everything here works on listings as bytes, because a FastBasic listing can hold any byte
inside a string literal. Lines end in ATASCII EOL ($9B) or in LF; both are accepted.

Environment:
  FASTBASIC  path to the FastBasic cross-compiler (default: `fastbasic` on PATH)
  FBP        path to fbp, the FastBasic parser/minimizer (default: `fbp` on PATH, optional)
  FB_TARGET  compiler target (default: atari-int)
"""
import os, shutil, signal, subprocess, tempfile

# piping a tool into `head` should end quietly, not with a traceback
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

EOL = b'\x9b'
FASTBASIC = os.environ.get('FASTBASIC', 'fastbasic')
FBP = os.environ.get('FBP', 'fbp')
TARGET = os.environ.get('FB_TARGET', 'atari-int')


def read_lines(path):
    """Return the lines of a listing as a list of bytes, without line ends."""
    data = open(path, 'rb').read()
    eol = EOL if EOL in data else b'\n'
    data = data.replace(b'\r\n', b'\n') if eol == b'\n' else data
    lines = data.split(eol)
    while lines and lines[-1] == b'':
        lines.pop()
    return lines


def split_statements(line):
    """Split one listing line into statements at ':' outside string literals.

    A string literal runs from '"' to the next '"'; a doubled quote inside it is an escaped
    quote, which the toggle handles for free. Comments are not expected in minimized code;
    a "'" outside a string ends the line's statements and is kept with the last one.
    """
    out, cur, q = [], bytearray(), False
    for i, c in enumerate(line):
        ch = bytes([c])
        if ch == b'"':
            q = not q
        if not q and ch == b"'":
            cur += line[i:]
            break
        if ch == b':' and not q:
            out.append(bytes(cur)); cur = bytearray()
        else:
            cur += ch
    out.append(bytes(cur))
    return [s for s in out if s != b'']


def statements(path):
    """All statements of a listing, in order."""
    return [s for line in read_lines(path) for s in split_statements(line)]


def measure(lines):
    """Size figures for a list of lines (bytes)."""
    lens = [len(l) for l in lines]
    stmts = sum(len(split_statements(l)) for l in lines)
    chars = sum(lens)
    return {
        'lines': len(lines),
        'max': max(lens) if lens else 0,
        'chars': chars,
        # the program as if it were one line: every line break turned back into ':'
        'measure': chars + max(len(lines) - 1, 0),
        'statements': stmts,
        'lens': lens,
    }


def write_listing(path, lines, eol=EOL):
    with open(path, 'wb') as f:
        f.write(eol.join(lines) + eol)


def have(prog):
    return shutil.which(prog) is not None or os.path.isfile(prog)


def compile_xex(src_bytes, target=None, name='p', extra=()):
    """Compile a listing (bytes) and return (xex bytes or None, compiler output)."""
    target = target or TARGET
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, name + '.bas')
        open(p, 'wb').write(src_bytes)
        r = subprocess.run([FASTBASIC, '-t:' + target, *extra, name + '.bas'], cwd=d,
                           capture_output=True, text=True, errors='replace')
        x = os.path.join(d, name + '.xex')
        if r.returncode or not os.path.exists(x):
            return None, r.stdout + r.stderr
        return open(x, 'rb').read(), r.stdout + r.stderr


def fb_minimize(src_path, width=120, target=None):
    """FastBasic's own minimizer (-l:min). Returns the listing bytes."""
    target = target or TARGET
    with tempfile.TemporaryDirectory() as d:
        shutil.copy(src_path, os.path.join(d, 'p.bas'))
        r = subprocess.run([FASTBASIC, '-t:' + target, '-ls:%d' % width, '-l:min', 'p.bas'],
                           cwd=d, capture_output=True, text=True, errors='replace')
        m = os.path.join(d, 'p.min')
        if not os.path.exists(m):
            raise SystemExit('fastbasic -l:min failed:\n' + r.stdout + r.stderr)
        return open(m, 'rb').read()


def fbp_minimize(src_path, width=120, target=None, opts=('-O',), keep_names=False):
    """fbp's minimizer. Returns the listing bytes (Atari EOLs)."""
    target = target or TARGET
    cmd = [FBP, '-q', '-t', target, '-n', str(width), '-c', *opts]
    if keep_names:
        cmd.append('-f')
    r = subprocess.run(cmd + [src_path], capture_output=True)
    if r.returncode:
        raise SystemExit('fbp failed:\n' + r.stderr.decode('latin1'))
    return r.stdout


def minimize(src_path, width=120, target=None, tool='auto', keep_names=False):
    """Minimize with fbp if available (or asked for), else FastBasic's -l:min."""
    if tool == 'fbp' or (tool == 'auto' and have(FBP)):
        return fbp_minimize(src_path, width, target, keep_names=keep_names), 'fbp -O'
    return fb_minimize(src_path, width, target), 'fastbasic -l:min'


def show(b):
    """Printable form of listing bytes: control and high bytes as {XX}."""
    return ''.join(chr(c) if 32 <= c < 127 else '{%02X}' % c for c in b)


# Every word FastBasic 4.7's grammar knows (all targets). Anything else in an expanded
# statement is a variable, array, string, PROC or DLI name.
KEYWORDS = set('''ABS ADR AND ASC ATN BGET BPUT BYTE CHR CLOSE CLR CLS COLOR COS DATA DEC DEG DIM
DLI DO DPEEK DPOKE DRAWTO ELIF ELSE END ENDIF ENDPROC ERR EXEC EXIT EXOR EXP EXP10 FCOLOR FILE
FILLTO FOR FRE GET GRAPHICS IF INC INPUT INT INTO KEY LEN LOCATE LOG LOG10 LOOP MOD MOVE MSET
NCLOSE NEXT NGET NOPEN NOT NPUT NSTATUS OPEN OR PADDLE PAUSE PEEK PLOT PMADR PMGRAPHICS PMHPOS
POKE POSITION PRINT PROC PTRIG PUT RAD RAND REPEAT RND ROM RTAB SERR SET SETCOLOR SGN SIN SIO
SOUND SQR STEP STICK STR STRIG TAB THEN TIME TIMER TO UNTIL USR VAL WEND WHILE WORD WSYNC
XIO'''.split())


def expand(src_bytes, target=None):
    """FastBasic's expanded listing (-l:lst): one statement per line, keywords in full."""
    target = target or TARGET
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, 'p.bas'), 'wb').write(src_bytes)
        subprocess.run([FASTBASIC, '-t:' + target, '-l:lst', 'p.bas'], cwd=d,
                       capture_output=True)
        p = os.path.join(d, 'p.lst')
        if not os.path.exists(p):
            return None
        return [l.strip() for l in open(p, 'rb').read().split(b'\n') if l.strip()]


def names(expanded_stmt):
    """Names (variables, arrays, strings, PROCs, DLIs) mentioned in an expanded statement."""
    import re
    s = re.sub(rb'"(?:[^"]|"")*"', b' ', expanded_stmt)      # string literals
    s = re.sub(rb'\$[0-9A-Fa-f]+', b' ', s)                  # $xx escapes, hex numbers
    out = set()
    for m in re.finditer(rb'(?<![0-9.$A-Za-z_])[A-Za-z_][A-Za-z_0-9]*', s):
        w = m.group(0).decode().upper()
        if w not in KEYWORDS:
            out.add(w)
    return out
