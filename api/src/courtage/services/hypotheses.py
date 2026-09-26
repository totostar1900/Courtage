"""Les hypothèses d'une étude : ce qu'on peut régler, dans quelles bornes, et ce que chacune fait.

Un seul texte, lu par le formulaire, le rapport et le classeur. Chaque hypothèse dit son rôle, son effet sur
le chiffre et comment la fixer ; la valeur par défaut vient du référentiel. Une valeur hors bornes est refusée ici,
pas plus loin : le moteur ne reçoit que des hypothèses lisibles.

La rotation du personnel est uniforme par défaut (un taux pour tous les âges) ; elle peut être donnée par tranche
d'âge (`rotation_par_age`), chaque tranche courant de son âge de début jusqu'à la suivante, la dernière jusqu'à la
retraite.
"""
from collections.abc import Iterable
from math import floor

from courtage.erreurs import ErreurMetier
from courtage.referentiel import HYPOTHESES_PAR_DEFAUT, referentiel_courant

AGE_PREMIER_EMPLOI = 18
MAX_TRANCHES = 6

# champ : (libellé, nature, minimum, maximum)
BORNES: dict[str, tuple[str, str, float | None, float | None]] = {
    "taux_actualisation": ("Taux d'actualisation", "taux", -0.02, 0.15),
    "croissance_salaires": ("Croissance des salaires", "taux", -0.05, 0.15),
    "inflation": ("Inflation", "taux", -0.05, 0.20),
    "age_retraite": ("Âge de départ à la retraite", "age", 50, 70),
    "taux_turnover": ("Rotation du personnel", "taux", 0.0, 0.5),
    "rotation_par_age": ("Rotation par tranche d'âge", "tranches", 0.0, 0.5),
    "frais_sur_cotisation": ("Frais sur cotisation", "taux", 0.0, 0.2),
    "table": ("Table de mortalité", "table", None, None),
}
SAISISSABLES = tuple(BORNES)

SENSIBILITES = {
    "taux_actualisation_moins_1pt": "Taux d'actualisation − 1 point",
    "taux_actualisation_plus_1pt": "Taux d'actualisation + 1 point",
    "croissance_salaires_moins_1pt": "Croissance des salaires − 1 point",
    "croissance_salaires_plus_1pt": "Croissance des salaires + 1 point",
    "rotation_moins_1pt": "Rotation du personnel − 1 point",
    "rotation_plus_1pt": "Rotation du personnel + 1 point",
}

# Le rôle, l'effet et la façon de fixer chaque hypothèse. « {effet} » se remplace par l'effet mesuré sur l'étude
# quand il existe (les sensibilités), sinon par une phrase générale.
EXPLICATIONS: dict[str, dict[str, str]] = {
    "taux_actualisation": {
        "role": "Une indemnité versée dans 20 ans ne coûte pas son montant aujourd'hui : l'argent mis de côté d'ici "
                "là rapporte. Le taux d'actualisation ramène chaque versement futur à sa valeur d'aujourd'hui.",
        "effet": "Plus il est bas, plus l'engagement est lourd{effet}. C'est l'hypothèse qui pèse le plus sur le "
                 "résultat.",
        "fixer": "On retient le rendement de placements sûrs, d'une durée proche de celle de vos engagements (le temps "
                 "moyen avant les départs à la retraite). Un taux prudent protège l'entreprise d'une mauvaise surprise. "
                 "Un taux trop élevé embellit le chiffre sans rien changer à ce qui sera réellement payé.",
        "avec": "La croissance des salaires. C'est l'écart entre les deux qui compte : un taux de 3,5 % avec des "
                "salaires à +2 % pèse comme un taux de 5 % avec des salaires à +3,5 %.",
    },
    "croissance_salaires": {
        "role": "L'indemnité se calcule sur le dernier salaire. Ce taux projette le salaire d'aujourd'hui jusqu'au "
                "départ à la retraite.",
        "effet": "Plus il est haut, plus l'engagement est lourd{effet}.",
        "fixer": "Sur les augmentations des dernières années (générales, d'ancienneté, de promotion) et la politique "
                 "salariale annoncée. Une hausse exceptionnelle ne se prolonge pas sur trente ans.",
        "avec": "Le taux d'actualisation : c'est l'écart entre les deux qui compte.",
    },
    "inflation": {
        "role": "Elle s'ajoute à la croissance des salaires, quand celle-ci est exprimée hors inflation.",
        "effet": "Elle agit comme des points de croissance des salaires en plus : plus elle est haute, plus "
                 "l'engagement est lourd.",
        "fixer": "À zéro quand la croissance des salaires retenue comprend déjà l'inflation (c'est le cas par défaut). "
                 "Sinon, la cible d'inflation de la zone.",
        "avec": "La croissance des salaires : ne pas compter l'inflation deux fois.",
    },
    "age_retraite": {
        "role": "L'âge auquel l'indemnité est versée : il fixe l'ancienneté acquise au départ et la durée qui reste.",
        "effet": "Un départ plus tardif allonge l'ancienneté (l'indemnité grandit) mais éloigne le versement (sa valeur "
                 "d'aujourd'hui baisse) ; le sens dépend de la pyramide des âges.",
        "fixer": "L'âge légal du pays, ou l'âge prévu par votre convention ou votre régime s'il est différent.",
        "avec": "La table de mortalité et la rotation : plus le départ est loin, plus elles comptent.",
    },
    "taux_turnover": {
        "role": "La part des salariés qui quittent l'entreprise chaque année avant la retraite (démission, "
                "licenciement) : ils ne toucheront pas l'indemnité de départ à la retraite.",
        "effet": "Plus elle est haute, plus l'engagement est léger : beaucoup de salariés d'aujourd'hui ne seront plus "
                 "là au départ{effet}.",
        "fixer": "Sur les départs volontaires et les licenciements des trois à cinq dernières années, rapportés à "
                 "l'effectif. L'expérience réelle de l'étude le compare à ce qui est supposé.",
        "avec": "Par tranche d'âge si les jeunes partent bien plus que les anciens : un taux unique sous-estime alors "
                "l'engagement des seniors.",
    },
    "rotation_par_age": {
        "role": "La rotation, tranche d'âge par tranche d'âge : chaque tranche court de son âge jusqu'à la suivante, la "
                "dernière jusqu'à la retraite.",
        "effet": "Une rotation forte chez les jeunes et faible chez les seniors allège moins l'engagement qu'un taux "
                 "uniforme : ce sont les seniors, proches du départ, qui pèsent.",
        "fixer": "Sur les départs observés par âge ; trois tranches suffisent le plus souvent (moins de 30 ans, 30 à "
                 "45, au-delà).",
        "avec": "L'expérience réelle de l'étude, qui compare la rotation observée à celle supposée.",
    },
    "frais_sur_cotisation": {
        "role": "Les frais que l'assureur prélève sur chaque cotisation versée au fonds.",
        "effet": "Sans effet sur la dette : ils s'ajoutent à la cotisation à verser (cotisation totale = cotisation "
                 "nette × (1 + frais)).",
        "fixer": "Sur le contrat en place, ou sur les conditions demandées aux assureurs.",
        "avec": "Le cahier des charges, qui demande un plafond de frais aux assureurs.",
    },
    "table": {
        "role": "La probabilité d'être encore en vie à l'âge de la retraite : une indemnité n'est versée qu'à un "
                "salarié vivant.",
        "effet": "Une table plus favorable à la survie alourdit légèrement l'engagement ; l'effet reste faible avant "
                 "la retraite.",
        "fixer": "La table réglementaire CIMA. La table féminine (TF), plus prudente, s'applique à tous par défaut.",
        "avec": "L'âge de la retraite.",
    },
}

def tables() -> list[dict]:
    """Les tables de mortalité du référentiel ; la table masculine s'ajoutera quand sa source sera versée."""
    connues = referentiel_courant().tables
    liste = [{"code": t.code, "libelle": t.libelle, "disponible": True} for t in connues.values()]
    if not any("_H" in code for code in connues):
        liste.append({"code": "TV_CIMA_H", "libelle": "Table de mortalité CIMA H (hommes)", "disponible": False,
                      "raison": "À venir : la table sera ajoutée au référentiel avec sa source."})
    return liste


def catalogue() -> dict:
    """Ce que le formulaire affiche : défauts, bornes, explications et tables."""
    return {
        "defauts": {**HYPOTHESES_PAR_DEFAUT, "rotation_par_age": None},
        "champs": [{"champ": c, "libelle": l, "nature": n, "min": mn, "max": mx, **EXPLICATIONS[c]}
                   for c, (l, n, mn, mx) in BORNES.items()],
        "tables": tables(),
        "age_premier_emploi": AGE_PREMIER_EMPLOI,
    }


def lire(champ: str, valeur, age_retraite: int | None = None):
    """La valeur saisie, contrôlée ; une erreur métier sinon."""
    if champ not in BORNES:
        raise ErreurMetier("hypothese_inconnue", f"Hypothèse inconnue : {champ}.", 422)
    libelle, nature, mn, mx = BORNES[champ]
    try:
        if nature == "table":
            if valeur not in referentiel_courant().tables:
                raise ErreurMetier("table_indisponible", f"La table {valeur} n'est pas au référentiel.", 422)
            return str(valeur)
        if nature == "tranches":
            return _tranches(valeur, mn, mx, age_retraite)
        v = int(valeur) if nature == "age" else float(valeur)
        if nature == "age" and v != float(valeur):
            raise ValueError
    except (TypeError, ValueError):
        raise ErreurMetier("hypothese_invalide", f"{libelle} : valeur illisible.", 422, {"champ": champ}) from None
    if not (mn <= v <= mx):
        borne = (lambda x: f"{x:g} ans") if nature == "age" else (lambda x: f"{x * 100:g} %")
        raise ErreurMetier("hypothese_hors_bornes", f"{libelle} : entre {borne(mn)} et {borne(mx)}.", 422,
                           {"champ": champ})
    return v


def _tranches(valeur, mn: float, mx: float, age_retraite: int | None) -> list[dict] | None:
    if valeur in (None, []):
        return None
    if not isinstance(valeur, list) or len(valeur) > MAX_TRANCHES:
        raise ErreurMetier("rotation_invalide", f"La rotation par âge tient en 1 à {MAX_TRANCHES} tranches.", 422)
    tranches = []
    for t in valeur:
        if not isinstance(t, dict) or set(t) != {"des", "taux"}:
            raise ErreurMetier("rotation_invalide", "Chaque tranche donne son âge de début et son taux.", 422)
        des, taux = int(t["des"]), float(t["taux"])
        if not (mn <= taux <= mx):
            raise ErreurMetier("rotation_invalide", f"Le taux d'une tranche va de 0 à {mx * 100:g} %.", 422)
        tranches.append({"des": des, "taux": taux})
    ages = [t["des"] for t in tranches]
    if ages[0] != AGE_PREMIER_EMPLOI or ages != sorted(set(ages)):
        raise ErreurMetier("rotation_invalide", f"Les tranches commencent à {AGE_PREMIER_EMPLOI} ans, dans l'ordre "
                                                "des âges, sans doublon.", 422)
    if age_retraite is not None and ages[-1] >= age_retraite:
        raise ErreurMetier("rotation_invalide", "Une tranche commence après l'âge de la retraite.", 422)
    return tranches


def valeurs_et_ecarts(saisies: dict) -> tuple[dict, list[dict]]:
    """Les hypothèses retenues (le référentiel, complété par la saisie) et leurs écarts au référentiel."""
    defauts = {**HYPOTHESES_PAR_DEFAUT, "rotation_par_age": None}
    for champ in saisies:
        if champ not in BORNES:
            raise ErreurMetier("hypothese_inconnue", f"Hypothèse inconnue : {champ}.", 422)
    valeurs = dict(defauts)
    if "age_retraite" in saisies:
        valeurs["age_retraite"] = lire("age_retraite", saisies["age_retraite"])
    for champ, valeur in saisies.items():
        if champ != "age_retraite":
            valeurs[champ] = lire(champ, valeur, valeurs["age_retraite"])
    ecarts = [{"champ": c, "referentiel": defauts[c], "retenu": valeurs[c]}
              for c in BORNES if valeurs[c] != defauts[c]]
    if valeurs["rotation_par_age"] is None:
        del valeurs["rotation_par_age"]
    return valeurs, ecarts


def turnover(valeurs: dict) -> dict[int, float]:
    """Le taux de sortie à chaque âge, de 18 ans à la veille de la retraite."""
    tranches = valeurs.get("rotation_par_age")
    ages = range(AGE_PREMIER_EMPLOI, valeurs["age_retraite"])
    if not tranches:
        return {a: valeurs["taux_turnover"] for a in ages}
    return {a: next(t["taux"] for t in reversed(tranches) if t["des"] <= a) for a in ages}


def taux_moyen(valeurs: dict, ages: Iterable[float]) -> float:
    """La rotation moyenne de la population : le taux de chacun à son âge. Uniforme, c'est le taux lui-même."""
    if not valeurs.get("rotation_par_age"):
        return valeurs["taux_turnover"]
    par_age = turnover(valeurs)
    taux = [par_age.get(max(floor(a), AGE_PREMIER_EMPLOI), 0.0) for a in ages]
    return round(sum(taux) / len(taux), 4) if taux else valeurs["taux_turnover"]


def pct(v: float) -> str:
    return f"{v * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


def en_texte(champ: str, valeur) -> str:
    """Une hypothèse telle qu'un lecteur la lit : « 3,5 % », « 60 ans », « 18 ans : 6 % ; 30 ans : 3 % »."""
    if valeur is None:
        return "uniforme" if champ == "rotation_par_age" else "—"
    nature = BORNES.get(champ, ("", "texte"))[1]
    if nature == "taux":
        return pct(valeur)
    if nature == "age":
        return f"{valeur} ans"
    if nature == "tranches":
        return " ; ".join(f"dès {t['des']} ans : {pct(t['taux'])}" for t in valeur)
    if nature == "table":
        return next((t["libelle"] for t in tables() if t["code"] == valeur), str(valeur))
    return str(valeur)


def rotation_en_texte(valeurs: dict) -> str:
    if valeurs.get("rotation_par_age"):
        return "par tranche d'âge — " + en_texte("rotation_par_age", valeurs["rotation_par_age"])
    return f"{pct(valeurs['taux_turnover'])} par an, à tout âge"


def ecarts_en_texte(ecarts: list[dict]) -> list[dict]:
    return [{"libelle": BORNES.get(e["champ"], (e["champ"],))[0], "referentiel": en_texte(e["champ"], e["referentiel"]),
             "retenu": en_texte(e["champ"], e["retenu"])} for e in ecarts]


def pour_le_lecteur(valeurs: dict, ecarts: list[dict], sensibilites: dict | None, dette: float | None) -> list[dict]:
    """Chaque hypothèse de l'étude, pour le rapport : défaut, retenue, rôle, effet mesuré, comment la fixer."""
    ecartes = {e["champ"] for e in ecarts}
    effets = _effets(sensibilites or {}, dette)
    lignes = []
    for champ in ("taux_actualisation", "croissance_salaires", "inflation", "age_retraite", "taux_turnover",
                  "frais_sur_cotisation", "table"):
        if champ not in valeurs:
            continue
        defaut = HYPOTHESES_PAR_DEFAUT.get(champ)
        retenu = valeurs[champ]
        if champ == "taux_turnover":
            retenu_txt = rotation_en_texte(valeurs)
            ecarte = bool(ecartes & {"taux_turnover", "rotation_par_age"})
            explications = EXPLICATIONS["rotation_par_age" if valeurs.get("rotation_par_age") else champ]
        else:
            retenu_txt, ecarte, explications = en_texte(champ, retenu), champ in ecartes, EXPLICATIONS[champ]
        lignes.append({
            "champ": champ, "libelle": BORNES[champ][0], "defaut": en_texte(champ, defaut), "retenu": retenu_txt,
            "ecarte": ecarte, "role": explications["role"],
            "effet": explications["effet"].replace("{effet}", effets.get(champ, "")),
            "fixer": explications["fixer"],
        })
    return lignes


def _effets(sensibilites: dict, dette: float | None) -> dict[str, str]:
    if not dette:
        return {}

    def part(cle: str) -> float | None:
        s = sensibilites.get(cle)
        return None if s is None else (s["dette"] - dette) / dette

    effets = {}
    if (x := part("taux_actualisation_moins_1pt")) is not None:
        effets["taux_actualisation"] = f" : sur cette étude, 1 point de moins augmente la dette de {pct(abs(x))}"
    if (x := part("croissance_salaires_plus_1pt")) is not None:
        effets["croissance_salaires"] = f" : sur cette étude, 1 point de plus augmente la dette de {pct(abs(x))}"
    if (x := part("rotation_plus_1pt")) is not None:
        effets["taux_turnover"] = f" ; sur cette étude, 1 point de plus réduit la dette de {pct(abs(x))}"
    return effets
