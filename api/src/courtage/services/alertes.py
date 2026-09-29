"""Les points d'attention d'un dossier : calculés à la lecture, jamais stockés.

Une alerte dit ce qui attend, qui doit agir, et où. Elle disparaît d'elle-même quand sa cause est réglée :
une étude renouvelée, un dossier payé, un assureur choisi. Trois niveaux : « grave » (à traiter maintenant),
« attention » (à traiter bientôt), « info » (à savoir).
"""
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import EtatDossier, Etude, FicheRegime, FichierPersonnel, Organisation, VersionRegime
from courtage.fichier.controles import FRAICHEUR_MOIS
from courtage.langue import t

from . import annuel, cycle, dossiers, placement, regimes, reponses

ORDRE = {"grave": 0, "attention": 1, "info": 2}
ATTENTE_BROUILLON = 30        # jours avant qu'un brouillon d'étude ou une version de régime en attente le soit trop
VERIFICATION = 7              # jours pour que le conseiller vérifie un dossier de prise en charge déclaré
COMPLEMENT = 15               # jours après lesquels des pièces demandées se relancent


def _alerte(niveau: str, code: str, titre: str, detail: str, lien: str, pour: str) -> dict:
    return {"niveau": niveau, "code": code, "titre": titre, "detail": detail, "lien": lien, "pour": pour}


def du_dossier(session: Session, org: Organisation, aujourd_hui: date) -> list[dict]:
    """Les alertes du dossier ouvert (le contexte RLS de l'organisation est posé par l'appelant).

    Clôturé, le dossier ne dit plus que la date de son archivage : il ne se modifie plus, relancer n'a pas de sens."""
    if org.etat == "cloture":
        prevu = cycle.archivage_prevu(org)
        return [_alerte("attention", "archivage_prevu", t("Le dossier sera archivé", "The file will be archived"),
                        t(f"Clôturé, il sera archivé le {prevu:%d/%m/%Y} : le personnel déposé sera alors effacé et le "
                          "dossier ne s'ouvrira plus. Exporter d'ici là ce que l'entreprise veut garder ; ses documents "
                          "scellés restent vérifiables par leur numéro.",
                          f"Closed, it will be archived on {prevu:%d/%m/%Y}: the uploaded staff data will then be erased "
                          "and the file will no longer open. Export before then whatever the company wants to keep; its "
                          "sealed documents remain verifiable by their number."), "equipe", "entreprise")]
    alertes = _cycle(session, org)
    alertes += _etudes(session, aujourd_hui) + _personnel(session, aujourd_hui) + _regime(session, aujourd_hui)
    alertes += _prises_en_charge(session, aujourd_hui) + _cahiers(session, aujourd_hui)
    alertes += [_alerte(niveau, code, titre, detail, "placement", pour)
                for niveau, code, titre, detail, pour in placement.alertes(session, aujourd_hui)]
    alertes += [_alerte(*x) for x in annuel.alertes(session, aujourd_hui)]
    return sorted(alertes, key=lambda a: ORDRE[a["niveau"]])


def _cycle(session: Session, org: Organisation) -> list[dict]:
    if org.etat != "suspendu":
        return []
    e = session.scalars(select(EtatDossier).where(EtatDossier.etat == "suspendu").order_by(EtatDossier.le.desc())).first()
    motif = ""
    if e is not None:
        libelle = cycle.libelle_motif("suspendre", e.motif_code or "") or ""
        motif = " : " + " — ".join(x for x in (libelle, e.motif) if x) if (libelle or e.motif) else ""
    return [_alerte("attention", "dossier_suspendu", t("Le dossier est suspendu", "The file is suspended"),
                    t(f"Depuis le {org.etat_depuis:%d/%m/%Y}{motif}. Tout se lit et s'exporte ; aucune étude ne s'émet "
                      "et aucun cahier ne part tant que le conseiller ne l'a pas repris.",
                      f"Since {org.etat_depuis:%d/%m/%Y}{motif}. Everything can be read and exported; no study is "
                      "issued and no tender specifications go out until the adviser resumes it."), "equipe", "conseiller")]


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
                t("Une nouvelle étude s'impose", "A new study is needed"),
                t(f"La dernière étude émise est au {derniere.date_evaluation:%d/%m/%Y}, il y a {mois} mois : l'engagement "
                  "s'évalue à chaque clôture annuelle.",
                  f"The last issued study is as at {derniere.date_evaluation:%d/%m/%Y}, {mois} months ago: the "
                  "liability is valued at every year-end close."), "etudes", "entreprise"))
    elif any(True for _ in session.scalars(select(FichierPersonnel.id).limit(1))):
        alertes.append(_alerte("info", "aucune_etude", t("Aucune étude émise", "No study issued"),
                               t("Le personnel est déposé : l'évaluation de l'engagement peut être lancée.",
                                 "The staff data is uploaded: the liability valuation can be started."), "etudes",
                               "entreprise"))
    for e in etudes:
        if e.statut == "brouillon" and _jours(e.cree_le, aujourd_hui) > ATTENTE_BROUILLON and \
                not any(x.date_evaluation >= e.date_evaluation for x in emises):
            alertes.append(_alerte("info", "brouillon_en_attente", t("Un brouillon attend l'émission", "A draft is awaiting issue"),
                                   t(f"L'étude au {e.date_evaluation:%d/%m/%Y} est en brouillon depuis "
                                     f"{_jours(e.cree_le, aujourd_hui)} jours : le conseiller la relit et l'émet.",
                                     f"The study as at {e.date_evaluation:%d/%m/%Y} has been a draft for "
                                     f"{_jours(e.cree_le, aujourd_hui)} days: the adviser reviews and issues it."),
                                   f"etudes/{e.id}", "conseiller"))
    return alertes


def _personnel(session: Session, aujourd_hui: date) -> list[dict]:
    dernier = session.scalars(select(FichierPersonnel).order_by(FichierPersonnel.date_donnees.desc()).limit(1)).first()
    if dernier is None or dernier.date_donnees + relativedelta(months=FRAICHEUR_MOIS) >= aujourd_hui:
        return []
    return [_alerte("attention", "donnees_anciennes", t("Le personnel est à mettre à jour", "The staff data needs updating"),
                    t(f"Le dernier fichier est arrêté au {dernier.date_donnees:%d/%m/%Y}, il y a plus de {FRAICHEUR_MOIS} "
                      "mois : une étude à une clôture récente ne pourra pas être émise dessus. Déposer un fichier à jour "
                      "(le canevas est sur la page).",
                      f"The latest file is as at {dernier.date_donnees:%d/%m/%Y}, more than {FRAICHEUR_MOIS} months "
                      "ago: a study at a recent close cannot be issued on it. Upload an up-to-date file (the template "
                      "is on the page)."), "personnel", "entreprise")]


def _regime(session: Session, aujourd_hui: date) -> list[dict]:
    """Un brouillon sans décision : un rappel à 30 jours ; à 90, une invitation au ménage (il encombre la page)."""
    alertes = []
    for v in session.scalars(select(VersionRegime).where(VersionRegime.statut == "analyse")):
        age = _jours(v.cree_le, aujourd_hui)
        if age >= regimes.JOURS_SANS_DECISION:
            alertes.append(_alerte("attention", "projet_a_trancher", t("Un brouillon de version à trancher", "A draft version needs a decision"),
                                   t(f"La version {v.numero} est un brouillon depuis {age} jours : l'adopter, ou la "
                                     "supprimer (« Faire le ménage » sur la page Régime).",
                                     f"Version {v.numero} has been a draft for {age} days: adopt it, or delete it "
                                     "(“Clean up” on the Plan page)."), "regime", "entreprise"))
        elif age > ATTENTE_BROUILLON:
            alertes.append(_alerte("info", "version_a_adopter", t("Un brouillon de version attend une décision", "A draft version is awaiting a decision"),
                                   t(f"La version {v.numero}, du {v.en_vigueur_du:%d/%m/%Y}, est un brouillon depuis {age} "
                                     "jours : l'entreprise l'adopte, ou on le supprime s'il n'est pas retenu.",
                                     f"Version {v.numero}, effective {v.en_vigueur_du:%d/%m/%Y}, has been a draft for "
                                     f"{age} days: the company adopts it, or it is deleted if not retained."), "regime",
                                   "entreprise"))
    return alertes


def _prises_en_charge(session: Session, aujourd_hui: date) -> list[dict]:
    alertes = []
    for d in dossiers.lister(session):
        evenements = dossiers._evenements(session, d)
        if not evenements:
            continue
        dernier, lien = evenements[-1], f"dossiers/{d.id}"
        depuis = _jours(dernier.le, aujourd_hui)
        quoi = t(f"Le dossier de prise en charge du matricule {d.matricule}",
                 f"The claim file for staff number {d.matricule}")
        for c in dossiers._constats(session, d, evenements, aujourd_hui):
            alertes.append(_alerte("grave", c["code"], t("L'assureur tarde à payer", "The insurer is late paying"), f"{quoi} : {c['message']}", lien,
                                   "conseiller"))
        if dernier.etape in ("declare", "resoumis") and depuis > VERIFICATION:
            alertes.append(_alerte("attention", "verification_en_attente", t("Un dossier attend la vérification", "A file is awaiting verification"),
                                   t(f"{quoi} est déclaré depuis {depuis} jours : le conseiller vérifie les pièces "
                                     "avant de le transmettre.",
                                     f"{quoi} has been declared for {depuis} days: the adviser checks the documents "
                                     "before sending it."), lien, "conseiller"))
        elif dernier.etape == "a_completer" and depuis > COMPLEMENT:
            alertes.append(_alerte("attention", "pieces_attendues", t("Des pièces sont attendues", "Documents are awaited"),
                                   t(f"{quoi} attend des compléments depuis {depuis} jours.",
                                     f"{quoi} has been awaiting further documents for {depuis} days."), lien, "entreprise"))
        elif dernier.etape == "refuse":
            alertes.append(_alerte("attention", "prise_en_charge_refusee", t("Une prise en charge a été refusée", "A claim has been refused"),
                                   t(f"{quoi} a été refusé par l'assureur"
                                     + (f" : « {dernier.motif} »" if dernier.motif else "")
                                     + ". Compléter et transmettre à nouveau, ou contester.",
                                     f"{quoi} was refused by the insurer"
                                     + (f": “{dernier.motif}”" if dernier.motif else "")
                                     + ". Complete and send it again, or dispute it."), lien, "conseiller"))
    return alertes


def _cahiers(session: Session, aujourd_hui: date) -> list[dict]:
    alertes = []
    for f in session.scalars(select(FicheRegime)):
        if reponses.choix(session, f) is not None:
            continue
        n = len(reponses.actives(session, f))
        lien = f"cahier/{f.id}"
        if f.date_limite_reponse < aujourd_hui:
            alertes.append(_alerte("attention", "assureur_a_choisir", t("Les réponses sont closes : un assureur à choisir",
                                     "Responses are closed: an insurer to choose"),
                                   t(f"Réponses attendues avant le {f.date_limite_reponse:%d/%m/%Y} ; {n} reçue(s). "
                                     "L'entreprise choisit, et motive un autre choix que la recommandée.",
                                     f"Responses expected before {f.date_limite_reponse:%d/%m/%Y}; {n} received. "
                                     "The company chooses, and gives reasons for any choice other than the "
                                     "recommended one."), lien, "entreprise")
                           if n else
                           _alerte("attention", "aucune_reponse", t("Aucune réponse d'assureur", "No insurer response"),
                                   t(f"La date limite du {f.date_limite_reponse:%d/%m/%Y} est passée sans réponse : "
                                     "relancer les assureurs ou reporter la date.",
                                     f"The deadline of {f.date_limite_reponse:%d/%m/%Y} has passed with no response: "
                                     "chase the insurers or postpone the date."), lien, "conseiller"))
        elif n == 0 and (f.date_limite_reponse - aujourd_hui).days <= 7:
            alertes.append(_alerte("info", "reponses_attendues", t("Date limite proche, aucune réponse", "Deadline near, no response"),
                                   t(f"Les assureurs doivent répondre avant le {f.date_limite_reponse:%d/%m/%Y}.",
                                     f"Insurers must respond before {f.date_limite_reponse:%d/%m/%Y}."), lien,
                                   "conseiller"))
    return alertes
