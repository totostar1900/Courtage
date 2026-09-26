"""Étude IFC : brouillon calculé, recalculé à volonté, puis émise par un conseiller.

Un brouillon garde tout ce qu'il faut pour être refait à l'identique : la
version du référentiel, la convention et la date d'effet de son barème, les
hypothèses retenues et leurs écarts justifiés, le fichier tel que lu. À
l'émission s'ajoutent l'empreinte, l'émetteur et les honoraires dus selon les
conditions du jour ; la base interdit ensuite toute modification.
"""
import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field, replace
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import VERSION_MOTEUR, Hypotheses, Resultat, evaluer
from courtage.db import Etude, Organisation
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.fichier import Anomalie, controler, controler_parametres, controler_resultat, salaries
from courtage.referentiel import HYPOTHESES_PAR_DEFAUT, motifs_de_refus, referentiel_courant

from . import fichiers, journaliser, remuneration

ECART_MAX_ETUDE_PRECEDENTE = 0.25
AGE_PREMIER_EMPLOI = 18
_SAISISSABLES = {"taux_actualisation": float, "croissance_salaires": float, "inflation": float,
                 "age_retraite": int, "taux_turnover": float}


@dataclass
class Saisie:
    fichier_id: uuid.UUID
    date_evaluation: date
    convention_code: str
    fonds_disponible: int
    hypotheses: dict = field(default_factory=dict)
    justification: str | None = None


# --- Écritures ----------------------------------------------------------------

def creer(session: Session, org: Organisation, auteur: uuid.UUID, saisie: Saisie) -> Etude:
    etude = Etude(organisation_id=org.id, **_calculer(session, org, saisie))
    session.add(etude)
    session.flush()
    journaliser(session, org.id, auteur, "etude.creee", etude.id,
                {"convention": saisie.convention_code, "date_evaluation": saisie.date_evaluation.isoformat()})
    return etude


def recalculer(session: Session, org: Organisation, etude: Etude, auteur: uuid.UUID, saisie: Saisie) -> Etude:
    _exiger_brouillon(etude)
    for cle, valeur in _calculer(session, org, saisie, sauf=etude.id).items():
        setattr(etude, cle, valeur)
    session.flush()
    journaliser(session, org.id, auteur, "etude.recalculee", etude.id)
    return etude


def supprimer(session: Session, etude: Etude, auteur: uuid.UUID) -> None:
    _exiger_brouillon(etude)
    journaliser(session, etude.organisation_id, auteur, "etude.supprimee", etude.id)
    session.delete(etude)
    session.flush()


def emettre(session: Session, org: Organisation, etude: Etude, auteur: uuid.UUID, aujourd_hui: date) -> Etude:
    _exiger_brouillon(etude)
    motifs = motifs_emission(session, org, etude, aujourd_hui)
    if motifs:
        raise ErreurMetier("emission_refusee", "L'étude ne peut pas être émise : " + ", ".join(motifs) + ".", 409,
                           {"motifs": motifs})
    conditions = remuneration.en_vigueur(session, aujourd_hui)
    etude.statut = "emise"
    etude.emise_par = auteur
    etude.emise_le = datetime.now(timezone.utc)
    etude.conditions_remuneration_id = conditions.id
    etude.honoraires_ht = remuneration.honoraires_etude(conditions, etude.resultats["totaux"]["effectif"])
    etude.empreinte = empreinte(etude)
    session.flush()
    journaliser(session, org.id, auteur, "etude.emise", etude.id,
                {"empreinte": etude.empreinte, "honoraires_ht": etude.honoraires_ht})
    return etude


# --- Lectures -----------------------------------------------------------------

def obtenir(session: Session, etude_id: uuid.UUID) -> Etude:
    etude = session.get(Etude, etude_id)
    if etude is None:
        raise Introuvable("Étude")
    return etude


def lister(session: Session) -> list[Etude]:
    return list(session.scalars(select(Etude).order_by(Etude.date_evaluation.desc(), Etude.cree_le.desc())))


def motifs_emission(session: Session, org: Organisation, etude: Etude, aujourd_hui: date) -> list[str]:
    """Tout ce qui interdit d'émettre ; vide : l'étude peut sortir."""
    motifs = sorted({a["code"] for a in etude.resultats["anomalies"] if a["niveau"] == "bloquant"})
    convention = referentiel_courant().convention(etude.convention_code, etude.convention_du)
    motifs += motifs_de_refus(convention, pays_organisation=org.pays, date_evaluation=etude.date_evaluation)
    if remuneration.en_vigueur(session, aujourd_hui) is None:
        motifs.append("remuneration_absente")
    return motifs


def en_clair(session: Session, org: Organisation, etude: Etude, aujourd_hui: date) -> dict:
    r = etude.resultats
    if etude.statut == "brouillon":
        motifs = motifs_emission(session, org, etude, aujourd_hui)
        emission = {"possible": not motifs, "motifs": motifs}
    else:
        emission = {"possible": False, "motifs": []}
    convention = referentiel_courant().convention(etude.convention_code, etude.convention_du)
    return {
        "id": str(etude.id), "statut": etude.statut, "fichier_id": str(etude.fichier_id),
        "date_evaluation": etude.date_evaluation.isoformat(),
        "convention": {"code": convention.code, "libelle": convention.libelle, "en_vigueur_du": convention.en_vigueur_du.isoformat(),
                       "statut": convention.statut, "verification": convention.verification},
        "referentiel_version": etude.referentiel_version, "version_moteur": etude.version_moteur,
        "hypotheses": etude.hypotheses, "fonds_disponible": etude.fonds_disponible,
        "totaux": r["totaux"], "echeancier": r["echeancier"], "sensibilites": r["sensibilites"],
        "lignes": r["lignes"], "anomalies": r["anomalies"], "emission": emission,
        "empreinte": etude.empreinte, "honoraires_ht": etude.honoraires_ht,
        "emise_le": etude.emise_le.isoformat() if etude.emise_le else None,
        "emise_par": str(etude.emise_par) if etude.emise_par else None,
        "remplace_etude_id": str(etude.remplace_etude_id) if etude.remplace_etude_id else None,
    }


def empreinte(etude: Etude) -> str:
    """SHA-256 d'une forme canonique de tout ce qui fait l'étude."""
    contenu = {
        "organisation_id": str(etude.organisation_id), "fichier_id": str(etude.fichier_id),
        "date_evaluation": etude.date_evaluation.isoformat(), "convention": etude.convention_code,
        "convention_du": etude.convention_du.isoformat(), "referentiel_version": etude.referentiel_version,
        "version_moteur": etude.version_moteur, "hypotheses": etude.hypotheses,
        "fonds_disponible": etude.fonds_disponible, "resultats": etude.resultats,
    }
    canonique = json.dumps(contenu, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonique.encode("utf-8")).hexdigest()


# --- Calcul -------------------------------------------------------------------

def _calculer(session: Session, org: Organisation, saisie: Saisie, sauf: uuid.UUID | None = None) -> dict:
    fichier = fichiers.obtenir(session, saisie.fichier_id)
    lecture = fichiers.relire(fichier)
    ref = referentiel_courant()
    try:
        convention = ref.convention(saisie.convention_code, saisie.date_evaluation)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None

    valeurs, ecarts = _hypotheses(saisie)
    h = Hypotheses(
        date_evaluation=saisie.date_evaluation,
        taux_actualisation=valeurs["taux_actualisation"], croissance_salaires=valeurs["croissance_salaires"],
        inflation=valeurs["inflation"], age_retraite=valeurs["age_retraite"],
        turnover={age: valeurs["taux_turnover"] for age in range(AGE_PREMIER_EMPLOI, valeurs["age_retraite"])},
        table=ref.table(valeurs["table"]), fonds_disponible=saisie.fonds_disponible,
        frais_sur_cotisation=valeurs["frais_sur_cotisation"],
    )
    resultat = evaluer(salaries(lecture), h, convention)

    anomalies: list[Anomalie] = [
        *lecture.anomalies,
        *controler(lecture, date_evaluation=saisie.date_evaluation, age_retraite=h.age_retraite),
        *controler_parametres(date_evaluation=saisie.date_evaluation, date_donnees=fichier.date_donnees),
        *controler_resultat(resultat),
        *_ecart_etude_precedente(session, saisie.date_evaluation, resultat, sauf),
    ]
    return {
        "fichier_id": fichier.id, "referentiel_version": ref.version, "convention_code": convention.code,
        "convention_du": convention.en_vigueur_du, "date_evaluation": saisie.date_evaluation,
        "hypotheses": {"valeurs": valeurs, "ecarts": ecarts, "justification": saisie.justification},
        "fonds_disponible": saisie.fonds_disponible, "version_moteur": VERSION_MOTEUR,
        "resultats": {
            "totaux": _totaux(resultat),
            "lignes": _lignes(resultat),
            "echeancier": _echeancier(resultat, saisie.date_evaluation),
            "sensibilites": _sensibilites(lecture, h, convention),
            "anomalies": [asdict(a) for a in anomalies],
        },
    }


def _hypotheses(saisie: Saisie) -> tuple[dict, list[dict]]:
    valeurs = dict(HYPOTHESES_PAR_DEFAUT)
    ecarts = []
    for champ, valeur in saisie.hypotheses.items():
        if champ not in _SAISISSABLES:
            raise ErreurMetier("hypothese_inconnue", f"Hypothèse inconnue : {champ}.", 422)
        valeur = _SAISISSABLES[champ](valeur)
        if valeur != HYPOTHESES_PAR_DEFAUT[champ]:
            ecarts.append({"champ": champ, "referentiel": HYPOTHESES_PAR_DEFAUT[champ], "retenu": valeur,
                           "justification": saisie.justification})
        valeurs[champ] = valeur
    if ecarts and not (saisie.justification or "").strip():
        raise ErreurMetier("justification_requise",
                           "Une hypothèse qui s'écarte du référentiel doit être justifiée.", 422,
                           {"champs": [e["champ"] for e in ecarts]})
    return valeurs, ecarts


def _ecart_etude_precedente(session: Session, date_evaluation: date, resultat: Resultat,
                            sauf: uuid.UUID | None) -> list[Anomalie]:
    requete = (select(Etude).where(Etude.statut == "emise", Etude.date_evaluation < date_evaluation)
               .order_by(Etude.date_evaluation.desc()).limit(1))
    if sauf is not None:
        requete = requete.where(Etude.id != sauf)
    precedente = session.scalars(requete).first()
    if precedente is None:
        return []
    avant = precedente.resultats["totaux"]["dette"]
    if avant <= 0:
        return []
    ecart = (resultat.totaux.dette - avant) / avant
    if abs(ecart) <= ECART_MAX_ETUDE_PRECEDENTE:
        return []
    return [Anomalie("avertissement", "ecart_etude_precedente",
                     f"La dette passe de {avant:,} F au {precedente.date_evaluation:%d/%m/%Y} à "
                     f"{resultat.totaux.dette:,} F ({ecart:+.0%}) : expliquer l'écart.".replace(",", " "))]


def _totaux(r: Resultat) -> dict:
    t = r.totaux
    return {"effectif": t.effectif, "vapf": t.vapf, "dette": t.dette, "charge": t.charge,
            "cotisation_nette": t.cotisation_nette, "cotisation_totale": t.cotisation_totale}


def _lignes(r: Resultat) -> list[dict]:
    return [{
        "matricule": l.matricule, "age": round(l.age, 2), "anciennete": round(l.anciennete, 2),
        "date_retraite": l.date_retraite.isoformat(), "ifc": round(l.ifc), "vapf": round(l.vapf),
        "dette": round(l.dette), "charge": round(l.charge), "au_dela_de_la_retraite": l.au_dela_de_la_retraite,
    } for l in r.lignes]


def _echeancier(r: Resultat, date_evaluation: date) -> list[dict]:
    """Les départs par année : ce que l'entreprise devra payer, et quand."""
    par_annee: dict[int, dict] = defaultdict(lambda: {"effectif": 0, "ifc": 0.0, "vapf": 0.0})
    for l in r.lignes:
        annee = max(l.date_retraite.year, date_evaluation.year)
        par_annee[annee]["effectif"] += 1
        par_annee[annee]["ifc"] += l.ifc
        par_annee[annee]["vapf"] += l.vapf
    return [{"annee": a, "effectif": v["effectif"], "ifc": round(v["ifc"]), "vapf": round(v["vapf"])}
            for a, v in sorted(par_annee.items())]


def _sensibilites(lecture, h: Hypotheses, convention) -> dict:
    variantes = {
        "taux_actualisation_moins_1pt": replace(h, taux_actualisation=h.taux_actualisation - 0.01),
        "taux_actualisation_plus_1pt": replace(h, taux_actualisation=h.taux_actualisation + 0.01),
        "croissance_salaires_plus_1pt": replace(h, croissance_salaires=h.croissance_salaires + 0.01),
    }
    sal = salaries(lecture)
    totaux = {nom: evaluer(sal, v, convention).totaux for nom, v in variantes.items()}
    return {nom: {"dette": t.dette, "charge": t.charge} for nom, t in totaux.items()}


def _exiger_brouillon(etude: Etude) -> None:
    if etude.statut != "brouillon":
        raise ErreurMetier("etude_emise", "Cette étude est émise : elle ne change plus. Créer une nouvelle étude.", 409)
