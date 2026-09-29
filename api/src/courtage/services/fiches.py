"""Fiche régime : le cahier des charges envoyé aux assureurs, depuis une étude émise.

La fiche dit aux assureurs ce qu'on leur demande de financer (le régime,
l'engagement chiffré et scellé, la population en agrégats) et à quelles
conditions (taux, frais, participation, transfert, délai de paiement). La
grille de réponse reprend les conditions d'une `Offre` du module de
financement : une réponse remplie se compare directement.
"""
import hashlib
import json
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Document, Etude, FicheRegime, Organisation, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import t
from courtage.fiche import agreger_population, regrouper_echeancier
from courtage.referentiel import referentiel_courant

from . import etudes, experience, fichiers, hypotheses, journaliser, rapport, regimes

GRILLE_DE_REPONSE = {
    "taux_garanti": "Taux minimum garanti annuel sur le fonds (ex. 0,025 pour 2,5 %)",
    "participation_benefices": "Part des produits financiers au-delà du garanti rendue au fonds (0 à 1)",
    "historique_participation_5_ans": "Taux servis sur ce type de contrat les cinq dernières années",
    "frais_sur_cotisations": "Frais prélevés sur chaque cotisation (0 à 1)",
    "frais_sur_encours": "Frais annuels prélevés sur le fonds (0 à 1)",
    "delai_paiement_jours": "Délai entre la demande de l'entreprise et le versement d'une indemnité",
    "transfert_preavis_mois": "Préavis pour transférer le fonds chez un autre assureur",
    "transfert_penalite": "Pénalité de transfert, en part du fonds (0 à 1)",
    "accepte_etude_plateforme": "L'étude jointe sert-elle de base au contrat (oui / non) ?",
    "reporting_annuel": "Relevé annuel du fonds et rapprochement avec l'étude (oui / non)",
}


def emettre(session: Session, org: Organisation, auteur: uuid.UUID, *, etude_id: uuid.UUID, conditions: dict,
            date_limite_reponse: date, config: rapport.ConfigSceau, aujourd_hui: date) -> tuple[FicheRegime, Document]:
    etude = etudes.obtenir(session, etude_id)
    if etude.statut != "emise":
        raise ErreurMetier("etude_non_emise", t("Une fiche part d'une étude émise : ses chiffres sont scellés.", "A sheet is built from an issued study: its figures are sealed."), 409)
    if date_limite_reponse <= aujourd_hui:
        raise ErreurMetier("date_limite_passee", t("La date limite de réponse doit être à venir.", "The response deadline must be in the future."), 422)

    contenu = _contenu(session, org, etude, conditions, date_limite_reponse)
    empreinte = hashlib.sha256(json.dumps(contenu, sort_keys=True, separators=(",", ":"),
                                          ensure_ascii=False).encode("utf-8")).hexdigest()
    fiche = FicheRegime(organisation_id=org.id, etude_id=etude.id, regime_version_id=etude.regime_version_id,
                        date_limite_reponse=date_limite_reponse, conditions=conditions, contenu=contenu,
                        empreinte=empreinte, emise_par=auteur)
    session.add(fiche)
    session.flush()

    emetteur = session.get(Utilisateur, auteur)
    resume = {"organisation": org.nom, "pays": org.pays, "date_evaluation": etude.date_evaluation.isoformat(),
              "effectif": contenu["population"]["effectif"], "dette": contenu["etude"]["totaux"]["dette"],
              "date_limite_reponse": date_limite_reponse.isoformat(), "emis_le": aujourd_hui.isoformat(),
              "emetteur": rapport.nom_de(emetteur), "probant": config.probant}
    document = rapport.sceller_document(
        session, org, nature="fiche_regime", empreinte=empreinte, resume=resume, config=config,
        gabarit="fiche_regime.html", fiche_id=fiche.id,
        contexte=lambda numero, sceau: {
            "org": org, "c": contenu, "numero": numero, "sceau": sceau, "empreinte": empreinte,
            "url_verification": f"{config.url_publique}/verifier/{numero}", "probant": config.probant,
            "emetteur": rapport.nom_de(emetteur), "emis_le": aujourd_hui, "grille": GRILLE_DE_REPONSE,
            "sensibilites": hypotheses.SENSIBILITES})
    journaliser(session, org.id, auteur, "fiche.emise", fiche.id, {"numero": document.numero, "etude_id": str(etude.id)})
    return fiche, document


def lister(session: Session) -> list[tuple[FicheRegime, str]]:
    rangs = session.execute(select(FicheRegime, Document.numero).join(Document, Document.fiche_id == FicheRegime.id)
                            .order_by(FicheRegime.emise_le.desc())).all()
    return [(f, n) for f, n in rangs]


def obtenir(session: Session, fiche_id: uuid.UUID) -> tuple[FicheRegime, Document]:
    fiche = session.get(FicheRegime, fiche_id)
    if fiche is None:
        raise Introuvable("Fiche")
    return fiche, session.scalars(select(Document).where(Document.fiche_id == fiche.id)).one()


def en_clair(fiche: FicheRegime, numero: str) -> dict:
    return {"id": str(fiche.id), "numero": numero, "etude_id": str(fiche.etude_id),
            "date_limite_reponse": fiche.date_limite_reponse.isoformat(), "emise_le": fiche.emise_le.isoformat(),
            "contenu": fiche.contenu}


def _contenu(session: Session, org: Organisation, etude: Etude, conditions: dict, date_limite: date) -> dict:
    e = etudes.en_clair(session, org, etude, etude.date_evaluation)
    fichier = fichiers.obtenir(session, etude.fichier_id)
    salaire_de = {l["matricule"]: l["salaire_annuel"] or 0 for l in fichier.lignes}
    lignes = e["lignes"]
    population = agreger_population(
        [{"age": l["age"], "anciennete": l["anciennete"], "categorie": l.get("categorie")} for l in lignes],
        [salaire_de.get(l["matricule"], 0) for l in lignes])
    if etude.regime_version_id:
        v = regimes.en_clair(session, regimes.obtenir_version(session, etude.regime_version_id), etude.date_evaluation)
        regime = {k: v[k] for k in ("nom", "numero", "en_vigueur_du", "fondement", "document_reference", "categories")}
    else:
        convention = referentiel_courant().convention(etude.convention_code, etude.convention_du)
        regime = {"nom": convention.libelle, "convention_seule": True, "categories": [
            {"categorie": "*", "convention_code": convention.code, "bareme": convention.bareme.model_dump(mode="json")}]}
    return {
        "organisation": {"nom": org.nom, "pays": org.pays, "secteur": org.secteur},
        "regime": regime,
        "etude": {"rapport": e["rapport"]["numero"] if e["rapport"] else None,
                  "date_evaluation": e["date_evaluation"], "convention": e["convention"]["code"],
                  "hypotheses": e["hypotheses"]["valeurs"], "fonds_disponible": e["fonds_disponible"],
                  "totaux": {k: e["totaux"][k] for k in ("dette", "charge", "vapf", "cotisation_totale")},
                  "sensibilites": e["sensibilites"],
                  # Les hypothèses telles qu'on les lit : l'assureur voit sur quoi repose le besoin chiffré.
                  "hypotheses_lues": hypotheses.pour_le_lecteur(e["hypotheses"]["valeurs"], e["hypotheses"]["ecarts"],
                                                                e["sensibilites"], e["totaux"]["dette"])},
        "population": population,
        "echeancier": regrouper_echeancier(e["echeancier"], depuis=etude.date_evaluation.year),
        # L'expérience réelle : les retraites passées par années regroupées, les délais de paiement constatés.
        "experience": experience.pour_cahier(session, etude.date_evaluation),
        "conditions_demandees": conditions,
        "date_limite_reponse": date_limite.isoformat(),
        "grille_de_reponse": GRILLE_DE_REPONSE,
    }
