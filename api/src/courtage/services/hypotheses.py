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
from courtage.langue import langue, t
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

# L'anglais de l'écran (`X-Langue: en`). Le français ci-dessus reste le texte du rapport, de la fiche et du
# classeur, qui se scellent : seuls le formulaire et les messages d'erreur passent par ces fonctions.
LIBELLES_EN: dict[str, str] = {
    "taux_actualisation": "Discount rate",
    "croissance_salaires": "Salary growth",
    "inflation": "Inflation",
    "age_retraite": "Retirement age",
    "taux_turnover": "Staff turnover",
    "rotation_par_age": "Staff turnover by age band",
    "frais_sur_cotisation": "Charges on contributions",
    "table": "Mortality table",
}

SENSIBILITES_EN = {
    "taux_actualisation_moins_1pt": "Discount rate − 1 point",
    "taux_actualisation_plus_1pt": "Discount rate + 1 point",
    "croissance_salaires_moins_1pt": "Salary growth − 1 point",
    "croissance_salaires_plus_1pt": "Salary growth + 1 point",
    "rotation_moins_1pt": "Staff turnover − 1 point",
    "rotation_plus_1pt": "Staff turnover + 1 point",
}

EXPLICATIONS_EN: dict[str, dict[str, str]] = {
    "taux_actualisation": {
        "role": "A benefit paid in 20 years does not cost its full amount today: money set aside in the meantime "
                "earns a return. The discount rate brings each future payment back to its value today.",
        "effet": "The lower it is, the heavier the liability{effet}. It is the assumption that weighs most on the "
                 "result.",
        "fixer": "Use the yield on safe investments with a term close to that of your obligations (the average time "
                 "until retirements). A prudent rate protects the company from a bad surprise. A rate set too high "
                 "flatters the figure without changing anything that will actually be paid.",
        "avec": "Salary growth. What matters is the gap between the two: a 3.5% rate with salaries at +2% weighs the "
                "same as a 5% rate with salaries at +3.5%.",
    },
    "croissance_salaires": {
        "role": "The benefit is calculated on the final salary. This rate projects today's salary up to retirement.",
        "effet": "The higher it is, the heavier the liability{effet}.",
        "fixer": "Based on pay rises over recent years (general, seniority, promotion) and the announced pay policy. "
                 "An exceptional rise is not carried forward over thirty years.",
        "avec": "The discount rate: what matters is the gap between the two.",
    },
    "inflation": {
        "role": "It is added to salary growth when salary growth is expressed excluding inflation.",
        "effet": "It acts like extra points of salary growth: the higher it is, the heavier the liability.",
        "fixer": "Zero when the salary growth used already includes inflation (the default). Otherwise, the "
                 "inflation target for the zone.",
        "avec": "Salary growth: do not count inflation twice.",
    },
    "age_retraite": {
        "role": "The age at which the benefit is paid: it sets the service accrued at departure and the time "
                "remaining until then.",
        "effet": "A later departure lengthens service (the benefit grows) but pushes the payment further away (its "
                 "value today falls); which way it goes depends on the age profile of the workforce.",
        "fixer": "The statutory age in the country, or the age set by your collective agreement or your plan if "
                 "different.",
        "avec": "The mortality table and staff turnover: the further away the departure, the more they count.",
    },
    "taux_turnover": {
        "role": "The share of employees who leave the company each year before retirement (resignation, "
                "dismissal): they will not receive the retirement benefit.",
        "effet": "The higher it is, the lighter the liability: many of today's employees will no longer be there "
                 "at retirement{effet}.",
        "fixer": "Based on resignations and dismissals over the last three to five years, relative to headcount. "
                 "The study's actual experience compares it with what is assumed.",
        "avec": "By age band if young employees leave much more often than long-serving ones: a single rate then "
                "understates the liability for senior staff.",
    },
    "rotation_par_age": {
        "role": "Staff turnover, age band by age band: each band runs from its starting age to the next one, the "
                "last up to retirement.",
        "effet": "High turnover among the young and low turnover among senior staff reduces the liability less "
                 "than a uniform rate: it is senior staff, close to retirement, who weigh.",
        "fixer": "Based on departures observed by age; three bands are usually enough (under 30, 30 to 45, over "
                 "45).",
        "avec": "The study's actual experience, which compares observed turnover with the turnover assumed.",
    },
    "frais_sur_cotisation": {
        "role": "The charges the insurer deducts from each contribution paid into the fund.",
        "effet": "No effect on the liability: they are added to the contribution to be paid (total contribution = "
                 "net contribution × (1 + charges)).",
        "fixer": "Based on the current contract, or on the terms requested from insurers.",
        "avec": "The tender specifications, which ask insurers for a cap on charges.",
    },
    "table": {
        "role": "The probability of still being alive at retirement age: a benefit is only paid to a living "
                "employee.",
        "effet": "A table more favourable to survival makes the liability slightly heavier; the effect remains "
                 "small before retirement.",
        "fixer": "The CIMA regulatory table. The female table (TF), the more prudent one, applies to everyone by "
                 "default.",
        "avec": "The retirement age.",
    },
}

TABLES_EN = {"TV_CIMA_F": "CIMA F mortality table (women)", "TV_CIMA_H": "CIMA H mortality table (men)"}


def _en() -> bool:
    return langue() == "en"


def libelle(champ: str) -> str:
    """Le libellé d'une hypothèse dans la langue de l'écran."""
    fr = BORNES[champ][0]
    return LIBELLES_EN.get(champ, fr) if _en() else fr


def explications(champ: str) -> dict[str, str]:
    """Le rôle, l'effet et la façon de fixer une hypothèse, dans la langue de l'écran."""
    return EXPLICATIONS_EN[champ] if _en() else EXPLICATIONS[champ]


def sensibilites() -> dict[str, str]:
    """Les libellés des sensibilités dans la langue de l'écran (`SENSIBILITES` reste le texte scellé)."""
    return SENSIBILITES_EN if _en() else SENSIBILITES


def tables() -> list[dict]:
    """Les tables de mortalité du référentiel ; la table masculine s'ajoutera quand sa source sera versée."""
    connues = referentiel_courant().tables
    liste = [{"code": t.code, "libelle": t.libelle, "disponible": True} for t in connues.values()]
    if not any("_H" in code for code in connues):
        liste.append({"code": "TV_CIMA_H", "libelle": "Table de mortalité CIMA H (hommes)", "disponible": False,
                      "raison": "À venir : la table sera ajoutée au référentiel avec sa source."})
    return liste


def _tables_a_l_ecran() -> list[dict]:
    if not _en():
        return tables()
    liste = []
    for table in tables():
        table = {**table, "libelle": TABLES_EN.get(table["code"], table["libelle"])}
        if "raison" in table:
            table["raison"] = "Coming soon: the table will be added to the reference data with its source."
        liste.append(table)
    return liste


def catalogue() -> dict:
    """Ce que le formulaire affiche : défauts, bornes, explications et tables."""
    return {
        "defauts": {**HYPOTHESES_PAR_DEFAUT, "rotation_par_age": None},
        "champs": [{"champ": c, "libelle": libelle(c), "nature": n, "min": mn, "max": mx, **explications(c)}
                   for c, (_l, n, mn, mx) in BORNES.items()],
        "tables": _tables_a_l_ecran(),
        "age_premier_emploi": AGE_PREMIER_EMPLOI,
    }


def lire(champ: str, valeur, age_retraite: int | None = None):
    """La valeur saisie, contrôlée ; une erreur métier sinon."""
    if champ not in BORNES:
        raise ErreurMetier("hypothese_inconnue", t(f"Hypothèse inconnue : {champ}.",
                                                        f"Unknown assumption: {champ}."), 422)
    _libelle, nature, mn, mx = BORNES[champ]
    nom = libelle(champ)
    try:
        if nature == "table":
            if valeur not in referentiel_courant().tables:
                raise ErreurMetier("table_indisponible", t(f"La table {valeur} n'est pas au référentiel.",
                                                           f"Table {valeur} is not in the reference data."), 422)
            return str(valeur)
        if nature == "tranches":
            return _tranches(valeur, mn, mx, age_retraite)
        v = int(valeur) if nature == "age" else float(valeur)
        if nature == "age" and v != float(valeur):
            raise ValueError
    except (TypeError, ValueError):
        raise ErreurMetier("hypothese_invalide", t(f"{nom} : valeur illisible.", f"{nom}: unreadable value."), 422,
                          {"champ": champ}) from None
    if not (mn <= v <= mx):
        borne = (lambda x: t(f"{x:g} ans", f"{x:g} years")) if nature == "age" else \
            (lambda x: t(f"{x * 100:g} %", f"{x * 100:g}%"))
        raise ErreurMetier("hypothese_hors_bornes", t(f"{nom} : entre {borne(mn)} et {borne(mx)}.",
                                                      f"{nom}: between {borne(mn)} and {borne(mx)}."), 422,
                           {"champ": champ})
    return v


def _tranches(valeur, mn: float, mx: float, age_retraite: int | None) -> list[dict] | None:
    if valeur in (None, []):
        return None
    if not isinstance(valeur, list) or len(valeur) > MAX_TRANCHES:
        raise ErreurMetier("rotation_invalide", t(f"La rotation par âge tient en 1 à {MAX_TRANCHES} tranches.",
                                                            f"Turnover by age takes 1 to {MAX_TRANCHES} bands."), 422)
    tranches = []
    for tr in valeur:
        if not isinstance(tr, dict) or set(tr) != {"des", "taux"}:
            raise ErreurMetier("rotation_invalide", t("Chaque tranche donne son âge de début et son taux.",
                                                            "Each band gives its starting age and its rate."), 422)
        des, taux = int(tr["des"]), float(tr["taux"])
        if not (mn <= taux <= mx):
            raise ErreurMetier("rotation_invalide", t(f"Le taux d'une tranche va de 0 à {mx * 100:g} %.",
                                                                f"A band's rate ranges from 0 to {mx * 100:g}%."), 422)
        tranches.append({"des": des, "taux": taux})
    ages = [tr["des"] for tr in tranches]
    if ages[0] != AGE_PREMIER_EMPLOI or ages != sorted(set(ages)):
        raise ErreurMetier("rotation_invalide", t(f"Les tranches commencent à {AGE_PREMIER_EMPLOI} ans, dans l'ordre "
                                                  "des âges, sans doublon.",
                                                  f"Bands start at age {AGE_PREMIER_EMPLOI}, in order of age, with no "
                                                  "duplicates."), 422)
    if age_retraite is not None and ages[-1] >= age_retraite:
        raise ErreurMetier("rotation_invalide", t("Une tranche commence après l'âge de la retraite.",
                                                            "A band starts after the retirement age."), 422)
    return tranches


def valeurs_et_ecarts(saisies: dict) -> tuple[dict, list[dict]]:
    """Les hypothèses retenues (le référentiel, complété par la saisie) et leurs écarts au référentiel."""
    defauts = {**HYPOTHESES_PAR_DEFAUT, "rotation_par_age": None}
    for champ in saisies:
        if champ not in BORNES:
            raise ErreurMetier("hypothese_inconnue", t(f"Hypothèse inconnue : {champ}.",
                                                        f"Unknown assumption: {champ}."), 422)
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


def pct(v: float, anglais: bool = False) -> str:
    if anglais:
        return f"{v * 100:.2f}".rstrip("0").rstrip(".") + "%"
    return f"{v * 100:.2f}".rstrip("0").rstrip(".").replace(".", ",") + " %"


def en_texte(champ: str, valeur, anglais: bool = False) -> str:
    """Une hypothèse telle qu'un lecteur la lit : « 3,5 % », « 60 ans », « 18 ans : 6 % ; 30 ans : 3 % ».

    En français par défaut : le classeur et le rapport, scellés, l'écrivent ainsi. `anglais` sert l'écran seul."""
    if valeur is None:
        if champ == "rotation_par_age":
            return "uniform" if anglais else "uniforme"
        return "—"
    nature = BORNES.get(champ, ("", "texte"))[1]
    if nature == "taux":
        return pct(valeur, anglais)
    if nature == "age":
        return f"{valeur} years" if anglais else f"{valeur} ans"
    if nature == "tranches":
        if anglais:
            return "; ".join(f"from age {tr['des']}: {pct(tr['taux'], True)}" for tr in valeur)
        return " ; ".join(f"dès {tr['des']} ans : {pct(tr['taux'])}" for tr in valeur)
    if nature == "table":
        if anglais and valeur in TABLES_EN:
            return TABLES_EN[valeur]
        return next((tb["libelle"] for tb in tables() if tb["code"] == valeur), str(valeur))
    return str(valeur)


def rotation_en_texte(valeurs: dict, anglais: bool = False) -> str:
    if valeurs.get("rotation_par_age"):
        debut = "by age band — " if anglais else "par tranche d'âge — "
        return debut + en_texte("rotation_par_age", valeurs["rotation_par_age"], anglais)
    if anglais:
        return f"{pct(valeurs['taux_turnover'], True)} a year, at every age"
    return f"{pct(valeurs['taux_turnover'])} par an, à tout âge"


def ecarts_en_texte(ecarts: list[dict]) -> list[dict]:
    return [{"libelle": BORNES.get(e["champ"], (e["champ"],))[0], "referentiel": en_texte(e["champ"], e["referentiel"]),
             "retenu": en_texte(e["champ"], e["retenu"])} for e in ecarts]


def pour_le_lecteur(valeurs: dict, ecarts: list[dict], sensibilites: dict | None, dette: float | None,
                    ecran: bool = False) -> list[dict]:
    """Chaque hypothèse de l'étude, pour le rapport : défaut, retenue, rôle, effet mesuré, comment la fixer.

    En français par défaut, parce que la fiche du régime et le rapport, scellés, s'en servent. `ecran=True` (la
    lecture d'une étude à l'écran seulement) suit la langue de la requête."""
    anglais = ecran and _en()
    textes = EXPLICATIONS_EN if anglais else EXPLICATIONS
    ecartes = {e["champ"] for e in ecarts}
    effets = _effets(sensibilites or {}, dette, anglais)
    lignes = []
    for champ in ("taux_actualisation", "croissance_salaires", "inflation", "age_retraite", "taux_turnover",
                  "frais_sur_cotisation", "table"):
        if champ not in valeurs:
            continue
        defaut = HYPOTHESES_PAR_DEFAUT.get(champ)
        retenu = valeurs[champ]
        if champ == "taux_turnover":
            retenu_txt = rotation_en_texte(valeurs, anglais)
            ecarte = bool(ecartes & {"taux_turnover", "rotation_par_age"})
            expl = textes["rotation_par_age" if valeurs.get("rotation_par_age") else champ]
        else:
            retenu_txt, ecarte, expl = en_texte(champ, retenu, anglais), champ in ecartes, textes[champ]
        lignes.append({
            "champ": champ, "libelle": LIBELLES_EN[champ] if anglais else BORNES[champ][0],
            "defaut": en_texte(champ, defaut, anglais), "retenu": retenu_txt,
            "ecarte": ecarte, "role": expl["role"],
            "effet": expl["effet"].replace("{effet}", effets.get(champ, "")),
            "fixer": expl["fixer"],
        })
    return lignes


def _effets(sensibilites: dict, dette: float | None, anglais: bool = False) -> dict[str, str]:
    if not dette:
        return {}

    def part(cle: str) -> float | None:
        s = sensibilites.get(cle)
        return None if s is None else (s["dette"] - dette) / dette

    effets = {}
    if anglais:
        if (x := part("taux_actualisation_moins_1pt")) is not None:
            effets["taux_actualisation"] = f": on this study, 1 point less raises the liability by {pct(abs(x), True)}"
        if (x := part("croissance_salaires_plus_1pt")) is not None:
            effets["croissance_salaires"] = f": on this study, 1 point more raises the liability by {pct(abs(x), True)}"
        if (x := part("rotation_plus_1pt")) is not None:
            effets["taux_turnover"] = f"; on this study, 1 point more reduces the liability by {pct(abs(x), True)}"
        return effets
    if (x := part("taux_actualisation_moins_1pt")) is not None:
        effets["taux_actualisation"] = f" : sur cette étude, 1 point de moins augmente la dette de {pct(abs(x))}"
    if (x := part("croissance_salaires_plus_1pt")) is not None:
        effets["croissance_salaires"] = f" : sur cette étude, 1 point de plus augmente la dette de {pct(abs(x))}"
    if (x := part("rotation_plus_1pt")) is not None:
        effets["taux_turnover"] = f" ; sur cette étude, 1 point de plus réduit la dette de {pct(abs(x))}"
    return effets
