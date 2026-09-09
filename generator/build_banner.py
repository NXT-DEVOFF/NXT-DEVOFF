"""Etape 3 : assemble assets/banner-dark.svg et assets/banner-light.svg.

Fenetre terminal 1180x610 intitulee profile.sh --live.
  - gauche  : cadre VISUAL.MAP, logo NXT DEV trame
  - droite  : releve SYSTEM.INFO, points de conduite calcules, pastille LIVE

Deux couches superposees, comme l'exige le prompt source :
  intro    60 groupes disperses qui apparaissent en fondu (joue une fois)
  loop     95 bandes de derive + 900 travellers (boucle 14,2 s)

La couche identite est dupliquee entre intro et loop : un point appartient a un
groupe d'apparition ET a une bande de derive, deux partitions differentes du
meme ensemble. Les fusionner casserait l'une des deux animations.

Les points sont ecrits en unites entieres (UNIT = 4 par cellule) puis remis a
l'echelle par le groupe parent : cela evite les decimales et allege nettement
le fichier.
"""
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
ASSETS = os.path.join(HERE, os.pardir, 'assets')

W, H = 1180, 610
UNIT = 4                # sous-unites par cellule de grille
DOT = 3                 # cote d'un point d'identite, en sous-unites
TDOT = 5                # cote d'un traveller : plus epais, comme prescrit

INTRO_DUR = 3.2
LOOP_DUR = 14.2
# portrait 3,0 + 3 x (transition 1,3 + palier 2,0) + retour 1,3 = 14,2 s
STOPS = [0.0, 3.0, 4.3, 6.3, 7.6, 9.6, 10.9, 12.9, 14.2]
KEYTIMES = ';'.join('%.4f' % (t / LOOP_DUR) for t in STOPS)

PALETTES = {
    'dark': dict(bg='#0A0F1E', win='#0E1424', panel='#0B1120', bar='#121A2E',
                 chrome='#1E6FF0', ink='#F59E0B', text='#E6EDF7',
                 muted='#7C8BA8', leader='#22304C', accent='#EC4899',
                 live='#FF4D4D'),
    'light': dict(bg='#EEF2F8', win='#FFFFFF', panel='#F7F9FC', bar='#E7ECF5',
                  chrome='#0B4FD0', ink='#B45309', text='#0B1220',
                  muted='#55637A', leader='#C7D2E4', accent='#BE185D',
                  live='#D32020'),
}

ROWS = [
    ('Subject',       'NXT'),
    ('Role',          'Dev Lua / GLua · Web full-stack'),
    ('Origin',        'France'),
    ('Education',     'Pix · Développement, écosystème Discord'),
    ('Status',        'Build · Opti · Toujours en apprentissage'),
    ('ToolChain',     'AntiGravity, VS Code, Orca, outils IA'),
    None,
    ('Core.Lang',     'Lua, GLua, JavaScript, TypeScript, Python'),
    ('Core.Platform', 'FiveM, Garry’s Mod'),
    ('Core.Frontend', 'HTML, CSS, JS'),
    ('Core.Backend',  'Node.js, Shell'),
    ('Core.Focus',    'Performance & systèmes propres'),
    None,
    ('Grid.Mail',     'kikilebg51@gmail.com'),
    ('Grid.Discord',  'NXT'),
    ('Grid.GitHub',   'NXT-DEVOFF'),
]

HANDLE = '@NXT-DEVOFF'
TAGLINE = '10+ ans'

FS_ROW, FS_HEAD, FS_LIVE, FS_PILL = 14, 13, 12, 14
ROW_STEP = 23
CW = 0.6                # avance d'un caractere en fraction de la taille de police


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def encode_dots(cells, size=DOT):
    """Cellules (x, y) -> chemin compact de petits carres, en coordonnees relatives."""
    out = []
    px = py = 0
    for i, (x, y) in enumerate(cells):
        X, Y = int(x) * UNIT, int(y) * UNIT
        out.append(('M%d,%d' % (X, Y)) if i == 0 else ('m%d,%d' % (X - px, Y - py)))
        out.append('h%dv%dh-%dz' % (size, size, size))
        px, py = X, Y
    return ''.join(out)


def row_svg(label, value, y, p, x_left, x_right):
    """Une ligne : libelle, points de conduite calcules, valeur alignee a droite."""
    lw = len(label) * FS_ROW * CW
    vw = len(value) * FS_ROW * CW
    vx = x_right - vw
    parts = [
        '<text x="%.1f" y="%.1f" class="row" textLength="%.1f" '
        'lengthAdjust="spacingAndGlyphs" fill="%s">%s</text>'
        % (x_left, y, lw, p['muted'], esc(label)),
        '<text x="%.1f" y="%.1f" class="row" textLength="%.1f" '
        'lengthAdjust="spacingAndGlyphs" fill="%s">%s</text>'
        % (vx, y, vw, p['text'], esc(value)),
    ]
    a, b = x_left + lw + 9, vx - 9
    if b > a + 6:
        parts.insert(1, '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                        'stroke-width="1" stroke-dasharray="1 5" '
                        'stroke-linecap="round"/>' % (a, y - 4.5, b, y - 4.5, p['leader']))
    return ''.join(parts)


def build(theme):
    p = PALETTES[theme]
    ident = np.load(os.path.join(DATA, 'identity.npy'))
    bands = np.load(os.path.join(DATA, 'bands.npy'))
    drift = np.load(os.path.join(DATA, 'band_drift.npy'))
    intro = np.load(os.path.join(DATA, 'intro_groups.npy'))
    trav = np.load(os.path.join(DATA, 'travellers.npy'))

    ys, xs = np.where(ident)
    order = np.argsort(ys * ident.shape[1] + xs)
    xs, ys = xs[order], ys[order]
    bands, intro = bands[order], intro[order]

    gh, gw = ident.shape
    # zone de dessin du portrait
    px0, py0, pw, ph = 48.0, 112.0, 364.0, 396.0
    k = pw / gw                       # pixels par cellule
    draw_h = gh * k
    oy = py0 + (ph - draw_h) / 2.0
    scale = k / UNIT
    tf = 'translate(%.2f,%.2f) scale(%.5f)' % (px0, oy, scale)

    s = []
    s.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
             'width="%d" height="%d" role="img" '
             'aria-label="NXT DEV — profile.sh --live">' % (W, H, W, H))
    s.append('<title>NXT DEV · profile.sh --live</title>')
    s.append('<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'
             '"DejaVu Sans Mono",monospace}'
             '.row{font-size:%dpx}.head{font-size:%dpx;letter-spacing:1.4px}'
             '.live{font-size:%dpx;letter-spacing:1.2px}'
             '.pill{font-size:%dpx}</style>' % (FS_ROW, FS_HEAD, FS_LIVE, FS_PILL))

    s.append('<rect width="%d" height="%d" fill="%s"/>' % (W, H, p['bg']))
    s.append('<rect x="16" y="16" width="1148" height="578" rx="11" fill="%s" '
             'stroke="%s" stroke-opacity=".38"/>' % (p['win'], p['chrome']))
    s.append('<path d="M16 27a11 11 0 0 1 11-11h1126a11 11 0 0 1 11 11v33H16z" '
             'fill="%s"/>' % (p['bar']))
    s.append('<line x1="16" y1="60" x2="1164" y2="60" stroke="%s" '
             'stroke-opacity=".38"/>' % p['chrome'])
    for i, c in enumerate(('#FF5F57', '#FEBC2E', '#28C840')):
        s.append('<circle cx="%d" cy="38" r="5.5" fill="%s"/>' % (44 + i * 21, c))
    s.append('<text x="112" y="43" class="row" fill="%s">profile.sh --live</text>'
             % p['muted'])

    # ---- cadre du portrait
    s.append('<rect x="40" y="80" width="380" height="440" rx="7" fill="%s" '
             'stroke="%s" stroke-opacity=".28"/>' % (p['panel'], p['chrome']))
    s.append('<text x="52" y="99" class="head" fill="%s">VISUAL.MAP</text>' % p['chrome'])
    s.append('<clipPath id="pc"><rect x="42" y="104" width="376" height="412" rx="5"/>'
             '</clipPath>')
    s.append('<g clip-path="url(#pc)" fill="%s" shape-rendering="crispEdges">' % p['ink'])

    # couche intro : 60 groupes disperses, apparition echelonnee sur ~2 s
    s.append('<g transform="%s">' % tf)
    for g in range(int(intro.max()) + 1):
        m = intro == g
        if not m.any():
            continue
        d = encode_dots(list(zip(xs[m], ys[m])))
        begin = 2.0 * g / (intro.max() + 1)
        s.append('<g opacity="0"><path d="%s"/>'
                 '<animate attributeName="opacity" values="0;1" dur="0.55s" '
                 'begin="%.2fs" fill="freeze"/></g>' % (d, begin))
    s.append('<set attributeName="opacity" to="0" begin="%.2fs"/>' % INTRO_DUR)
    s.append('</g>')

    # couche boucle : bandes de derive
    s.append('<g transform="%s" opacity="0">' % tf)
    s.append('<animate attributeName="opacity" values="1;1;0;0;0;0;0;0;1" '
             'keyTimes="%s" dur="%.1fs" begin="%.2fs" repeatCount="indefinite"/>'
             % (KEYTIMES, LOOP_DUR, INTRO_DUR))
    for b in range(len(drift)):
        m = bands == b
        if not m.any():
            continue
        d = encode_dots(list(zip(xs[m], ys[m])))
        dx, dy = drift[b] * UNIT
        v = '0 0;0 0;' + ';'.join(['%.0f %.0f' % (dx, dy)] * 6) + ';0 0'
        s.append('<g><path d="%s"/><animateTransform attributeName="transform" '
                 'type="translate" values="%s" keyTimes="%s" dur="%.1fs" '
                 'begin="%.2fs" repeatCount="indefinite"/></g>'
                 % (d, v, KEYTIMES, LOOP_DUR, INTRO_DUR))
    s.append('</g>')

    # couche travellers : morph entre les trois logos
    s.append('<g transform="%s" opacity="0">' % tf)
    s.append('<animate attributeName="opacity" values="0;0;1;1;1;1;1;1;0" '
             'keyTimes="%s" dur="%.1fs" begin="%.2fs" repeatCount="indefinite"/>'
             % (KEYTIMES, LOOP_DUR, INTRO_DUR))
    base = trav[0]
    for i in range(trav.shape[1]):
        x0, y0 = base[i]
        offs = []
        for j in (0, 0, 1, 1, 2, 2, 3, 3):
            offs.append((trav[j][i] - base[i]) * UNIT)
        v = ';'.join('%.0f %.0f' % (o[0], o[1]) for o in offs) + ';0 0'
        s.append('<path d="M%d,%dh%dv%dh-%dz">'
                 '<animateTransform attributeName="transform" type="translate" '
                 'values="%s" keyTimes="%s" dur="%.1fs" begin="%.2fs" '
                 'repeatCount="indefinite"/></path>'
                 % (int(x0) * UNIT, int(y0) * UNIT, TDOT, TDOT, TDOT,
                    v, KEYTIMES, LOOP_DUR, INTRO_DUR))
    s.append('</g>')
    s.append('</g>')

    # ---- pastille du handle
    s.append('<rect x="40" y="534" width="380" height="36" rx="18" fill="%s" '
             'fill-opacity=".14" stroke="%s" stroke-opacity=".55"/>'
             % (p['chrome'], p['chrome']))
    s.append('<circle cx="64" cy="552" r="4" fill="%s"/>' % p['accent'])
    s.append('<text x="78" y="557" class="pill" fill="%s">%s</text>'
             % (p['text'], HANDLE))
    s.append('<text x="404" y="557" class="pill" text-anchor="end" fill="%s">%s</text>'
             % (p['chrome'], TAGLINE))

    # ---- panneau d'information
    ix0, ix1 = 452.0, 1144.0
    s.append('<text x="%.0f" y="99" class="head" fill="%s">SYSTEM.INFO</text>'
             % (ix0, p['text']))
    s.append('<rect x="1078" y="85" width="66" height="20" rx="10" fill="%s" '
             'fill-opacity=".16" stroke="%s" stroke-opacity=".6"/>'
             % (p['live'], p['live']))
    s.append('<circle cx="1093" cy="95" r="3.4" fill="%s">'
             '<animate attributeName="opacity" values="1;.2;1" dur="1.6s" '
             'repeatCount="indefinite"/></circle>' % p['live'])
    s.append('<text x="1103" y="99.5" class="live" fill="%s">LIVE</text>' % p['live'])
    s.append('<line x1="%.0f" y1="112" x2="%.0f" y2="112" stroke="%s" '
             'stroke-opacity=".5"/>' % (ix0, ix1, p['leader']))

    y = 136.0
    for r in ROWS:
        if r is None:
            s.append('<line x1="%.0f" y1="%.1f" x2="%.0f" y2="%.1f" stroke="%s" '
                     'stroke-opacity=".55"/>' % (ix0, y - 12, ix1, y - 12, p['leader']))
            y += 12
            continue
        s.append(row_svg(r[0], r[1], y, p, ix0, ix1))
        y += ROW_STEP

    s.append('</svg>')
    out = ''.join(s)
    path = os.path.join(ASSETS, 'banner-%s.svg' % theme)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(out)
    return path, len(out.encode('utf-8'))


def main():
    for theme in ('dark', 'light'):
        path, size = build(theme)
        print('%-28s %7.1f Ko' % (os.path.basename(path), size / 1024))


if __name__ == '__main__':
    main()
