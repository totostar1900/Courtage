"""Financer une étude : son engagement, projeté sous les offres et les scénarios demandés."""
from courtage.db import Etude
from courtage.erreurs import ErreurMetier
from courtage.financement import SCENARIOS_PAR_DEFAUT, Engagement, Offre, Parametres, Scenario, projeter

PROVISION_INTERNE = Offre(nom="Provision interne", taux_garanti=0.0, interne=True)


def financer(etude: Etude, *, offres: list[Offre], scenarios: list[Scenario] | None, horizon: int,
             amortissement_annees: int, taux_actualisation: float | None, croissance_salaires: float | None) -> dict:
    echeancier = etude.resultats["echeancier"]
    if any("prestations_probables" not in a for a in echeancier):
        raise ErreurMetier("etude_a_recalculer",
                           "Cette étude précède le calcul des prestations probables : la recalculer.", 422)
    valeurs = etude.hypotheses["valeurs"]
    try:
        parametres = Parametres(
            horizon=horizon, amortissement_annees=amortissement_annees,
            taux_actualisation=valeurs["taux_actualisation"] if taux_actualisation is None else taux_actualisation,
            croissance_salaires=valeurs["croissance_salaires"] if croissance_salaires is None else croissance_salaires)
    except ValueError as e:
        raise ErreurMetier("parametres_invalides", str(e), 422) from None
    engagement = Engagement(
        annee_evaluation=etude.date_evaluation.year, dette=float(etude.resultats["totaux"]["dette"]),
        charge=float(etude.resultats["totaux"]["charge"]), fonds_initial=float(etude.fonds_disponible),
        prestations={a["annee"]: float(a["prestations_probables"]) for a in echeancier})
    if not any(o.interne for o in offres):
        offres = [*offres, PROVISION_INTERNE]     # toujours la référence : garder l'argent chez soi
    resultat = projeter(engagement, offres, scenarios or list(SCENARIOS_PAR_DEFAUT), parametres)
    return {"etude_id": str(etude.id), "date_evaluation": etude.date_evaluation.isoformat(),
            "parametres": parametres.__dict__, **_arrondi(resultat)}


def _arrondi(x):
    """Les montants en francs entiers ; les taux restent des taux."""
    if isinstance(x, dict):
        return {k: (v if k in _TAUX else _arrondi(v)) for k, v in x.items()}
    if isinstance(x, list):
        return [_arrondi(v) for v in x]
    if isinstance(x, float):
        return round(x)
    return x


_TAUX = {"couverture_des_departs_restants", "taux_credite", "rendement", "taux_garanti", "participation_benefices", "frais_sur_cotisations",
         "frais_sur_encours"}
