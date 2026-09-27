"""Ce que le rapport d'étude explique, au-delà des tableaux : la synthèse et la décision, la population, ce que le
régime verse face à la convention, et quand l'argent sort face au fonds constitué.

Rien n'est recalculé ici : tout se lit dans l'étude scellée (ses totaux, ses lignes, son échéancier, ses
sensibilités). Seules les courbes de prestation relisent les barèmes, qui ne dépendent d'aucune hypothèse.
"""
from datetime import date

from sqlalchemy.orm import Session

from courtage.actuariat.ifc import Regles, mois_d_ifc, mois_dus

from . import baremes, graphiques, regimes
from .hypotheses import pct

HORIZON = 30                   # années affichées sur les graphiques de l'échéancier
ANCIENNETE_MAX = 40            # années sur la courbe de prestation
MAX_CATEGORIES = 3             # au-delà, la courbe devient illisible : les plus grandes catégories seulement
PROCHES = 5                    # « les cinq prochaines années »


def _montant(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " F"


# --- Population ---------------------------------------------------------------

def pyramide(lignes: list[dict]) -> dict:
    """Les effectifs par tranche de cinq ans d'âge et d'ancienneté."""
    def tranches(valeurs: list[float], debut: int, fin: int, premiere: str, derniere: str) -> list[tuple[str, int]]:
        bornes = list(range(debut, fin + 1, 5))
        groupes = [(premiere, sum(1 for v in valeurs if v < debut))]
        groupes += [(f"{b}-{b + 4} ans", sum(1 for v in valeurs if b <= v < b + 5)) for b in bornes[:-1]]
        groupes.append((derniere, sum(1 for v in valeurs if v >= fin)))
        # Les tranches vides aux deux bouts n'apprennent rien.
        while groupes and groupes[0][1] == 0:
            groupes.pop(0)
        while groupes and groupes[-1][1] == 0:
            groupes.pop()
        return groupes

    ages = tranches([l["age"] for l in lignes], 25, 60, "moins de 25 ans", "60 ans et plus")
    anciennetes = tranches([l["anciennete"] for l in lignes], 5, 30, "moins de 5 ans", "30 ans et plus")
    return {"ages": ages, "anciennetes": anciennetes,
            "svg_ages": graphiques.histogramme("Âges", ages),
            "svg_anciennetes": graphiques.histogramme("Anciennetés", anciennetes)}


# --- Ce que le régime verse ---------------------------------------------------

def courbes_de_prestation(session: Session, etude, e: dict, convention) -> dict:
    """Les mois de salaire versés au départ, ancienneté par ancienneté : le régime (par catégorie) et la convention."""
    anciennetes = range(0, ANCIENNETE_MAX + 1)
    conv = [(n, round(mois_d_ifc(convention.bareme, n), 3)) for n in anciennetes]
    series: list[tuple[str, list[tuple[int, float]]]] = []
    if etude.regime_version_id:
        regles = regimes.regles(session, regimes.obtenir_version(session, etude.regime_version_id),
                                etude.date_evaluation)
        poids = e.get("par_categorie") or {}
        cats = sorted(regles, key=lambda c: -(poids.get(c, {}).get("effectif", 0)))[:MAX_CATEGORIES]
        seule = len(regles) == 1
        for c in cats:
            nom = "Régime" if seule else ("Régime, autres salariés" if c == "*" else f"Régime, {c}")
            series.append((nom, [(n, round(mois_dus(regles[c], n)[0], 3)) for n in anciennetes]))
    elif e.get("bareme_entreprise"):
        b = Regles(bareme=baremes._BAREME.validate_python(e["bareme_entreprise"]["bareme"]))
        series.append(("Accord d'entreprise", [(n, round(mois_dus(b, n)[0], 3)) for n in anciennetes]))
    series.append(("Convention", conv))
    confondues = [nom for nom, pts in series[:-1] if all(abs(y - conv[i][1]) < 1e-9 for i, (_, y) in enumerate(pts))]
    au_dessus = [n for n in anciennetes if any(pts[n][1] > conv[n][1] + 1e-9 for _, pts in series[:-1])]
    return {
        "series": series, "comparaison": len(series) > 1, "confondues": confondues,
        "au_dessus_des": au_dessus[0] if au_dessus else None,
        "a_20_ans": [(nom, pts[20][1]) for nom, pts in series],
        "svg": graphiques.courbes("Mois de salaire versés au départ, selon l'ancienneté", series, reference="Convention"),
    }


# --- Quand l'argent sort ------------------------------------------------------

def couverture(echeancier: list[dict], fonds: int, annee_evaluation: int) -> dict:
    """Les prestations probables année par année, et jusqu'où le fonds constitué les couvre."""
    par_annee = {a["annee"]: a.get("prestations_probables", a["ifc"]) for a in echeancier}
    departs = {a["annee"]: a["effectif"] for a in echeancier}
    annees = [(a, par_annee.get(a, 0)) for a in range(annee_evaluation, annee_evaluation + HORIZON)]
    total = sum(par_annee.values()) or 1
    cumul, epuisement = 0.0, None
    for a, v in sorted(par_annee.items()):
        cumul += v
        if fonds and epuisement is None and cumul > fonds:
            epuisement = a
    proches = [a for a in par_annee if a < annee_evaluation + PROCHES]
    return {
        "epuisement": epuisement,
        "proches": {"departs": sum(departs[a] for a in proches), "montant": sum(par_annee[a] for a in proches),
                    "part": sum(par_annee[a] for a in proches) / total},
        "svg_annuel": graphiques.echeancier("Prestations probables, par année", annees),
        "svg_cumul": graphiques.echeancier("Prestations probables cumulées, face au fonds constitué", annees,
                                           fonds=fonds or None, cumul=True),
    }


# --- Synthèse -----------------------------------------------------------------

def synthese(e: dict, couv: dict, avertissements: int) -> dict:
    """Les chiffres en phrases, puis la décision à prendre."""
    t, fonds, jour = e["totaux"], e["fonds_disponible"], e["date_evaluation"]
    date_fr = date.fromisoformat(jour[:10]).strftime("%d/%m/%Y")
    constats = [
        ("Ce que l'entreprise doit aujourd'hui",
         f"Les indemnités de fin de carrière déjà acquises par vos {t['effectif']} salariés valent {_montant(t['dette'])} "
         f"au {date_fr}, compte tenu des chances que chacun parte à la retraite dans l'entreprise. C'est la dette "
         "actuarielle : l'engagement que vos comptes doivent refléter à cette date."),
        ("Ce que coûte l'année qui vient",
         f"Une année de service de plus fait acquérir {_montant(t['charge'])} de droits : c'est la charge de "
         "l'exercice."),
    ]
    if t["cotisation_nette"] > 0:
        frais = t["cotisation_totale"] - t["cotisation_nette"]
        constats.append(("Ce qu'il faudrait verser",
                         f"Avec un fonds déclaré de {_montant(fonds)}, il manque {_montant(t['cotisation_nette'])} pour "
                         f"couvrir la dette et la charge ; {_montant(t['cotisation_totale'])} avec les frais de gestion "
                         f"({_montant(frais)})."))
    else:
        constats.append(("Ce qu'il faudrait verser",
                         f"Le fonds déclaré ({_montant(fonds)}) couvre la dette et la charge : aucune cotisation "
                         "d'ajustement n'est due."))
    p = couv["proches"]
    sortie = (f"{p['departs']} départ{'s' if p['departs'] > 1 else ''} à la retraite dans les {PROCHES} prochaines "
              f"années, pour {_montant(p['montant'])} de prestations probables ({pct(round(p['part'], 3))} de "
              "l'ensemble).")
    if fonds:
        premiere = int(jour[:4])
        if couv["epuisement"] is None:
            sortie += " Le fonds constitué couvre tous les départs prévus."
        elif couv["epuisement"] == premiere:
            sortie += f" Dès {premiere}, les versements dépassent le fonds constitué."
        else:
            sortie += (f" Le fonds constitué couvre les départs jusqu'en {couv['epuisement'] - 1} ; au-delà, les "
                       "versements le dépassent.")
    constats.append(("Quand l'argent sort", sortie))
    s = e["sensibilites"].get("taux_actualisation_moins_1pt")
    if s and t["dette"]:
        constats.append(("Ce qui fait bouger le chiffre",
                         f"Le taux d'actualisation, surtout : avec un point de moins, la dette passerait à "
                         f"{_montant(s['dette'])} ({pct(round((s['dette'] - t['dette']) / t['dette'], 3))} de plus). "
                         "Les autres hypothèses sont détaillées plus loin, avec ce que chacune pèse."))
    decisions = ["Constater l'engagement dans les comptes de l'exercice, à hauteur de la dette actuarielle."]
    if t["cotisation_nette"] > 0:
        decisions.append("Choisir comment le financer : verser la cotisation d'ajustement en une fois, l'étaler sur "
                         "quelques années, ou provisionner en interne. La page Financement du dossier compare ces "
                         "voies, avec les offres des assureurs.")
    else:
        decisions.append("Continuer d'alimenter le fonds au rythme de la charge annuelle, et le revoir à la "
                         "prochaine étude.")
    if avertissements:
        decisions.append(f"Traiter les {avertissements} point{'s' if avertissements > 1 else ''} d'attention en fin de "
                         "rapport avant de s'appuyer sur ce chiffre.")
    decisions.append("Refaire l'étude à chaque clôture annuelle, ou dès que le personnel ou le régime change "
                     "sensiblement.")
    return {"constats": constats, "decisions": decisions}
