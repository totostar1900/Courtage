"""Le pipeline et le portefeuille du courtier : chaque dossier à son étape, et les dossiers sous mandat avec ce qui les
attend (spec 2026-09-29 §3).

Lu dossier par dossier, chacun dans son propre contexte (RLS) ; rien de nouveau n'est stocké. L'administrateur de la
plateforme voit tous les dossiers vivants ; un conseiller, ceux qu'il suit.
"""
from datetime import date, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from courtage.db import (Adhesion, ChoixFiche, Contrat, FicheRegime, MandatCourtage, Organisation, Police, Utilisateur,
                         contexte)
from courtage.langue import t

from . import alertes, annuel, dossiers, placement

ETAPES = ("inscrit", "confirme", "accompagnement_demande", "mandat_propose", "sous_mandat", "consultation",
          "offre_choisie", "en_vigueur")


def libelles() -> dict[str, str]:
    return {"inscrit": t("Inscrit, à confirmer", "Signed up, to confirm"), "confirme": t("Confirmé", "Confirmed"),
            "accompagnement_demande": t("Accompagnement demandé", "Support requested"),
            "mandat_propose": t("Mandat proposé", "Mandate proposed"), "sous_mandat": t("Sous mandat", "Under mandate"),
            "consultation": t("En consultation", "Tendering"), "offre_choisie": t("Offre choisie", "Offer chosen"),
            "en_vigueur": t("Police en vigueur", "Policy in force")}


def _jour(x) -> str | None:
    if x is None:
        return None
    return (x.date() if isinstance(x, datetime) else x).isoformat()


def _etape(session: Session, org: Organisation, aujourd_hui: date) -> tuple[str, str | None]:
    """L'étape la plus avancée du dossier, et depuis quand."""
    if org.activation == "en_attente":
        return "inscrit", _jour(org.activation_demandee_le)
    polices = list(session.scalars(select(Police)))
    for p in polices:
        s = placement.statut(session, p, aujourd_hui)
        if s["code"] == "en_vigueur":
            return "en_vigueur", next(e["le"] for e in s["etapes"] if e["code"] == "en_vigueur")
    choix = session.scalars(select(ChoixFiche).order_by(ChoixFiche.choisi_le.desc())).first()
    if choix is not None:
        return "offre_choisie", _jour(choix.choisi_le)
    fiche = session.scalars(select(FicheRegime).order_by(FicheRegime.emise_le.desc())).first()
    if fiche is not None:
        return "consultation", _jour(fiche.emise_le)
    signe = session.scalars(select(MandatCourtage).where(MandatCourtage.statut == "signe")
                            .order_by(MandatCourtage.signe_le.desc())).first()
    if signe is not None:
        return "sous_mandat", _jour(signe.signe_le)
    courtage = session.scalars(select(Contrat).where(Contrat.service == "courtage", Contrat.en_vigueur_du <= aujourd_hui)
                               .order_by(Contrat.en_vigueur_du.desc())).first()
    if courtage is not None:
        return "sous_mandat", _jour(courtage.en_vigueur_du)
    en_cours = session.scalars(select(MandatCourtage).where(MandatCourtage.statut.in_(("demande", "propose")))
                               .order_by(MandatCourtage.demande_le.desc())).first()
    if en_cours is not None and en_cours.statut == "propose":
        return "mandat_propose", _jour(en_cours.propose_le)
    if en_cours is not None:
        return "accompagnement_demande", _jour(en_cours.demande_le)
    return "confirme", _jour(org.activation_decidee_le)


def _ligne(session: Session, org: Organisation, aujourd_hui: date) -> dict:
    etape, depuis = _etape(session, org, aujourd_hui)
    conseillers = [u.nom_affiche or u.email or "—" for u in session.scalars(
        select(Utilisateur).join(Adhesion, Adhesion.utilisateur_id == Utilisateur.id)
        .where(Adhesion.organisation_id == org.id, Adhesion.role == "conseiller"))]
    ligne = {"id": str(org.id), "nom": org.nom, "pays": org.pays, "etape": etape, "depuis": depuis,
             "jours": (aujourd_hui - date.fromisoformat(depuis)).days if depuis else None, "conseillers": conseillers}
    if ETAPES.index(etape) >= ETAPES.index("sous_mandat"):
        polices = [(p, placement.statut(session, p, aujourd_hui)["code"]) for p in session.scalars(select(Police))]
        retards = sum(1 for p, _ in polices for a in placement._appels(session, p)
                      if placement.etat_appel(a, aujourd_hui) == "en_retard")
        cal = annuel.calendrier(session, aujourd_hui)
        prochaine = next((e for e in cal["etapes"] if e["etat"] != "fait"), None)
        ouverts = sum(1 for d in dossiers.lister(session) if dossiers.statut(session, d) not in ("paye", "refuse"))
        graves = sum(1 for a in alertes.du_dossier(session, org, aujourd_hui) if a["niveau"] == "grave")
        ligne["portefeuille"] = {
            "polices": [{"assureur": p.assureur, "statut": s, "numero": p.numero_police} for p, s in polices],
            "primes_en_retard": retards, "prochaine_etape": prochaine, "prises_en_charge_ouvertes": ouverts,
            "alertes_graves": graves}
    return ligne


def tableau(session: Session, moi: Utilisateur, aujourd_hui: date) -> dict:
    requete = select(Organisation).where(Organisation.etat.not_in(("archive", "supprime")),
                                         Organisation.activation != "refusee")
    if not moi.admin_plateforme:
        suivis = select(Adhesion.organisation_id).where(Adhesion.utilisateur_id == moi.id, Adhesion.role == "conseiller")
        requete = requete.where(Organisation.id.in_(suivis))
    lignes = []
    for org in list(session.scalars(requete.order_by(Organisation.nom))):
        contexte(session.connection(), org.id)
        lignes.append(_ligne(session, org, aujourd_hui))
    session.execute(text("SELECT set_config('app.organisation_id', '', true)"))
    libelle = libelles()
    return {"etapes": [{"code": e, "libelle": libelle[e], "n": sum(1 for x in lignes if x["etape"] == e)} for e in ETAPES],
            "dossiers": lignes}
