# Mise en ligne — ce qui reste à faire à la main

Tout le code est prêt et vérifié en local. Les étapes ci-dessous demandent tes
identifiants GitHub et Vercel, que je n'ai pas : `gh` n'est pas installé sur
cette machine et aucun credential Git n'y est enregistré.

---

## 1. Créer le dépôt de profil

Vérifié le 9 septembre 2026 : `NXT-DEVOFF/NXT-DEVOFF` **n'existe pas encore**
(l'API renvoie `Not Found`, et tes trois dépôts publics sont `bl-host`,
`HeliosLauncher` et `NXT-Project-uptime`).

Le nom du dépôt n'est pas libre : pour qu'un README s'affiche sur ton profil,
il doit s'appeler **exactement** comme ton compte.

1. <https://github.com/new>
2. Repository name : `NXT-DEVOFF`
3. Public
4. **Ne coche pas** « Add a README » — il y en a déjà un ici
5. Create repository

## 2. Pousser le contenu

Depuis `C:\Users\nxt\Desktop\github\NXT-DEVOFF` :

```bash
git remote add origin https://github.com/NXT-DEVOFF/NXT-DEVOFF.git
git branch -M main
git push -u origin main
```

Ton identité Git est déjà configurée (`NXT-DEVOFF` / `kikilebg51@gmail.com`).

## 3. Autoriser les Actions à écrire

Sans ça, le snake échouera avec une erreur de permission.

`Settings` → `Actions` → `General` → `Workflow permissions` →
**Read and write permissions** → `Save`.

> C'est bien dans les réglages **du dépôt**, pas ceux de ton compte.

## 4. Lancer le snake

`Actions` → `Snake de contributions` → `Run workflow`.

Attends que le job passe au **vert**, puis décommente le bloc snake dans
`README.md`. La branche `output` n'existe pas avant ce premier run réussi :
décommenter trop tôt afficherait deux images cassées.

> Ton compte datant de mars 2026, la grille sera clairsemée au début. C'est
> normal, elle se remplit avec le temps.

## 5. Déployer ton instance de stats

**Cette étape n'est pas optionnelle.** L'instance publique
`github-readme-stats.vercel.app` renvoie `503 DEPLOYMENT_PAUSED` — testé trois
fois le 9 septembre 2026. Elle est arrêtée, pas seulement saturée. Sans
instance personnelle, les deux cartes ne peuvent pas s'afficher.

1. **Token GitHub** : `Settings` → `Developer settings` → `Personal access
   tokens` → `Tokens (classic)` → `Generate new token (classic)`.
   Scope **`repo`**, expiration **No expiration**.
   Copie-le tout de suite, il ne sera plus jamais affiché — et ne le colle
   nulle part en public.
2. Fork <https://github.com/anuraghazra/github-readme-stats>
3. <https://vercel.com> → inscription avec GitHub → plan **Hobby** (gratuit)
4. `Add New Project` → importe ton fork
5. Variable d'environnement : `PAT_1` = ton token
6. `Deploy`
7. Récupère ton domaine (`quelque-chose.vercel.app`), remplace les deux
   occurrences de `TON-INSTANCE.vercel.app` dans `README.md`, puis décommente
   le bloc des cartes de stats.

---

## Regénérer la bannière

```bash
python generator/build.py
```

Les `.npy` et les scripts sont la source de vérité, pas les SVG — ceux-ci sont
écrasés à chaque exécution. Ne les édite jamais à la main.

Dépendances : `pip install pillow numpy scipy` (wheels `cp314` disponibles).

## Vérifier un rendu

`cairosvg` ne convient pas : il ne rend que la première image SMIL et gère mal
`textLength`. En plus, il exige une DLL cairo absente sous Windows. Utilise
Chrome en pilotant le temps virtuel :

```bash
chrome --headless=new --no-sandbox --disable-gpu \
  --window-size=1180,610 --virtual-time-budget=8500 \
  --screenshot="C:/chemin/absolu/sortie.png" \
  "file:///C:/Users/nxt/Desktop/github/NXT-DEVOFF/assets/banner-dark.svg"
```

Le chemin de `--screenshot` doit être **absolu**, sinon Chrome refuse d'écrire.

Repères de temps : `1500` apparition, `4000` logo NXT DEV, `8500` Lua,
`11800` FiveM, `15000` Discord.

## Si « rien n'a changé » après un push

C'est presque toujours le cache du CDN, pas un bug. Vérifie le fichier
réellement servi :

```
raw.githubusercontent.com/NXT-DEVOFF/NXT-DEVOFF/main/assets/banner-dark.svg?v=999
```

Vérifie aussi que tu es dans le bon thème : les assets sombres ne s'affichent
qu'en mode sombre.
