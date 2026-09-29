"""Financement d'un engagement IFC : ce que l'entreprise versera, et ce que chaque offre en fera.

Module pur. Il ne fixe pas la prime d'un assureur : il projette, année par
année, un fonds alimenté par les cotisations de l'entreprise et vidé par les
prestations, sous les conditions de chaque offre et sous plusieurs scénarios
de rendement, et il en tire un critère de comparaison.

Une année, dans l'ordre :
1. l'entreprise cotise : la charge annuelle (indexée sur les salaires) et une
   annuité d'amortissement du déficit initial (dette − fonds) sur N années ;
2. l'assureur prélève ses frais sur cotisations ;
3. le fonds est crédité au taux garanti, plus la participation aux bénéfices
   sur le rendement au-delà du garanti ;
4. l'assureur prélève ses frais sur encours ;
5. les prestations probables de l'année sont payées PAR LE FONDS, DANS LA
   LIMITE DE CE QU'IL CONTIENT (clause du contrat Ariane) ; le reste est un
   découvert que l'entreprise paie elle-même.

Le coût net actualisé additionne cotisations et découverts, actualisés, et
retranche le fonds restant à l'horizon : il appartient à l'entreprise et
financera les départs d'après. Il peut donc être négatif quand le fonds
rapporte plus que le taux d'actualisation ; il sert à COMPARER des offres, qui
reçoivent les mêmes cotisations et paient les mêmes prestations. Pour juger
si le fonds suffit, la couverture rapporte le fonds à l'horizon à la valeur,
à cette date, des prestations probables qui restent à payer.

Le rendement net est ce que l'offre rapporte VRAIMENT au fonds, tous frais
payés : le taux r qui égalise ce qui y entre (le fonds initial, les
cotisations brutes, en début d'année) et ce qui en sort ou y reste (les
prestations payées en fin d'année, le fonds à l'horizon). C'est le taux servi
(garanti + participation) moins les frais sur encours moins l'effet des frais
sur cotisations — calculé exactement plutôt qu'approché. Il classe les offres
du courtier : la plus intéressante est celle qui rapporte le plus.
"""
from dataclasses import dataclass

ANNEES_MAX = 40


def _borne(nom: str, valeur: float, bas: float, haut: float) -> None:
    if not bas <= valeur <= haut:
        raise ValueError(f"{nom} doit être entre {bas} et {haut}")


@dataclass(frozen=True)
class Engagement:
    annee_evaluation: int
    dette: float                        # dette actuarielle à la date d'évaluation
    charge: float                       # charge annuelle (coût des services de l'année)
    fonds_initial: float
    prestations: dict[int, float]       # prestations probables par année de versement


@dataclass(frozen=True)
class Offre:
    nom: str
    taux_garanti: float = 0.0
    participation_benefices: float = 0.0     # part du rendement au-delà du garanti rendue au fonds
    frais_sur_cotisations: float = 0.0
    frais_sur_encours: float = 0.0           # par an, sur le fonds
    interne: bool = False                    # la provision interne, offre de référence

    def __post_init__(self):
        _borne("taux_garanti", self.taux_garanti, -0.05, 0.2)
        _borne("participation_benefices", self.participation_benefices, 0, 1)
        _borne("frais_sur_cotisations", self.frais_sur_cotisations, 0, 0.2)
        _borne("frais_sur_encours", self.frais_sur_encours, 0, 0.2)


@dataclass(frozen=True)
class Scenario:
    nom: str
    rendement: float                         # le rendement des actifs de l'assureur

    def __post_init__(self):
        _borne("rendement", self.rendement, -0.1, 0.3)


@dataclass(frozen=True)
class Parametres:
    horizon: int = 10
    amortissement_annees: int = 1
    taux_actualisation: float = 0.035
    croissance_salaires: float = 0.02
    scenario_de_reference: str = "central"

    def __post_init__(self):
        if not 1 <= self.horizon <= ANNEES_MAX:
            raise ValueError(f"horizon entre 1 et {ANNEES_MAX} ans")
        if not 1 <= self.amortissement_annees <= self.horizon:
            raise ValueError("amortissement entre 1 an et l'horizon")
        _borne("taux_actualisation", self.taux_actualisation, -0.05, 0.2)
        _borne("croissance_salaires", self.croissance_salaires, -0.05, 0.2)


SCENARIOS_PAR_DEFAUT = (Scenario("prudent", 0.035), Scenario("central", 0.05), Scenario("favorable", 0.065))


def projeter(engagement: Engagement, offres: list[Offre], scenarios: list[Scenario] | tuple = SCENARIOS_PAR_DEFAUT,
             parametres: Parametres = Parametres()) -> dict:
    deficit = max(engagement.dette - engagement.fonds_initial, 0.0)
    annuite = deficit / parametres.amortissement_annees
    reference = next((s.nom for s in scenarios if s.nom == parametres.scenario_de_reference), scenarios[0].nom)
    resultats = [{
        "nom": o.nom, "interne": o.interne, "conditions": _conditions(o),
        "scenarios": [_projeter_une(engagement, o, s, parametres, annuite) for s in scenarios],
    } for o in offres]

    def cout_de_reference(o):
        return next(s["cout_net_actualise"] for s in o["scenarios"] if s["scenario"] == reference)
    def rendement_de_reference(o):
        r = next(s["rendement_net"] for s in o["scenarios"] if s["scenario"] == reference)
        return -r if r is not None else float("inf")
    return {
        "plan_amortissement": {"deficit_initial": deficit, "annees": parametres.amortissement_annees,
                               "annuite": annuite},
        "scenario_de_reference": reference,
        "offres": resultats,
        "classement": [o["nom"] for o in sorted(resultats, key=cout_de_reference)],
        # Par rendement net décroissant (à égalité, le coût départage) : le classement des offres du courtier.
        "classement_rendement": [o["nom"] for o in sorted(resultats, key=lambda o: (rendement_de_reference(o),
                                                                                     cout_de_reference(o)))],
    }


def rendement_net(fonds_initial: float, annees: list[dict], fonds_final: float) -> float | None:
    """Le taux r tel que fonds_initial·(1+r)^H + Σ cotisation_t·(1+r)^(H−t+1) − Σ payées_t·(1+r)^(H−t) = fonds_final.
    `None` quand rien n'est placé (pas de fonds, pas de cotisation) ou que le taux sort de [−50 %, +100 %]."""
    h = len(annees)
    if h == 0 or (fonds_initial <= 0 and not any(a["cotisation"] > 0 for a in annees)):
        return None

    def ecart(r: float) -> float:
        v = fonds_initial * (1 + r) ** h
        for t, a in enumerate(annees, start=1):
            v += a["cotisation"] * (1 + r) ** (h - t + 1) - a["payees_par_le_fonds"] * (1 + r) ** (h - t)
        return v - fonds_final

    bas, haut = -0.5, 1.0
    if ecart(bas) > 0 or ecart(haut) < 0:
        return None
    for _ in range(200):
        milieu = (bas + haut) / 2
        if ecart(milieu) > 0:
            haut = milieu
        else:
            bas = milieu
        if haut - bas < 1e-12:
            break
    return round((bas + haut) / 2, 8)      # sans frais, il tombe exactement sur le taux servi, comme à l'affichage


def _projeter_une(e: Engagement, o: Offre, s: Scenario, p: Parametres, annuite: float) -> dict:
    taux = o.taux_garanti + o.participation_benefices * max(s.rendement - o.taux_garanti, 0.0)
    fonds = e.fonds_initial
    annees, cout_total, cout_actualise, frais_totaux, decouverts = [], 0.0, 0.0, 0.0, []
    for t in range(1, p.horizon + 1):
        annee = e.annee_evaluation + t
        charge = e.charge * (1 + p.croissance_salaires) ** (t - 1)
        amortissement = annuite if t <= p.amortissement_annees else 0.0
        cotisation = charge + amortissement
        frais_cotisation = cotisation * o.frais_sur_cotisations
        debut = fonds
        fonds += cotisation - frais_cotisation
        interets = fonds * taux
        fonds += interets
        frais_encours = fonds * o.frais_sur_encours
        fonds -= frais_encours
        prestations = sum(v for a, v in e.prestations.items() if (a <= annee if t == 1 else a == annee))
        payees = min(prestations, max(fonds, 0.0))
        fonds -= payees
        decouvert = prestations - payees
        if decouvert > 1e-9:
            decouverts.append(annee)
        cout = cotisation + decouvert
        cout_total += cout
        cout_actualise += cout / (1 + p.taux_actualisation) ** t
        frais_totaux += frais_cotisation + frais_encours
        annees.append({
            "annee": annee, "fonds_debut": debut, "charge": charge, "amortissement": amortissement,
            "cotisation": cotisation, "frais_cotisation": frais_cotisation, "taux_credite": taux,
            "interets": interets, "frais_encours": frais_encours, "prestations": prestations,
            "payees_par_le_fonds": payees, "decouvert": decouvert, "fonds_fin": fonds,
        })
    derniere = e.annee_evaluation + p.horizon
    restant = sum(v / (1 + p.taux_actualisation) ** (a - derniere) for a, v in e.prestations.items() if a > derniere)
    return {
        "scenario": s.nom, "rendement": s.rendement, "annees": annees,
        "prestations_restantes_actualisees": restant,
        "couverture_des_departs_restants": (fonds / restant) if restant > 0 else None,
        "cout_total": cout_total, "frais_totaux": frais_totaux, "annees_decouvert": decouverts,
        "fonds_final": fonds,
        "cout_net_actualise": cout_actualise - fonds / (1 + p.taux_actualisation) ** p.horizon,
        "taux_servi": taux,
        "rendement_net": rendement_net(e.fonds_initial, annees, fonds),
    }


def _conditions(o: Offre) -> dict:
    return {"taux_garanti": o.taux_garanti, "participation_benefices": o.participation_benefices,
            "frais_sur_cotisations": o.frais_sur_cotisations, "frais_sur_encours": o.frais_sur_encours}

