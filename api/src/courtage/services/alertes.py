"""Les points d'attention d'un dossier : calculés à la lecture, jamais stockés.

Une alerte dit ce qui attend, qui doit agir, et où. Elle disparaît d'elle-même quand sa cause est réglée :
une étude renouvelée, un dossier payé, un assureur choisi. Trois niveaux : « grave » (à traiter maintenant),
« attention » (à traiter bientôt), « info » (à savoir).
"""
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Etude, FicheRegime, FichierPersonnel, Organisation, VersionRegime
from courtage.fichier.controles import FRAICHEUR_MOIS

from . import dossiers, reponses

ORDRE = {"grave": 0, "attention": 1, "info": 2}
ATTENTE_BROUILLON = 30        # jours avant qu'un brouillon d'étude ou une version de régime en attente le soit trop
VERIFICATION = 7              # jours pour que le conseiller vérifie un dossier de prise en charge déclaré
COMPLEMENT = 15               # jours après lesquels des pièces demandées se relancent


def _alerte(niveau: str, code: str, titre: str, detail: str, lien: str, pour: str) -> dict:
    return {"niveau": niveau, "code": code, "titre": titre, "detail": detail, "lien": lien, "pour": pour}


def du_dossier(session: Session, org: Organisation, aujourd_hui: date) -> list[dict]:
    """Les alertes du dossier ouvert (le contexte RLS de l'organisation est posé par l'appelant)."""
    alertes = _etudes(session, aujourd_hui) + _personnel(session, aujourd_hui) + _regime(session, aujourd_hui)
    alertes += _prises_en_charge(session, aujourd_hui) + _cahiers(session, aujourd_hui)
    return sorted(alertes, key=lambda a: ORDRE[a["niveau"]])


def _jours(depuis, aujourd_hui: date) -> int:
    return (aujourd_hui - (depuis.date() if hasattr(depuis, "date") else depuis)).days


def _etudes(session: Session, aujourd_hui: date) -> list[dict]:
    etudes = list(session.scalars(select(Etude).order_by(Etude.date_evaluation.desc())))
    emises = [e for e in etudes if e.statut == "emise"]
    alertes = []
    if emises:
        derniere = emises[0]
        age = relativedelta(aujourd_hui, derniere.date_evaluation)
        mois = age.years * 12 + age.months
        if mois >= 12:
            alertes.append(_alerte(
                "grave" if mois >= 24 else "attention", "etude_a_renouveler",
                "Une nouvelle étude s'impose",
                f"La dernière étude émise est au {derniere.date_evaluation:%d/%m/%Y}, il y a {mois} mois : l'engagement "
                "s'évalue à chaque clôture annuelle.", "etudes", "entreprise"))
    elif any(True for _ in session.scalars(select(FichierPersonnel.id).limit(1))):
        alertes.append(_alerte("info", "aucune_etude", "Aucune étude émise",
                               "Le personnel est déposé : l'évaluation de l'engagement peut être lancée.", "etudes",
                               "entreprise"))
    for e in etudes:
        if e.statut == "brouillon" and _jours(e.cree_le, aujourd_hui) > ATTENTE_BROUILLON and \
                not any(x.date_evaluation >= e.date_evaluation for x in emises):
            alertes.append(_alerte("info", "brouillon_en_attente", "Un brouillon attend l'émission",
                                   f"L'étude au {e.date_evaluation:%d/%m/%Y} est en brouillon depuis "
                                   f"{_jours(e.cree_le, aujourd_hui)} jours : le conseiller la relit et l'émet.",
                                   f"etudes/{e.id}", "conseiller"))
    return alertes


def _personnel(session: Session, aujourd_hui: date) -> list[dict]:
    dernier = session.scalars(select(FichierPersonnel).order_by(FichierPersonnel.date_donnees.desc()).limit(1)).first()
    if dernier is None or dernier.date_donnees + relativedelta(months=FRAICHEUR_MOIS) >= aujourd_hui:
        return []
    return [_alerte("attention", "donnees_anciennes", "Le personnel est à mettre à jour",
                    f"Le dernier fichier est arrêté au {dernier.date_donnees:%d/%m/%Y}, il y a plus de {FRAICHEUR_MOIS} "
                    "mois : une étude à une clôture récente ne pourra pas être émise dessus. Déposer un fichier à jour "
                    "(le canevas est sur la page).", "personnel", "entreprise")]


def _regime(session: Session, aujourd_hui: date) -> list[dict]:
    return [_alerte("info", "version_a_adopter", "Une version du régime attend l'adoption",
                    f"La version {v.numero}, du {v.en_vigueur_du:%d/%m/%Y}, est en analyse depuis "
                    f"{_jours(v.cree_le, aujourd_hui)} jours : l'entreprise l'adopte ou la laisse.", "regime", "entreprise")
            for v in session.scalars(select(VersionRegime).where(VersionRegime.statut == "analyse"))
            if _jours(v.cree_le, aujourd_hui) > ATTENTE_BROUILLON]


def _prises_en_charge(session: Session, aujourd_hui: date) -> list[dict]:
    alertes = []
    for d in dossiers.lister(session):
        evenements = dossiers._evenements(session, d)
        if not evenements:
            continue
        dernier, lien = evenements[-1], f"dossiers/{d.id}"
        depuis = _jours(dernier.le, aujourd_hui)
        quoi = f"Le dossier de prise en charge du matricule {d.matricule}"
        for c in dossiers._constats(session, d, evenements, aujourd_hui):
            alertes.append(_alerte("grave", c["code"], "L'assureur tarde à payer", f"{quoi} : {c['message']}", lien,
                                   "conseiller"))
        if dernier.etape in ("declare", "resoumis") and depuis > VERIFICATION:
            alertes.append(_alerte("attention", "verification_en_attente", "Un dossier attend la vérification",
                                   f"{quoi} est déclaré depuis {depuis} jours : le conseiller vérifie les pièces "
                                   "avant de le transmettre.", lien, "conseiller"))
        elif dernier.etape == "a_completer" and depuis > COMPLEMENT:
            alertes.append(_alerte("attention", "pieces_attendues", "Des pièces sont attendues",
                                   f"{quoi} attend des compléments depuis {depuis} jours.", lien, "entreprise"))
        elif dernier.etape == "refuse":
            alertes.append(_alerte("attention", "prise_en_charge_refusee", "Une prise en charge a été refusée",
                                   f"{quoi} a été refusé par l'assureur"
                                   + (f" : « {dernier.motif} »" if dernier.motif else "")
                                   + ". Compléter et transmettre à nouveau, ou contester.", lien, "conseiller"))
    return alertes


def _cahiers(session: Session, aujourd_hui: date) -> list[dict]:
    alertes = []
    for f in session.scalars(select(FicheRegime)):
        if reponses.choix(session, f) is not None:
            continue
        n = len(reponses.actives(session, f))
        lien = f"cahier/{f.id}"
        if f.date_limite_reponse < aujourd_hui:
            alertes.append(_alerte("attention", "assureur_a_choisir", "Les réponses sont closes : un assureur à choisir",
                                   f"Réponses attendues avant le {f.date_limite_reponse:%d/%m/%Y} ; {n} reçue(s). "
                                   "L'entreprise choisit, et motive un autre choix que la recommandée.", lien, "entreprise")
                           if n else
                           _alerte("attention", "aucune_reponse", "Aucune réponse d'assureur",
                                   f"La date limite du {f.date_limite_reponse:%d/%m/%Y} est passée sans réponse : "
                                   "relancer les assureurs ou reporter la date.", lien, "conseiller"))
        elif n == 0 and (f.date_limite_reponse - aujourd_hui).days <= 7:
            alertes.append(_alerte("info", "reponses_attendues", "Date limite proche, aucune réponse",
                                   f"Les assureurs doivent répondre avant le {f.date_limite_reponse:%d/%m/%Y}.", lien,
                                   "conseiller"))
    return alertes
