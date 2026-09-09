"""Etape 1 : transforme les sources (PNG du logo, SVG des technos) en grilles de points.

Produit dans data/ :
  identity.npy   grille booleenne du logo NXT DEV, tramee Floyd-Steinberg
  lua.npy        masque booleen du logo Lua
  fivem.npy      masque booleen du logo FiveM

Deux ecarts assumes par rapport au prompt source, tous deux mesures :

1. autocontrast(cutoff=1) est REMPLACE par un etirement borne a la zone opaque.
   Sur ce logo, autocontrast fait passer la couverture d'encre de 95,1 % a
   97,1 % : il pousse des blancs deja satures. L'etirement borne descend a
   93,5 % et double l'ecart-type de densite (0,082 -> 0,149).

2. La grille passe de 300x340 a 250x278. Le logo etant une forme pleine, il
   remplit 24 748 cellules sur 300x340, contre les ~17 000 attendus pour un
   visage. Reduire la grille ramene le compte a ~17 000, allege le fichier, et
   applique gratuitement le seul correctif reconnu contre le moire en 1080p
   (moins de points, plus gros) — correctif juge trop couteux pour une photo,
   sans cout ici puisqu'un logo n'a aucun detail fin a perdre.
"""
import os
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance
from scipy.cluster.vq import kmeans2

from svgpath import load_svg_mask

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
ASSETS = os.path.join(HERE, os.pardir, 'assets')

GRID_W = 250            # largeur de la grille en cellules
N_TRAVELLERS = 900      # points de la couche mobile


def dither_serpentine(arr, mask):
    """Floyd-Steinberg 1 bit en ordre serpentin, restreint au masque."""
    d = arr.astype(np.float32).copy()
    h, w = d.shape
    out = np.zeros((h, w), np.uint8)
    for y in range(h):
        forward = (y % 2 == 0)
        xs = range(w) if forward else range(w - 1, -1, -1)
        for x in xs:
            old = d[y, x]
            new = 255.0 if old >= 128 else 0.0
            out[y, x] = 1 if new > 0 else 0
            err = old - new
            if forward:
                nb = ((1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16))
            else:
                nb = ((-1, 0, 7 / 16), (1, 1, 3 / 16), (0, 1, 5 / 16), (-1, 1, 1 / 16))
            for dx, dy, f in nb:
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h:
                    d[yy, xx] += err * f
    return out * mask


def build_identity():
    """Logo NXT DEV -> grille tramee."""
    im = Image.open(os.path.join(ASSETS, 'logo-nxtdev.png')).convert('RGBA')
    a = np.array(im)[:, :, 3]
    ys, xs = np.where(a > 200)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))

    scale = GRID_W / im.width
    nw, nh = GRID_W, max(1, int(round(im.height * scale)))
    im = im.resize((nw, nh), Image.LANCZOS)

    rgba = np.array(im)
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    mask = (alpha > 0.5).astype(np.uint8)
    gray = np.array(Image.fromarray(rgba[:, :, :3]).convert('L')).astype(np.float32)

    # Etirement tonal borne a la zone opaque : c'est la correction cle.
    vals = gray[mask > 0]
    lo, hi = np.percentile(vals, 2), np.percentile(vals, 98)
    g = np.clip((gray - lo) / max(1e-6, hi - lo) * 255.0, 0, 255).astype(np.uint8)
    g = Image.fromarray(g).filter(ImageFilter.UnsharpMask(radius=3, percent=140))
    g = np.array(ImageEnhance.Contrast(g).enhance(1.3))

    dots = dither_serpentine(g, mask)
    np.save(os.path.join(DATA, 'identity.npy'), dots.astype(bool))

    inside = dots[mask > 0]
    dens = [dots[y:y + 10, x:x + 10].mean()
            for y in range(0, dots.shape[0] - 9, 10)
            for x in range(0, dots.shape[1] - 9, 10)
            if mask[y:y + 10, x:x + 10].mean() > 0.9]
    print('identity : grille %dx%d  %d points  encre %.1f%%  ecart-type densite %.3f'
          % (nw, nh, int(dots.sum()), 100 * inside.mean(), float(np.std(dens))))
    return dots


def build_logo(name, grid_h):
    """SVG monochrome -> masque booleen a la meme echelle que l'identite."""
    m = load_svg_mask(os.path.join(DATA, name + '.svg'), GRID_W, ss=4, pad=0.10)
    if m.shape[0] != grid_h:                       # recadre verticalement
        out = np.zeros((grid_h, GRID_W), np.float32)
        top = max(0, (grid_h - m.shape[0]) // 2)
        src = m[:min(m.shape[0], grid_h - top)]
        out[top:top + src.shape[0]] = src
        m = out
    dots = (m > 0.5).astype(np.uint8)
    np.save(os.path.join(DATA, name + '.npy'), dots.astype(bool))
    print('%-8s : %d cellules pleines (%.1f%% de la grille)'
          % (name, int(dots.sum()), 100 * dots.mean()))
    return dots


def sample_points(grid, n, seed):
    """n points bien repartis sur une grille booleenne, via k-means."""
    ys, xs = np.where(grid > 0)
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    if len(pts) <= n:
        idx = np.random.default_rng(seed).integers(0, len(pts), n)
        return pts[idx]
    rng = np.random.default_rng(seed)
    init = pts[rng.choice(len(pts), n, replace=False)]
    cent, _ = kmeans2(pts, init, iter=12, minit='matrix', missing='warn')
    return cent


def main():
    ident = build_identity()
    gh = ident.shape[0]
    lua = build_logo('lua', gh)
    fivem = build_logo('fivem', gh)
    discord = build_logo('discord', gh)

    shapes = {'identity': ident, 'lua': lua, 'fivem': fivem, 'discord': discord}
    for i, (name, g) in enumerate(shapes.items()):
        p = sample_points(g, N_TRAVELLERS, seed=1000 + i)
        np.save(os.path.join(DATA, 'pts_' + name + '.npy'), p)
        print('pts_%-9s %d points echantillonnes' % (name, len(p)))


if __name__ == '__main__':
    main()
