"""Comparaison : orienter l'entreprise vers son assureur (spec prestations §3).

Hors courtage, la plateforme ne porte pas la prestation : elle dit à qui
s'adresser, avec quelles pièces et pour quel montant, et fournit sa FICHE DE
CALCUL scellée à joindre à la demande. Elle ne recueille rien : ni identité, ni
pièce. L'entreprise peut ensuite déclarer ce que l'assureur a payé
(`prestations.declarer_paiement`), pour que ses rapports tiennent compte de
l'expérience réelle.
"""
import hashlib
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Contrat, Document, Organisation, Prestation, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import langue, t

from . import contrats, journaliser, prestations, rapport
from .dossiers import _delai

# Ce que les assureurs demandent d'ordinaire : une aide, pas une liste officielle.
PIECES = [
    {"nature": "courrier_demande", "libelle": "La demande de l'entreprise",
     "detail": "Un courrier signé qui cite la police, le matricule, la date de départ et le montant demandé."},
    {"nature": "fiche_de_calcul", "libelle": "La fiche de calcul de la plateforme",
     "detail": "Scellée : l'assureur vérifie en ligne qu'elle n'a pas été modifiée."},
    {"nature": "certificat_travail", "libelle": "Le certificat de travail",
     "detail": "Il établit les dates d'embauche et de départ."},
    {"nature": "attestation_depart", "libelle": "L'attestation de départ en retraite",
     "detail": "Ou la notification de mise à la retraite."},
    {"nature": "piece_identite", "libelle": "La pièce d'identité du salarié",
     "detail": "À transmettre à l'assureur seul : la plateforme ne la demande pas."},
    {"nature": "coordonnees_paiement", "libelle": "Les coordonnées de paiement",
     "detail": "De l'entreprise si l'assureur la rembourse, du salarié s'il le paie directement."},
    {"nature": "justificatif_versement", "libelle": "La preuve du versement au salarié",
     "detail": "Si l'entreprise a déjà payé l'indemnité et en demande le remboursement."},
]


PIECES_EN = {
    "courrier_demande": ("The company's request",
                         "A signed letter quoting the policy, the staff number, the departure date and the amount "
                         "claimed."),
    "fiche_de_calcul": ("The platform's calculation sheet",
                        "Sealed: the insurer checks online that it has not been altered."),
    "certificat_travail": ("The employment certificate", "It establishes the hire and departure dates."),
    "attestation_depart": ("The retirement certificate", "Or the notice of retirement."),
    "piece_identite": ("The employee's identity document",
                       "To be sent to the insurer only: the platform does not ask for it."),
    "coordonnees_paiement": ("The payment details",
                             "The company's if the insurer reimburses it, the employee's if the insurer pays them "
                             "directly."),
    "justificatif_versement": ("Proof of payment to the employee",
                               "If the company has already paid the benefit and is claiming reimbursement."),
}


def pieces() -> list[dict]:
    """Les pièces usuelles, dans la langue de l'écran."""
    if langue() != "en":
        return PIECES
    return [{**p, "libelle": PIECES_EN[p["nature"]][0], "detail": PIECES_EN[p["nature"]][1]} for p in PIECES]


def _prestation_retraite(session: Session, prestation_id) -> Prestation:
    p = session.get(Prestation, prestation_id)
    if p is None or p.annulation:
        raise Introuvable("Prestation")
    if p.motif != "retraite":
        raise ErreurMetier("pas_d_ifc", t("Seul un départ en retraite ouvre droit à l'IFC : rien à demander.",
                                           "Only a retirement gives entitlement to the IFC: nothing to claim."), 409)
    return p


def orienter(session: Session, prestation_id) -> dict:
    p = _prestation_retraite(session, prestation_id)
    service = contrats.service_a_la_date(session, p.date_depart)
    c = service.contrat
    delai, exige = _delai(session)
    a_demander = min(p.du, p.verse) if p.verse is not None else p.du
    if service.service == "courtage":
        message = t("Au jour de ce départ, la plateforme est votre courtier : elle porte la demande. Ouvrez le dossier "
                    "de prise en charge.",
                    "On the date of this departure, the platform is your broker: it handles the claim. Open the "
                    "claim file.")
    elif c and c.assureur:
        message = t(f"Adressez la demande à {c.assureur}, avec les pièces ci-dessous. La plateforme ne transmet rien "
                    "et ne recueille aucune identité.",
                    f"Send the claim to {c.assureur}, with the documents below. The platform forwards nothing and "
                    "collects no identity.")
    else:
        message = t("Aucun assureur n'est enregistré pour ce départ : adressez-vous à celui qui gère votre fonds "
                    "d'IFC, et demandez à votre conseiller de l'enregistrer dans « Contrat ».",
                    "No insurer is recorded for this departure: contact whoever manages your IFC fund, and ask your "
                    "adviser to record it under “Contract”.")
    return {
        "prestation_id": str(p.id), "service": service.service,
        "qui_s_en_occupe": "plateforme" if service.service == "courtage" else "entreprise",
        "assureur": c.assureur if c else None, "numero_police": c.numero_police if c else None,
        "date_effet_police": c.date_effet_police.isoformat() if c and c.date_effet_police else None,
        "du": p.du, "verse": p.verse, "montant_a_demander": a_demander,
        "calcul": prestations._calcul_en_clair(p.calcul),
        "delai_jours": delai, "delai_exige": exige, "pieces": pieces(), "message": message,
    }


def fiche_de_calcul(session: Session, org: Organisation, auteur, prestation_id, config: rapport.ConfigSceau,
                    aujourd_hui: date) -> Document:
    """La fiche scellée d'une ligne : rendue une fois, la même ensuite."""
    p = _prestation_retraite(session, prestation_id)
    deja = session.scalars(select(Document).where(Document.prestation_id == p.id)).first()
    if deja is not None:
        return deja
    service = contrats.service_a_la_date(session, p.date_depart)
    c: Contrat | None = service.contrat
    emetteur = session.get(Utilisateur, auteur)
    contenu = {"prestation": str(p.id), "matricule": p.matricule, "date_embauche": p.date_embauche.isoformat(),
               "date_depart": p.date_depart.isoformat(), "salaire": p.salaire_mensuel_reference, "du": p.du,
               "calcul": p.calcul, "verse": p.verse}
    empreinte = hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    resume = {"organisation": org.nom, "date_depart": p.date_depart.isoformat(), "du": p.du,
              "assureur": c.assureur if c else None, "emis_le": aujourd_hui.isoformat(),
              "emetteur": rapport.nom_de(emetteur), "probant": config.probant}
    document = rapport.sceller_document(
        session, org, nature="fiche_de_calcul", empreinte=empreinte, resume=resume, config=config,
        gabarit="fiche_de_calcul.html", prestation_id=p.id, prefixe="FC",
        contexte=lambda numero, sceau: {
            "org": org, "p": p, "c": c, "numero": numero, "sceau": sceau, "empreinte": empreinte,
            "probant": config.probant, "emis_le": aujourd_hui, "emetteur": rapport.nom_de(emetteur),
            "url_verification": f"{config.url_publique}/verifier/{numero}"})
    journaliser(session, org.id, auteur, "prestation.fiche_de_calcul", p.id, {"numero": document.numero})
    return document
