"""Emulator harness: run an XEX in atari800 under a virtual X display, press keys, read the screen.

Linux only. Needs: atari800 (5.x), Xvfb, xdotool, ImageMagick (`import`), Python Pillow + numpy.
The emulator always runs as an 800XL with the built-in AltirraOS, BASIC off, artifacting off and
its own config file (tools/.cache/atari800.cfg), so your personal atari800 setup can't change the
results.

Keys, as atari800's defaults map them (use these names in xdotool key scripts):
  joystick  KP_Up KP_Down KP_Left KP_Right (numeric keypad 8 2 4 6)   fire  Control_R
  START F4   SELECT F3   OPTION F2   (F1 opens atari800's menu: avoid)

Screen reading assumes the standard GRAPHICS 0 screen at atari800's default 336x224 window:
40 x 24 cells of 8x8 pixels starting at (8, 16). The tools that read results (fbbench, fbframes)
switch back to GRAPHICS 0 before printing, so that holds whatever your program did.
"""
import os, subprocess, time, tempfile, shutil
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, '.cache')
DISPLAY = os.environ.get('EMU_DISPLAY', ':99')
X0, Y0, W, H = 8, 16, 336, 224


def _env():
    e = dict(os.environ); e['DISPLAY'] = DISPLAY; e['SDL_AUDIODRIVER'] = 'dummy'
    return e


def launch(args, stdin=None, stdout=subprocess.DEVNULL):
    """Start atari800 and wait for its window. Returns (process, window id).

    Under a virtual X server SDL sometimes fails to start ("no display resolutions
    available") when emulators are started back to back; that start is simply retried.
    """
    for attempt in range(5):
        p = subprocess.Popen(args, env=_env(), stdin=stdin, stdout=stdout,
                             stderr=subprocess.STDOUT)
        for _ in range(100):
            r = subprocess.run(['xdotool', 'search', '--pid', str(p.pid)], env=_env(),
                               capture_output=True, text=True)
            if r.stdout.split():
                return p, r.stdout.split()[0]
            if p.poll() is not None:
                break
            time.sleep(0.1)
        p.kill(); p.wait()
        time.sleep(0.5 + attempt)
    raise SystemExit('atari800 did not start (5 attempts): ' + ' '.join(args))


# a killed tool (Ctrl-C, timeout) must not leave an emulator running
import signal as _signal
_signal.signal(_signal.SIGTERM, lambda *a: (_ for _ in ()).throw(SystemExit(143)))


def ensure_display():
    r = subprocess.run(['xdotool', 'getdisplaygeometry'], env=_env(), capture_output=True)
    if r.returncode == 0:
        return
    subprocess.Popen(['Xvfb', DISPLAY, '-screen', '0', '800x600x24'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        time.sleep(0.1)
        if subprocess.run(['xdotool', 'getdisplaygeometry'], env=_env(),
                          capture_output=True).returncode == 0:
            return
    raise SystemExit(f'could not start Xvfb on {DISPLAY}')


def run(xex, keys='', wait=2.5, pal=False, turbo=False, until=None, timeout=60, shot=None):
    """Run xex; after `wait` seconds send the bash/xdotool `keys` script; then screenshot.

    With `until` (a function taking a PNG path and returning a result or None), keep taking
    screenshots every half second until it returns something, or `timeout` seconds pass.
    Returns (png path, until's result).
    """
    ensure_display()
    os.makedirs(CACHE, exist_ok=True)
    cfg = os.path.join(CACHE, 'atari800.cfg')
    shot = shot or tempfile.mktemp(suffix='.png')
    args = ['atari800', '-config', cfg, '-xl', '-xl-rev', 'altirra', '-nobasic',
            '-pal' if pal else '-ntsc', '-ntsc-artif', 'none']
    if turbo:
        args.append('-turbo')
    proc, win = launch(args + ['-run', os.path.abspath(xex)])
    try:
        time.sleep(wait)
        subprocess.run(['xdotool', 'windowactivate', win], env=_env(), capture_output=True)
        subprocess.run(['xdotool', 'windowfocus', win], env=_env(), capture_output=True)
        if keys:
            subprocess.run(['bash', '-c', keys], env=_env())
        t0, res = time.time(), None
        while True:
            subprocess.run(['import', '-window', win, shot], env=_env(), check=True)
            if until is None:
                break
            res = until(shot)
            if res is not None or time.time() - t0 > timeout:
                break
            time.sleep(0.5)
        return shot, res
    finally:
        proc.kill(); proc.wait()


class Session:
    """A running atari800 whose built-in monitor we can drive, to read memory exactly.

    atari800's monitor (F8) reads commands from the emulator's standard input and prints to
    its standard output; we own both. `labels` comes from `fastbasic -g` (the .lbl file), so
    variables can be read by name: `fb_var_X` is variable X's address.

        with Session(xex, labels) as s:
            s.sync('EXE_PAUSE')            # stop exactly when the program reaches PAUSE
            n = s.var('Z9_N'); t = s.time()
            s.resume()
    """

    def __init__(self, xex, labels=None, pal=False, wait=2.5):
        import threading
        ensure_display()
        os.makedirs(CACHE, exist_ok=True)
        self.labels = labels or {}
        args = ['atari800', '-config', os.path.join(CACHE, 'atari800.cfg'), '-xl', '-xl-rev',
                'altirra', '-nobasic', '-pal' if pal else '-ntsc', '-ntsc-artif', 'none',
                '-run', os.path.abspath(xex)]
        self.p, self.win = launch(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.out = []
        self._lock = threading.Lock()

        def reader():
            for line in iter(self.p.stdout.readline, b''):
                with self._lock:
                    self.out.append(line.decode('latin1'))
        threading.Thread(target=reader, daemon=True).start()
        time.sleep(wait)
        self.focus()
        self._n = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def focus(self):
        subprocess.run(['xdotool', 'windowfocus', self.win], env=_env(), capture_output=True)

    def keys(self, script, background=True):
        """Run a bash/xdotool key script (in the background by default)."""
        self.focus()
        if background:
            return subprocess.Popen(['bash', '-c', script], env=_env())
        subprocess.run(['bash', '-c', script], env=_env())

    def _send(self, cmds):
        """Send monitor commands; return their output (waits for a sentinel)."""
        self._n += 1
        tag = 0x7A00 + self._n % 256
        with self._lock:
            start = len(self.out)
        self.p.stdin.write(('\n'.join(cmds) + f'\nHEX {tag}\n').encode()); self.p.stdin.flush()
        want = f'{tag} = $'          # the monitor answers "HEX 31233" with "31233 = $7a01"
        text = ''
        for _ in range(600):
            time.sleep(0.05)
            with self._lock:
                text = ''.join(self.out[start:])
            if want in text:
                return text
            if self.p.poll() is not None:
                break
        raise SystemExit('the atari800 monitor did not answer:\n' + text[-2000:])

    def stop(self):
        """Break into the monitor now (F8)."""
        self.focus(); time.sleep(0.05)
        subprocess.run(['xdotool', 'keydown', 'F8'], env=_env()); time.sleep(0.05)
        subprocess.run(['xdotool', 'keyup', 'F8'], env=_env())
        time.sleep(0.3)

    def sync(self, label='EXE_PAUSE'):
        """Stop in the monitor the next time the 6502 reaches a label (default: PAUSE)."""
        self.stop()
        addr = self.labels[label] if isinstance(label, str) else label
        self._send([f'BPC {addr:04X}', 'CONT'])

    def mem(self, addr, n=2):
        text = self._send([f'M {addr:04X}'])
        data = []
        for line in text.splitlines():
            parts = line.split()
            if parts and parts[0].rstrip(':').upper() == '%04X' % (addr + len(data)):
                data += [int(x, 16) for x in parts[1:17] if len(x) == 2]
            if len(data) >= n:
                break
        return data[:n]

    def word(self, addr):
        lo, hi = self.mem(addr, 2)
        v = lo + 256 * hi
        return v - 65536 if v >= 32768 else v

    def var(self, name):
        return self.word(self.labels['fb_var_' + name.upper()])

    def time(self):
        """FastBasic's TIME: RTCLOK bytes $13 (high) and $14 (low)."""
        hi, lo = self.mem(0x13, 2)
        return hi * 256 + lo

    def resume(self):
        self._send(['BPC 0'])                     # a breakpoint at $0000 never fires
        self.p.stdin.write(b'CONT\n'); self.p.stdin.flush()

    def screenshot(self, path=None):
        path = path or tempfile.mktemp(suffix='.png')
        subprocess.run(['import', '-window', self.win, path], env=_env(), check=True)
        return path

    def close(self):
        try:
            self.p.kill(); self.p.wait(timeout=5)
        except Exception:
            pass


def compile_with_labels(src_text, name='p'):
    """Compile with `fastbasic -g`; returns (xex path, {label: address})."""
    import fblib
    d = tempfile.mkdtemp(prefix='fbemu_')
    open(os.path.join(d, name + '.bas'), 'wb').write(src_text.encode('latin1'))
    r = subprocess.run([fblib.FASTBASIC, '-t:' + fblib.TARGET, '-g', name + '.bas'], cwd=d,
                       capture_output=True, text=True)
    x, l = os.path.join(d, name + '.xex'), os.path.join(d, name + '.lbl')
    if r.returncode or not os.path.exists(x):
        raise SystemExit('compile failed:\n' + r.stdout + r.stderr)
    labels = {}
    for line in open(l):
        p = line.split()
        if len(p) == 3 and p[0] == 'al':
            labels[p[2].lstrip('.')] = int(p[1], 16)
    return x, labels


def cells(png):
    """The 24 x 40 character cells of a GRAPHICS 0 screen, as 8x8 boolean arrays."""
    im = Image.open(png).convert('L')
    if im.size != (W, H):
        raise SystemExit(f'{png}: expected a {W}x{H} atari800 window, got {im.size[0]}x{im.size[1]}')
    a = np.asarray(im) > 100
    return a[Y0:Y0 + 192, X0:X0 + 320].reshape(24, 8, 40, 8).transpose(0, 2, 1, 3)


_FONT = None


def font():
    """128 glyphs (internal code order) as 8x8 boolean arrays, grabbed from the emulator once."""
    global _FONT
    if _FONT is None:
        path = os.path.join(CACHE, 'altirraos.fnt')
        if not os.path.exists(path):
            import fontgrab
            fontgrab.grab(path)
        data = open(path, 'rb').read()
        _FONT = np.unpackbits(np.frombuffer(data, np.uint8)).reshape(128, 8, 8).astype(bool)
    return _FONT


# internal code -> ATASCII, for showing what's on screen as text
def internal_to_atascii(c):
    return c + 32 if c < 64 else (c - 64 if c < 96 else c)


def read_screen(png):
    """The screen as 24 strings. Printable ATASCII shows as itself, anything else as '?'."""
    f = font()
    flat = f.reshape(128, 64)
    rows = []
    for row in cells(png):
        s = ''
        for cell in row:
            v = cell.reshape(64)
            hit = np.nonzero((flat == v).all(axis=1))[0]
            if len(hit) == 0:
                hit = np.nonzero((flat == ~v).all(axis=1))[0]   # inverse video
            a = internal_to_atascii(int(hit[0])) if len(hit) else None
            s += chr(a) if a is not None and 32 <= a < 123 else '?'
        rows.append(s)
    return rows


def read_numbers(png, rows=None):
    """Integers printed one per row (PRINT n), from the top of a GRAPHICS 0 screen."""
    out = []
    for line in read_screen(png)[:rows]:
        t = line.strip()
        if not t:
            break
        try:
            out.append(int(t))
        except ValueError:
            return None
    return out


def readout_code(prefix='Z9_'):
    """FastBasic statements that put the screen back to a plain GRAPHICS 0, for printing results.

    Undoes what games usually change: players/missiles, colors, the font, GTIA modes, sound.
    """
    return [
        'SOUND',
        'GRAPHICS 0',
        'POKE 53277,0 : MSET 53248,8,0 : POKE 623,0',   # GRACTL off, P/M off screen, GPRIOR
        'POKE 756,224 : POKE 709,15 : POKE 710,0 : POKE 712,0 : POKE 752,1 : POKE 559,34',
    ]


def compile_bas(src_text, name='p'):
    """Compile FastBasic source text; returns the XEX path (in a temp dir) or raises."""
    import fblib
    d = tempfile.mkdtemp(prefix='fbemu_')
    open(os.path.join(d, name + '.bas'), 'wb').write(src_text.encode('latin1'))
    r = subprocess.run([fblib.FASTBASIC, '-t:' + fblib.TARGET, name + '.bas'], cwd=d,
                       capture_output=True, text=True)
    x = os.path.join(d, name + '.xex')
    if r.returncode or not os.path.exists(x):
        raise SystemExit('compile failed:\n' + r.stdout + r.stderr + '\n--- source ---\n' + src_text)
    return x
