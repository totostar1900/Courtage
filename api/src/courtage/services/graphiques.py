"""Les graphiques du rapport, en SVG écrit à la main : WeasyPrint les imprime nets, sans bibliothèque.

Sobres et imprimables : un seul axe, des marques fines aux bouts arrondis posées sur la ligne de base, une grille
discrète, le texte en encre (jamais dans la couleur d'une série), une légende dès deux séries et une étiquette
directe au bout de chaque courbe. Les couleurs sont celles de l'application : #2a78d6 puis #eb6834, validées pour les
daltonismes ; une série seule prend l'indigo de l'échéancier.
"""
from math import floor, log10
from xml.sax.saxutils import escape

ENCRE, DISCRET, GRILLE = "#1b2240", "#55607a", "#dfe2ee"
ENSEMBLE = "#2f419a"
SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
POLICE = 'font-family="DejaVu Sans, sans-serif"'


def _svg(largeur: int, hauteur: int, corps: list[str], titre: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largeur} {hauteur}" width="100%" role="img" '
            f'aria-label="{escape(titre)}" {POLICE}>' + "".join(corps) + "</svg>")


def _texte(x: float, y: float, t: str, taille: float = 10, couleur: str = DISCRET, ancre: str = "start",
           gras: bool = False) -> str:
    poids = ' font-weight="bold"' if gras else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{taille}" fill="{couleur}" text-anchor="{ancre}"{poids}>'
            f"{escape(t)}</text>")


def haut_rond(maximum: float) -> float:
    """Un haut d'axe rond, au-dessus du maximum."""
    if maximum <= 0:
        return 1.0
    puissance = 10 ** floor(log10(maximum))
    return next(f * puissance for f in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10) if f * puissance >= maximum)


def compact(v: float) -> str:
    if v >= 1e9:
        return f"{v / 1e9:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " Md"
    if v >= 1e6:
        return f"{v / 1e6:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " M"
    if v >= 1e3:
        return f"{v / 1e3:.0f} k"
    return f"{v:g}".replace(".", ",")


def _barre_verticale(x: float, base: float, largeur: float, hauteur: float, couleur: str) -> str:
    """Une barre posée sur la ligne de base, arrondie en haut seulement."""
    if hauteur <= 0:
        return ""
    r = min(4.0, largeur / 2, hauteur)
    y = base - hauteur
    return (f'<path d="M{x:.1f},{base:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
            f'H{x + largeur - r:.1f} Q{x + largeur:.1f},{y:.1f} {x + largeur:.1f},{y + r:.1f} V{base:.1f} Z" '
            f'fill="{couleur}"/>')


def _barre_horizontale(x: float, y: float, longueur: float, epaisseur: float, couleur: str) -> str:
    if longueur <= 0:
        return ""
    r = min(4.0, epaisseur / 2, longueur)
    return (f'<path d="M{x:.1f},{y:.1f} H{x + longueur - r:.1f} Q{x + longueur:.1f},{y:.1f} {x + longueur:.1f},{y + r:.1f} '
            f'V{y + epaisseur - r:.1f} Q{x + longueur:.1f},{y + epaisseur:.1f} {x + longueur - r:.1f},{y + epaisseur:.1f} '
            f'H{x:.1f} Z" fill="{couleur}"/>')


def histogramme(titre: str, groupes: list[tuple[str, int]], largeur: int = 300) -> str:
    """Des effectifs par tranche, en barres horizontales, le nombre au bout de chaque barre."""
    gauche, pas, epaisseur = 86, 20, 14
    hauteur = 22 + pas * len(groupes) + 4
    maximum = max((n for _, n in groupes), default=0) or 1
    utile = largeur - gauche - 34
    corps = [_texte(0, 12, titre, 10.5, ENCRE, gras=True)]
    for i, (libelle, n) in enumerate(groupes):
        y = 22 + i * pas
        corps.append(_texte(gauche - 6, y + epaisseur - 3, libelle, 9, DISCRET, "end"))
        longueur = n / maximum * utile
        corps.append(_barre_horizontale(gauche, y, longueur, epaisseur, ENSEMBLE))
        corps.append(_texte(gauche + longueur + 4, y + epaisseur - 3, str(n), 9, ENCRE))
    corps.append(f'<line x1="{gauche}" y1="20" x2="{gauche}" y2="{hauteur - 2}" stroke="{DISCRET}" stroke-width="1"/>')
    return _svg(largeur, hauteur, corps, titre)


def courbes(titre: str, series: list[tuple[str, list[tuple[int, float]]]], reference: str | None = None,
            unite: str = "mois", largeur: int = 640, hauteur: int = 240) -> str:
    """Des courbes sur un axe commun : l'ancienneté en abscisse, les mois de salaire en ordonnée.

    `reference` nomme la série de comparaison (la convention) : tracée d'abord, en tirets gris, pour que les
    autres, pleines et colorées, restent visibles quand elles la recouvrent."""
    gauche, droite, haut, bas = 44, 150, 40, 30
    xs = [x for _, pts in series for x, _ in pts]
    x0, x1 = min(xs), max(xs)
    ymax = haut_rond(max((y for _, pts in series for _, y in pts), default=1))
    px = lambda x: gauche + (x - x0) / ((x1 - x0) or 1) * (largeur - gauche - droite)  # noqa: E731
    py = lambda y: haut + (1 - y / ymax) * (hauteur - haut - bas)  # noqa: E731
    corps = [_texte(0, 12, titre, 10.5, ENCRE, gras=True)]
    for g in (0, ymax / 2, ymax):
        corps.append(f'<line x1="{gauche}" y1="{py(g):.1f}" x2="{largeur - droite}" y2="{py(g):.1f}" '
                     f'stroke="{GRILLE}" stroke-width="1"/>')
        corps.append(_texte(gauche - 6, py(g) + 3, f"{g:g}".replace(".", ","), 9, DISCRET, "end"))
    corps.append(_texte(gauche - 6, haut - 12, unite, 8.5, DISCRET, "end"))
    for a in range(x0, x1 + 1, 5):
        corps.append(_texte(px(a), hauteur - bas + 14, f"{a}", 9, DISCRET, "middle"))
    corps.append(_texte((gauche + largeur - droite) / 2, hauteur - 4, "ancienneté (années)", 8.5, DISCRET, "middle"))
    etiquettes = []
    propres = [x for x in series if x[0] != reference]
    ordre = [x for x in series if x[0] == reference] + propres
    for nom, pts in ordre:
        if nom == reference:
            couleur, style = DISCRET, ' stroke-dasharray="5 3"'
        else:
            i = propres.index((nom, pts))
            couleur, style = (SERIES[i % len(SERIES)] if len(propres) > 1 else ENSEMBLE), ""
        chemin = " ".join(f"{'M' if j == 0 else 'L'}{px(x):.1f},{py(y):.1f}" for j, (x, y) in enumerate(pts))
        corps.append(f'<path d="{chemin}" fill="none" stroke="{couleur}" stroke-width="2" '
                     f'stroke-linejoin="round"{style}/>')
        etiquettes.append([py(pts[-1][1]), nom, couleur, px(pts[-1][0])])
    # Les étiquettes au bout des courbes, écartées pour ne pas se chevaucher.
    etiquettes.sort()
    for j in range(1, len(etiquettes)):
        etiquettes[j][0] = max(etiquettes[j][0], etiquettes[j - 1][0] + 12)
    for y, nom, couleur, x in etiquettes:
        corps.append(f'<circle cx="{x + 8:.1f}" cy="{y - 3:.1f}" r="3" fill="{couleur}"/>')
        corps.append(_texte(x + 14, y, nom[:26], 9, ENCRE))
    return _svg(largeur, hauteur, corps, titre)


def echeancier(titre: str, annees: list[tuple[int, float]], fonds: float | None = None, cumul: bool = False,
               largeur: int = 640, hauteur: int = 200) -> str:
    """Les versements par année (ou cumulés), une colonne par année ; en cumulé, le fonds constitué en repère."""
    gauche, droite, haut, bas = 52, 8, 26, 22
    valeurs, total = [], 0.0
    for _, v in annees:
        total = total + v if cumul else v
        valeurs.append(total)
    ymax = haut_rond(max(valeurs + ([fonds] if fonds else []), default=1))
    n = len(annees) or 1
    pas = (largeur - gauche - droite) / n
    epaisseur = max(pas - 2, 1.5)
    base = hauteur - bas
    py = lambda y: haut + (1 - y / ymax) * (base - haut)  # noqa: E731
    corps = [_texte(0, 12, titre, 10.5, ENCRE, gras=True)]
    for g in (0, ymax / 2, ymax):
        corps.append(f'<line x1="{gauche}" y1="{py(g):.1f}" x2="{largeur - droite}" y2="{py(g):.1f}" '
                     f'stroke="{GRILLE}" stroke-width="1"/>')
        corps.append(_texte(gauche - 6, py(g) + 3, compact(g), 9, DISCRET, "end"))
    reperes = {a for a, _ in annees if a % 5 == 0} if n > 12 else {a for a, _ in annees}
    for i, ((a, _), v) in enumerate(zip(annees, valeurs)):
        x = gauche + i * pas + 1
        corps.append(_barre_verticale(x, base, epaisseur, base - py(v), ENSEMBLE))
        if a in reperes:
            corps.append(_texte(x + epaisseur / 2, base + 13, str(a), 8.5, DISCRET, "middle"))
    if fonds:
        y = py(fonds)
        corps.append(f'<line x1="{gauche}" y1="{y:.1f}" x2="{largeur - droite}" y2="{y:.1f}" stroke="{ENCRE}" '
                     f'stroke-width="1.2" stroke-dasharray="4 3"/>')
        # La légende du repère, hors du tracé : posée sur les barres, elle serait illisible.
        libelle = f"Fonds constitué : {compact(fonds)}"
        x = largeur - droite - 7 * len(libelle) * 0.78
        corps.append(f'<line x1="{x - 26:.1f}" y1="8.5" x2="{x - 6:.1f}" y2="8.5" stroke="{ENCRE}" stroke-width="1.2" '
                     f'stroke-dasharray="4 3"/>')
        corps.append(_texte(x, 12, libelle, 9, ENCRE))
    return _svg(largeur, hauteur, corps, titre)
