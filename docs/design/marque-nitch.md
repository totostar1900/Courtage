# La marque « Nitch »

Choisie le 2026-09-29 parmi six logotypes (A · le point, B · la lame, C · la ligne de glace, D · le curseur, E et F :
leurs mélanges). Retenu : **A · le point**. Le nom peut encore changer ; tout ce qui suit est rangé pour qu'il se
remplace en un seul passage.

## Le logotype

« nitch » en minuscules, Geist Sans 600, serré (approche −34 sur 1 000). Le point du i devient un **carré à l'accent**
(`--accent`), de la largeur du fût : le même carré que les angles de 2 px et le seul cyan de l'identité. Tracé depuis
les contours de Geist (fontTools), il ne dépend d'aucune police chargée.

- `web/src/composants/Marque.tsx` : le logotype en SVG. L'encre suit `color`, le carré suit `--accent` : il change
  de thème avec l'écran. En tête de chaque page, lien vers l'accueil (« Nitch, accueil »).
- `web/public/favicon.svg` et `apple-touch-icon.png` (180 px) : le n clair sur une tuile d'encre, le carré cyan en
  haut à droite. Couleurs figées (un favicon ne lit pas les jetons) : lisible sur un onglet clair comme sombre.
- `web/public/apercu.png` (1 200 × 630) : l'aperçu d'un lien partagé, sur la nuit polaire.
- `theme-color` : une couleur par thème de l'appareil dans `index.html` ; un thème imposé (`theme.ts`) aligne les
  deux sur lui.

## Où le nom paraît

- Titres d'onglet « … — Nitch » (`Titre.tsx`), `<title>` et `og:site_name` (`index.html`), titre de l'API.
- Pied de page : « Nitch · exploitée par {cabinet}, courtier agréé {agrément} ». La marque n'est pas une personne :
  le cabinet reste nommé, sous son nom légal.
- SMS de code (connexion, inscription) : « Nitch : votre code… ». Le modèle WhatsApp des avis : `Nitch : {{1}} —
  {{2}}`, à créer et faire approuver chez Twilio (DEPLOY.md) ; un modèle approuvé sous l'ancien nom garde son texte.

## Ce qui ne change pas

- « courtage », nom commun, dans le texte : c'est le métier.
- Les documents scellés : ils portent le nom légal du cabinet, pas une marque.
- Les noms techniques (`courtage_session`, `X-Courtage`, `COURTAGE_*`, le paquet Python) : renommer un cookie
  déconnecte tout le monde, renommer une variable casse un déploiement, pour aucun gain visible.
