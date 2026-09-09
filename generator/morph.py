"""Etape 2 : calcule les mouvements des deux couches.

Produit dans data/ :
  travellers.npy    (4, 900, 2)  positions appariees par transport optimal
  bands.npy         (N,)         bande de derive de chaque point d'identite
  band_drift.npy    (94, 2)      translation propre a chaque bande
  intro_groups.npy  (N,)         groupe d'apparition de chaque point

Deux pieges du prompt source sont traites ici, et chacun est verifie par une
mesure imprimee a l'execution :

* Le piege de la grille. La derive est une fonction lineaire de la position :
  la quantifier en bandes recree mathematiquement un quadrillage carre, et la
  dissolution parait alors en damier. Un bruit gaussien par point (sigma 4) est
  injecte AVANT le groupement. `metrique_frontiere` compare les deux cas.

* Le piege du balayage. Les groupes d'apparition doivent etre disperses sur
  toute l'image pour que les points epaississent partout a la fois. Un
  groupement spatial revelerait l'image par plaques. `metrique_uniformite`
  compare une affectation aleatoire a un decoupage spatial.
"""
import os
import numpy as np
from scipy.optimize import linear_sum_assignment

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')

SEQUENCE = ['identity', 'lua', 'fivem', 'discord']
BINS = 10                  # 10 x 10 tuiles, les vides retirees -> ~94 bandes
N_INTRO = 60
DRIFT_FRACTION = 0.42      # part du trajet vers le centroide de la 1re forme
NOISE_SIGMA = 4.0          # bruit par point, avant groupement


def match_chain():
    """Apparie les nuees consecutives par transport optimal (cout quadratique)."""
    pts = {n: np.load(os.path.join(DATA, 'pts_%s.npy' % n)) for n in SEQUENCE}
    ordered = [pts['identity']]
    total = 0.0
    for prev_name, name in zip(SEQUENCE, SEQUENCE[1:]):
        a = ordered[-1]
        b = pts[name]
        cost = ((a[:, None, :] - b[None, :, :]) ** 2).sum(axis=2)
        ri, ci = linear_sum_assignment(cost)
        ordered.append(b[ci])
        d = np.sqrt(cost[ri, ci]).mean()
        total += d
        print('transport %-8s -> %-8s  trajet moyen %.1f cellules' % (prev_name, name, d))
    print('trajet moyen cumule : %.1f cellules' % total)
    return np.stack(ordered)          # (4, 900, 2)


def metrique_frontiere(labels, coords, shape):
    """Mesure la rectitude des frontieres entre bandes.

    Construit une image d'etiquettes, puis regarde si les positions de rupture
    coincident d'une ligne a la suivante. Un quadrillage aligne ses ruptures et
    fait monter le score ; un decoupage organique les disperse.
    """
    img = np.full(shape, -1, np.int32)
    img[coords[:, 1], coords[:, 0]] = labels
    common = 0
    total = 0
    for y in range(shape[0] - 1):
        r0, r1 = img[y], img[y + 1]
        b0 = {x for x in range(shape[1] - 1)
              if r0[x] >= 0 and r0[x + 1] >= 0 and r0[x] != r0[x + 1]}
        b1 = {x for x in range(shape[1] - 1)
              if r1[x] >= 0 and r1[x + 1] >= 0 and r1[x] != r1[x + 1]}
        if not b0 or not b1:
            continue
        common += len(b0 & b1)
        total += len(b0 | b1)
    return common / total if total else 0.0


def metrique_uniformite(groups, coords, shape, tiles=8):
    """Mesure la dispersion spatiale des groupes d'apparition.

    Pour chaque groupe, compare sa repartition en tuiles a la repartition
    globale (distance de variation totale). Proche de 0 : le groupe couvre
    toute l'image. Proche de 1 : il occupe une plaque.
    """
    ty = np.clip((coords[:, 1] * tiles // shape[0]), 0, tiles - 1)
    tx = np.clip((coords[:, 0] * tiles // shape[1]), 0, tiles - 1)
    cell = ty * tiles + tx
    overall = np.bincount(cell, minlength=tiles * tiles).astype(np.float64)
    overall /= overall.sum()
    scores = []
    for g in np.unique(groups):
        h = np.bincount(cell[groups == g], minlength=tiles * tiles).astype(np.float64)
        if h.sum() == 0:
            continue
        h /= h.sum()
        scores.append(0.5 * np.abs(h - overall).sum())
    return float(np.mean(scores))


def _quantize(coords, rng, sigma):
    """Quantifie les positions en tuiles BINS x BINS, avec bruit optionnel.

    Une bande doit rester un paquet spatial : ses points partagent une seule
    translation, ce qui n'a de sens que s'ils derivent de facon semblable. La
    quantification par quantiles produit donc des tuiles — et c'est exactement
    le quadrillage que le prompt source signale. Le bruit par point, applique
    AVANT la quantification, desaligne les frontieres sans disperser les
    paquets.
    """
    p = coords.copy()
    if sigma > 0:
        p = p + rng.normal(0.0, sigma, size=p.shape)
    qs = np.linspace(0, 1, BINS + 1)[1:-1]
    ix = np.searchsorted(np.quantile(p[:, 0], qs), p[:, 0])
    iy = np.searchsorted(np.quantile(p[:, 1], qs), p[:, 1])
    raw = iy * BINS + ix
    uniq, labels = np.unique(raw, return_inverse=True)   # tuiles vides retirees
    return labels, len(uniq)


def build_bands(coords, target, rng):
    """Groupe les points en bandes de derive, bruit injecte avant quantification."""
    drift = DRIFT_FRACTION * (target[None, :] - coords)

    labels, n_noisy = _quantize(coords, rng, NOISE_SIGMA)
    plain, n_plain = _quantize(coords, rng, 0.0)

    band_drift = np.zeros((n_noisy, 2))
    for b in range(n_noisy):
        m = labels == b
        if m.any():
            band_drift[b] = drift[m].mean(axis=0)
    print('bandes non vides : %d avec bruit, %d sans' % (n_noisy, n_plain))
    return labels, plain, band_drift


def main():
    travellers = match_chain()
    np.save(os.path.join(DATA, 'travellers.npy'), travellers)

    ident = np.load(os.path.join(DATA, 'identity.npy'))
    ys, xs = np.where(ident)
    coords = np.stack([xs, ys], axis=1).astype(np.float64)
    shape = ident.shape
    rng = np.random.default_rng(7)

    target = np.load(os.path.join(DATA, 'pts_lua.npy')).mean(axis=0)
    labels, plain, band_drift = build_bands(coords, target, rng)
    np.save(os.path.join(DATA, 'bands.npy'), labels.astype(np.int16))
    np.save(os.path.join(DATA, 'band_drift.npy'), band_drift)

    ci = coords.astype(int)
    f_noisy = metrique_frontiere(labels, ci, shape)
    f_plain = metrique_frontiere(plain, ci, shape)
    print()
    print('frontiere droite  sans bruit %.3f   avec bruit sigma=%.0f  %.3f'
          % (f_plain, NOISE_SIGMA, f_noisy))
    print('  -> %s' % ('bruit efficace, frontieres desalignees'
                       if f_noisy < f_plain * 0.5 else
                       'ATTENTION : le bruit ne casse pas le quadrillage'))

    intro = rng.integers(0, N_INTRO, size=len(coords))
    np.save(os.path.join(DATA, 'intro_groups.npy'), intro.astype(np.int16))

    order = np.argsort(coords[:, 1] * shape[1] + coords[:, 0])
    spatial = np.zeros(len(coords), np.int64)
    spatial[order] = np.arange(len(coords)) * N_INTRO // len(coords)
    u_rand = metrique_uniformite(intro, ci, shape)
    u_spat = metrique_uniformite(spatial, ci, shape)
    print('uniformite intro  aleatoire %.3f   spatial (contre-exemple) %.3f'
          % (u_rand, u_spat))
    print('  -> %s' % ('dispersion correcte, pas de balayage'
                       if u_rand < 0.2 else
                       'ATTENTION : apparition par plaques'))

    print()
    print('points identite %d   bandes %d   groupes intro %d   travellers %d'
          % (len(coords), len(band_drift), N_INTRO, travellers.shape[1]))


if __name__ == '__main__':
    main()
