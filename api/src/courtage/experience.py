"""L'expérience réelle : ce que les départs enregistrés disent des hypothèses (spec prestations §4, P5).

Module pur. Trois lectures, et une règle :
- l'ATTENDU contre le RÉEL, année par année : les retraites que l'étude
  précédente prévoyait (son échéancier) contre celles qui ont eu lieu ;
- la ROTATION OBSERVÉE : démissions et licenciements par an, rapportés à
  l'effectif — une PROPOSITION d'hypothèse, jamais appliquée d'office. Un
  décès relève de la mortalité, pas de la rotation ;
- l'HISTORIQUE PUBLIABLE, pour les assureurs : par années regroupées, chaque
  groupe d'au moins SEUIL retraites, faute de quoi le montant d'un départ
  dirait le salaire d'une personne.
La règle : peu de départs ne prouvent rien. Sous CREDIBILITE départs, la
rotation observée est montrée et n'est pas proposée.
"""
from dataclasses import dataclass
from datetime import date
from statistics import median

from courtage.fiche import SEUIL

CREDIBILITE = 5
ECART_SIGNIFICATIF = 0.005      # un demi-point de rotation
FENETRE = 5                     # années observées au plus
MOTIFS_DE_ROTATION = ("demission", "licenciement")


@dataclass(frozen=True)
class Depart:
    matricule: str
    date_depart: date
    motif: str
    du: int
    verse: int | None = None
    paye: int | None = None
    payee_le: date | None = None


def fenetre(date_evaluation: date) -> range:
    return range(date_evaluation.year - FENETRE + 1, date_evaluation.year + 1)


def attendu_contre_reel(departs: list[Depart], echeancier_precedent: list[dict] | None, date_evaluation: date,
                        annee_precedente: int | None) -> list[dict]:
    """Par année observée : les retraites prévues (étude précédente) et celles qui ont eu lieu."""
    prevu = {a["annee"]: a for a in (echeancier_precedent or [])}
    lignes = []
    for annee in fenetre(date_evaluation):
        reels = [d for d in departs if d.motif == "retraite" and d.date_depart.year == annee
                 and d.date_depart <= date_evaluation]
        couvert = annee_precedente is not None and annee > annee_precedente and annee in prevu
        if not reels and not couvert:
            continue
        lignes.append({
            "annee": annee,
            "attendu_retraites": prevu[annee]["effectif"] if couvert else None,
            "attendu_prestations": prevu[annee]["prestations_probables"] if couvert else None,
            "reel_retraites": len(reels), "reel_du": sum(d.du for d in reels),
            "reel_verse": sum(d.verse or 0 for d in reels),
        })
    return lignes


def rotation_observee(departs: list[Depart], effectif: int, date_evaluation: date, taux_hypothese: float) -> dict:
    observes = [d for d in departs if d.date_depart <= date_evaluation and d.date_depart.year in fenetre(date_evaluation)]
    if not observes or effectif <= 0:
        return {"taux": None, "departs": 0, "annees": 0, "effectif": effectif, "taux_hypothese": taux_hypothese,
                "credible": False, "proposition": None,
                "message": "Aucun départ enregistré sur la période : la rotation reste une hypothèse."}
    debut = min(d.date_depart.year for d in observes)
    annees = date_evaluation.year - debut + 1
    n = sum(d.motif in MOTIFS_DE_ROTATION for d in observes)
    taux = n / (annees * effectif)
    credible = n >= CREDIBILITE
    proposition = None
    if credible and abs(taux - taux_hypothese) >= ECART_SIGNIFICATIF:
        proposition = {
            "taux_turnover": round(taux, 3),
            "justification": f"Rotation observée : {n} démissions et licenciements de {debut} à {date_evaluation.year}, "
                             f"pour un effectif de {effectif}, soit {_pct(taux)} par an (hypothèse : {_pct(taux_hypothese)}).",
        }
    if not credible:
        message = f"{n} départ(s) hors retraite en {annees} an(s) : trop peu pour conclure ({CREDIBILITE} au moins)."
    elif proposition:
        message = f"Rotation observée {_pct(taux)} par an, contre {_pct(taux_hypothese)} supposés : à discuter."
    else:
        message = f"Rotation observée {_pct(taux)} par an : l'hypothèse de {_pct(taux_hypothese)} tient."
    return {"taux": round(taux, 4), "departs": n, "annees": annees, "effectif": effectif,
            "taux_hypothese": taux_hypothese, "credible": credible, "proposition": proposition, "message": message}


def paiements_du_fonds(departs: list[Depart], depuis: date | None, jusqu_a: date) -> int:
    return sum(d.paye or 0 for d in departs
               if d.paye and d.payee_le and d.payee_le <= jusqu_a and (depuis is None or d.payee_le > depuis))


def historique_publiable(departs: list[Depart], jusqu_a: date) -> list[dict]:
    """Les retraites par années regroupées, chaque groupe d'au moins SEUIL ; en dessous en tout, rien de chiffré."""
    retraites = sorted((d for d in departs if d.motif == "retraite" and d.date_depart <= jusqu_a),
                       key=lambda d: d.date_depart)
    if len(retraites) < SEUIL:
        return [{"periode": "—", "retraites": f"<{SEUIL}", "du": None, "paye": None}] if retraites else []
    par_annee: dict[int, list[Depart]] = {}
    for d in retraites:
        par_annee.setdefault(d.date_depart.year, []).append(d)
    groupes, en_cours = [], []
    for annee in sorted(par_annee):
        en_cours.append(annee)
        if sum(len(par_annee[a]) for a in en_cours) >= SEUIL:
            groupes.append(en_cours)
            en_cours = []
    if en_cours:
        groupes[-1] = groupes[-1] + en_cours
    sortie = []
    for g in groupes:
        ds = [d for a in g for d in par_annee[a]]
        sortie.append({"periode": str(g[0]) if len(g) == 1 else f"{g[0]}-{g[-1]}", "retraites": len(ds),
                       "du": sum(d.du for d in ds), "paye": sum(d.paye or 0 for d in ds)})
    return sortie


def delais_constates(delais_jours: list[int]) -> dict | None:
    """Les délais de paiement suivis (envoi → paiement) ; moins de SEUIL dossiers ne font pas une statistique."""
    if len(delais_jours) < SEUIL:
        return None
    return {"dossiers": len(delais_jours), "median": round(median(delais_jours)), "max": max(delais_jours)}


def _pct(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + " %"
