"""Barèmes d'entreprise : proposés par le client ou le conseiller, validés par le conseiller.

Un barème d'entreprise améliore une convention précise, et jamais ne la
diminue : c'est vérifié à la proposition contre la version de la convention
alors en vigueur, puis à chaque étude contre la version en vigueur à la date
d'évaluation, parce que le minimum légal monte avec le temps (commerce
camerounais, 16/01/2024).
"""
import uuid
from datetime import date, datetime, timezone

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import comparer_baremes
from courtage.db import BaremeEntreprise, Organisation
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.referentiel import Bareme, referentiel_courant

from . import journaliser

_BAREME = TypeAdapter(Bareme)


def type_de(bareme: dict) -> Bareme:
    return _BAREME.validate_python(bareme)


def proposer(session: Session, org: Organisation, auteur: uuid.UUID, *, libelle: str, fondement: str,
             document_reference: str, convention_code: str, en_vigueur_du: date, en_vigueur_au: date | None,
             bareme: dict) -> BaremeEntreprise:
    try:
        type_bareme = type_de(bareme)
    except ValidationError as e:
        raise ErreurMetier("bareme_mal_forme", "Barème mal formé.", 422, {"erreurs": e.errors(include_url=False)}) from None
    try:
        convention = referentiel_courant().convention(convention_code, en_vigueur_du)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None
    if convention.pays != org.pays:
        raise ErreurMetier("convention_autre_pays", f"{convention.code} n'est pas une convention de {org.pays}.", 422)
    en_dessous = comparer_baremes(type_bareme, convention.bareme)
    if en_dessous:
        raise ErreurMetier("bareme_inferieur_convention",
                           f"Le barème donne moins que la convention à partir de {en_dessous[0]} ans d'ancienneté : "
                           "une entreprise peut verser plus que sa convention, jamais moins.", 422,
                           {"anciennetes": en_dessous})
    b = BaremeEntreprise(organisation_id=org.id, libelle=libelle.strip(), fondement=fondement,
                         document_reference=document_reference.strip(), convention_code=convention.code,
                         en_vigueur_du=en_vigueur_du, en_vigueur_au=en_vigueur_au,
                         bareme=type_bareme.model_dump(mode="json"), propose_par=auteur)
    session.add(b)
    session.flush()
    journaliser(session, org.id, auteur, "bareme.propose", b.id, {"libelle": b.libelle, "convention": convention.code})
    return b


def valider(session: Session, b: BaremeEntreprise, auteur: uuid.UUID) -> BaremeEntreprise:
    if b.statut == "valide":
        raise ErreurMetier("bareme_deja_valide", "Ce barème est déjà validé.", 409)
    b.statut, b.valide_par, b.valide_le = "valide", auteur, datetime.now(timezone.utc)
    session.flush()
    journaliser(session, b.organisation_id, auteur, "bareme.valide", b.id)
    return b


def obtenir(session: Session, bareme_id: uuid.UUID) -> BaremeEntreprise:
    b = session.get(BaremeEntreprise, bareme_id)
    if b is None:
        raise Introuvable("Barème")
    return b


def lister(session: Session) -> list[BaremeEntreprise]:
    return list(session.scalars(select(BaremeEntreprise).order_by(BaremeEntreprise.en_vigueur_du.desc())))


def en_clair(b: BaremeEntreprise) -> dict:
    return {
        "id": str(b.id), "libelle": b.libelle, "fondement": b.fondement, "document_reference": b.document_reference,
        "convention_code": b.convention_code, "en_vigueur_du": b.en_vigueur_du.isoformat(),
        "en_vigueur_au": b.en_vigueur_au.isoformat() if b.en_vigueur_au else None, "bareme": b.bareme,
        "statut": b.statut, "valide_le": b.valide_le.isoformat() if b.valide_le else None,
    }
