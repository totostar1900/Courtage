# Identité « Glacier »

Choisie le 2026-09-29 parmi trois directions (A · Glacier, B · Slate & Signal, C · Frost Private). Le nom et le
logotype viendront plus tard ; tout ce qui suit s'y adaptera sans réécriture.

## Les principes

- **Des traits, pas des ombres.** Une surface se détache par un trait d'un pixel ; l'ombre est réservée à ce qui
  flotte (menu, palette, panneau).
- **Des angles de 2 px** (`--rayon`). Rien de rond, sauf un drapeau.
- **Un seul cyan** (`--accent`, `--indigo-vif`, `--ocre`) pour ce qui compte sur l'écran : un lien, le focus, l'étape
  en cours, la barre qui compte. Le bouton principal est à l'encre, pas en couleur.
- **Geist** pour le texte ; **Geist Mono** pour les chiffres (montants, taux, dates en tableau) et les étiquettes en
  capitales espacées. Les offres s'alignent chiffre à chiffre.
- **Trois thèmes**, dessinés chacun : blanc de glace et encre polaire ; **pénombre**, un gris neutre à mi-chemin (L* 33
  à 37, quand le clair est à 97 et le sombre à 3 ; chaque couleur au moins à 4,5:1 sur la surface) ; nuit polaire et
  glace. Celui de l'appareil par défaut ; « Automatique · Clair · Pénombre · Sombre » à côté de FR · EN (`theme.ts`,
  `data-theme` sur la racine : `light`, `dim`, `dark`). À
  l'impression, toujours clair. Les documents scellés (PDF) ne changent pas : ce sont des documents.

## Les jetons

Ils gardent les noms d'avant (`--indigo`, `--ocre`…), si bien que chaque règle a changé de peau sans être réécrite :
tête de `styles.css`, trois blocs générés d'une même table (clair, sombre, impression). Une couleur écrite en dur
dans une règle est un défaut : elle ne suit pas le thème. Exceptions voulues : les bulles noires des graphiques
(noires dans les deux thèmes), le vert de WhatsApp, et les couleurs des séries de graphiques (`echeancier.ts`,
`comparatif.ts`), choisies lisibles sur les deux fonds parce qu'un attribut SVG ne lit pas une variable CSS.

## Ce qui reste

- Rien : le nom, le logotype, l'icône, l'image d'aperçu et `theme-color` sont posés (`marque-nitch.md`).
