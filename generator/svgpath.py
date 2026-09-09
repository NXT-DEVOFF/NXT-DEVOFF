"""Rasteriseur de chemins SVG, sans dependance native.

Parse l'attribut `d` d'un <path> et le remplit par balayage de lignes avec la
regle non-zero, en surechantillonnant pour l'antialiasing.

Ecrit parce que cairosvg exige une DLL cairo absente sous Windows. Parser le
tracé officiel plutot que redessiner la forme respecte la consigne du prompt
source : tracer les logos, ne pas les dessiner de memoire.
"""
import re
import math
import numpy as np

class _Scanner:
    """Lecteur sensible au contexte pour l'attribut `d`.

    Un tokeniseur global ne suffit pas : dans un arc, les drapeaux `large` et
    `sweep` sont des caracteres uniques qui peuvent etre colles a leurs voisins
    ("0 00-4.88-1.51"). Les lire comme des nombres decale tous les arguments.
    Ils exigent donc `flag()`, qui consomme exactement un caractere.
    """

    NUM = re.compile(r'[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?')
    SEP = ' \t\r\n,'

    def __init__(self, s):
        self.s = s
        self.i = 0

    def _skip(self):
        while self.i < len(self.s) and self.s[self.i] in self.SEP:
            self.i += 1

    def eof(self):
        self._skip()
        return self.i >= len(self.s)

    def peek_cmd(self):
        self._skip()
        if self.i < len(self.s) and self.s[self.i].isalpha():
            return self.s[self.i]
        return None

    def cmd(self):
        c = self.peek_cmd()
        if c is not None:
            self.i += 1
        return c

    def num(self):
        self._skip()
        m = self.NUM.match(self.s, self.i)
        if not m:
            raise ValueError('nombre attendu en position %d : %r'
                             % (self.i, self.s[self.i:self.i + 12]))
        self.i = m.end()
        return float(m.group())

    def flag(self):
        self._skip()
        if self.i >= len(self.s):
            raise ValueError('drapeau attendu en fin de chaine')
        c = self.s[self.i]
        self.i += 1
        return 1 if c == '1' else 0


def _arc(x0, y0, rx, ry, phi_deg, large, sweep, x1, y1, out, steps=32):
    """Arc elliptique : conversion endpoint -> centre, puis echantillonnage."""
    if rx == 0 or ry == 0:
        out.append((x1, y1))
        return
    phi = math.radians(phi_deg)
    cp, sp = math.cos(phi), math.sin(phi)
    dx2, dy2 = (x0 - x1) / 2.0, (y0 - y1) / 2.0
    x1p, y1p = cp * dx2 + sp * dy2, -sp * dx2 + cp * dy2
    rx, ry = abs(rx), abs(ry)
    lam = (x1p * x1p) / (rx * rx) + (y1p * y1p) / (ry * ry)
    if lam > 1:
        s = math.sqrt(lam)
        rx, ry = rx * s, ry * s
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1p / ry, -co * ry * x1p / rx
    cx = cp * cxp - sp * cyp + (x0 + x1) / 2.0
    cy = sp * cxp + cp * cyp + (y0 + y1) / 2.0

    def ang(ux, uy, vx, vy):
        d = math.hypot(ux, uy) * math.hypot(vx, vy)
        if d == 0:
            return 0.0
        c = max(-1.0, min(1.0, (ux * vx + uy * vy) / d))
        a = math.acos(c)
        return -a if ux * vy - uy * vx < 0 else a

    ux, uy = (x1p - cxp) / rx, (y1p - cyp) / ry
    vx, vy = (-x1p - cxp) / rx, (-y1p - cyp) / ry
    t1 = ang(1, 0, ux, uy)
    dt = ang(ux, uy, vx, vy)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    for i in range(1, steps + 1):
        t = t1 + dt * i / steps
        ct, st = math.cos(t), math.sin(t)
        out.append((cx + rx * ct * cp - ry * st * sp,
                    cy + rx * ct * sp + ry * st * cp))


def parse_path(d, curve_steps=24):
    """Retourne une liste de sous-chemins, chacun une liste de points (x, y)."""
    sc = _Scanner(d)
    subs, cur = [], []
    x = y = sx = sy = 0.0
    px = py = None          # dernier point de controle, pour le lissage S / T
    cmd = None

    while not sc.eof():
        nxt = sc.peek_cmd()
        if nxt is not None:
            cmd = sc.cmd()
        elif cmd is None:
            break                      # nombres avant toute commande : ignore
        rel = cmd.islower()
        c = cmd.upper()

        if c == 'Z':
            if cur:
                cur.append((sx, sy))
                subs.append(cur)
                cur = []
            x, y = sx, sy
            px = py = None
            continue

        if c == 'M':
            ax, ay = sc.num(), sc.num()
            x, y = (x + ax, y + ay) if rel else (ax, ay)
            if cur:
                subs.append(cur)
            cur = [(x, y)]
            sx, sy = x, y
            cmd = 'l' if rel else 'L'   # les paires suivantes sont des lineto
        elif c == 'L':
            ax, ay = sc.num(), sc.num()
            x, y = (x + ax, y + ay) if rel else (ax, ay)
            cur.append((x, y))
        elif c == 'H':
            ax = sc.num()
            x = x + ax if rel else ax
            cur.append((x, y))
        elif c == 'V':
            ay = sc.num()
            y = y + ay if rel else ay
            cur.append((x, y))
        elif c in 'CS':
            if c == 'C':
                x1, y1 = sc.num(), sc.num()
                x2, y2 = sc.num(), sc.num()
                ax, ay = sc.num(), sc.num()
                if rel:
                    x1, y1 = x + x1, y + y1
                    x2, y2 = x + x2, y + y2
                    ax, ay = x + ax, y + ay
            else:
                x2, y2 = sc.num(), sc.num()
                ax, ay = sc.num(), sc.num()
                if rel:
                    x2, y2 = x + x2, y + y2
                    ax, ay = x + ax, y + ay
                x1, y1 = (2 * x - px, 2 * y - py) if px is not None else (x, y)
            for k in range(1, curve_steps + 1):
                t = k / curve_steps
                u = 1 - t
                cur.append((u**3 * x + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * ax,
                            u**3 * y + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * ay))
            px, py = x2, y2
            x, y = ax, ay
            continue
        elif c in 'QT':
            if c == 'Q':
                x1, y1 = sc.num(), sc.num()
                ax, ay = sc.num(), sc.num()
                if rel:
                    x1, y1 = x + x1, y + y1
                    ax, ay = x + ax, y + ay
            else:
                ax, ay = sc.num(), sc.num()
                if rel:
                    ax, ay = x + ax, y + ay
                x1, y1 = (2 * x - px, 2 * y - py) if px is not None else (x, y)
            for k in range(1, curve_steps + 1):
                t = k / curve_steps
                u = 1 - t
                cur.append((u * u * x + 2 * u * t * x1 + t * t * ax,
                            u * u * y + 2 * u * t * y1 + t * t * ay))
            px, py = x1, y1
            x, y = ax, ay
            continue
        elif c == 'A':
            rx, ry, rot = sc.num(), sc.num(), sc.num()
            la, sw = sc.flag(), sc.flag()      # un caractere chacun, jamais num()
            ax, ay = sc.num(), sc.num()
            if rel:
                ax, ay = x + ax, y + ay
            _arc(x, y, rx, ry, rot, la, sw, ax, ay, cur)
            x, y = ax, ay
        else:
            break
        px = py = None

    if cur:
        subs.append(cur)
    return subs


def rasterize(subpaths, size, ss=4, pad=0.06):
    """Remplit les sous-chemins (regle non-zero) dans une image carree.

    Retourne un tableau float32 [0, 1] antialiase par surechantillonnage `ss`.
    """
    pts = [p for s in subpaths for p in s]
    if not pts:
        return np.zeros((size, size), np.float32)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    w = max(x1 - x0, 1e-9)
    h = max(y1 - y0, 1e-9)
    scale = (1 - 2 * pad) * size / max(w, h)
    ox = (size - w * scale) / 2 - x0 * scale
    oy = (size - h * scale) / 2 - y0 * scale

    S = size * ss
    edges = []                     # (y_haut, y_bas, x_a_y_haut, pente, sens)
    for sub in subpaths:
        p = [((qx * scale + ox) * ss, (qy * scale + oy) * ss) for qx, qy in sub]
        if len(p) < 2:
            continue
        if p[0] != p[-1]:
            p.append(p[0])
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            if ay == by:
                continue
            d = 1 if by > ay else -1
            if d < 0:
                ax, ay, bx, by = bx, by, ax, ay
            edges.append((ay, by, ax, (bx - ax) / (by - ay), d))
    if not edges:
        return np.zeros((size, size), np.float32)

    acc = np.zeros((S, S), np.uint8)
    for yi in range(S):
        yc = yi + 0.5
        hits = [(e[2] + (yc - e[0]) * e[3], e[4]) for e in edges if e[0] <= yc < e[1]]
        if not hits:
            continue
        hits.sort()
        wind = 0
        start = None
        for xv, d in hits:
            prev = wind
            wind += d
            if prev == 0 and wind != 0:
                start = xv
            elif prev != 0 and wind == 0 and start is not None:
                a = max(0, int(math.ceil(start - 0.5)))
                b = min(S, int(math.ceil(xv - 0.5)))
                if b > a:
                    acc[yi, a:b] = 1
                start = None
    return acc.reshape(size, ss, size, ss).mean(axis=(1, 3)).astype(np.float32)


def load_svg_mask(path, size, ss=4, pad=0.06):
    """Charge un SVG a tracé monochrome (style simple-icons) -> masque [0, 1]."""
    svg = open(path, 'r', encoding='utf-8').read()
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    if not ds:
        raise ValueError('aucun <path d="..."> trouve dans ' + path)
    subs = []
    for d in ds:
        subs.extend(parse_path(d))
    return rasterize(subs, size, ss=ss, pad=pad)
