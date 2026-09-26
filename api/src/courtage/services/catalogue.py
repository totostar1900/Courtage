"""Le catalogue anonyme des régimes : partager, retirer, consulter.

Partager est l'acte de la DRH, sur une version ADOPTÉE, avec son accord : une photographie part dans la table
publique `catalogue_regimes`, sans organisation ni personne ; le lien reste chez l'entreprise
(`partages_regime`, RLS). Une entreprise a au plus un partage actif. Consulter montre des groupes d'au moins
cinq entreprises (`courtage.catalogue`). Conception : docs/specs/2026-09-26-catalogue-anonyme-design.md.
"""
import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import mois_d_ifc
from courtage.catalogue import SECTEURS, SEUIL, TAILLES, Partage, anonymiser_categories, groupes_visibles
from courtage.db import EntreeCatalogue, Organisation, PartageRegime, RetraitCatalogue, VersionRegime
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.referentiel import CEMAC, BaremePaliers, BaremeTranches, referentiel_courant
from courtage.services import journaliser
from courtage.services.regimes import categories_de

ANCIENNETES = (10, 20, 30)
# Ce qui part d'une catégorie : ses règles, jamais son identifiant ni sa convention (dite par le groupe).
_CHAMPS = ("categorie", "bareme", "anciennete_minimale", "plafond_mois", "arrondi", "base_salaire", "avec_primes",
           "evenements")


def empreinte(organisation_id: uuid.UUID) -> str:
    """Compter les entreprises distinctes sans les nommer : jamais servie, et un identifiant d'organisation
    est un UUID aléatoire que personne d'autre ne connaît."""
    return hashlib.sha256(f"catalogue:{organisation_id}".encode()).hexdigest()


def _actifs(session: Session) -> list[EntreeCatalogue]:
    retires = select(RetraitCatalogue.partage_id)
    return list(session.scalars(select(EntreeCatalogue).where(EntreeCatalogue.id.not_in(retires))))


def _retirer_actifs(session: Session, org: Organisation) -> None:
    retires = select(RetraitCatalogue.partage_id)
    for pid in session.scalars(select(PartageRegime.partage_id).where(
            PartageRegime.organisation_id == org.id, PartageRegime.partage_id.not_in(retires))):
        session.add(RetraitCatalogue(partage_id=pid))
    session.flush()


def partager(session: Session, org: Organisation, version: VersionRegime, auteur: uuid.UUID, *,
             secteur: str, taille: str) -> PartageRegime:
    if org.pays not in CEMAC:
        raise ErreurMetier("hors_cemac", "Le catalogue réunit pour l'instant les régimes des pays de la CEMAC.", 422)
    if version.statut != "adoptee":
        raise ErreurMetier("version_non_adoptee", "Seule une version adoptée se partage : un projet n'est le "
                           "régime de personne.", 409)
    if secteur not in SECTEURS or taille not in TAILLES:
        raise ErreurMetier("requete_invalide", "Secteur ou taille inconnus.", 422)
    categories = categories_de(session, version)
    principale = next((c for c in categories if c.categorie == "*"), categories[0])
    _retirer_actifs(session, org)                       # une entreprise, un partage actif
    entree = EntreeCatalogue(
        empreinte=empreinte(org.id), pays=org.pays, secteur=secteur, taille=taille,
        convention_code=principale.convention_code, annee=version.en_vigueur_du.year,
        categories=anonymiser_categories([{k: getattr(c, k) for k in _CHAMPS} for c in categories]))
    session.add(entree)
    session.flush()
    lien = PartageRegime(organisation_id=org.id, version_id=version.id, partage_id=entree.id, partage_par=auteur)
    session.add(lien)
    session.flush()
    journaliser(session, org.id, auteur, "regime.partage", version.id, {"partage_id": str(entree.id)})
    return lien


def retirer(session: Session, org: Organisation, partage_id: uuid.UUID, auteur: uuid.UUID) -> None:
    lien = session.scalars(select(PartageRegime).where(PartageRegime.partage_id == partage_id,
                                                       PartageRegime.organisation_id == org.id)).first()
    if lien is None:
        raise Introuvable("Partage")
    if session.get(RetraitCatalogue, partage_id) is None:
        session.add(RetraitCatalogue(partage_id=partage_id))
        session.flush()
        journaliser(session, org.id, auteur, "regime.partage_retire", lien.version_id, {"partage_id": str(partage_id)})


def _partages(entrees: list[EntreeCatalogue]) -> list[Partage]:
    return [Partage(id=str(e.id), empreinte=e.empreinte, pays=e.pays, secteur=e.secteur, taille=e.taille,
                    convention_code=e.convention_code, categories=e.categories) for e in entrees]


def partages_de(session: Session, org: Organisation) -> list[dict]:
    """Ce que l'entreprise a partagé : actif ou retiré, et s'il se voit déjà dans le catalogue."""
    visibles = {m.id for _, membres in groupes_visibles(_partages(_actifs(session))) for m in membres}
    liens = session.scalars(select(PartageRegime).where(PartageRegime.organisation_id == org.id)
                            .order_by(PartageRegime.partage_le.desc()))
    return [{"partage_id": str(l.partage_id), "version_id": str(l.version_id), "partage_le": l.partage_le.isoformat(),
             "actif": session.get(RetraitCatalogue, l.partage_id) is None,
             "visible": str(l.partage_id) in visibles} for l in liens]


def _bareme(b: dict):
    return (BaremeTranches if b["forme"] == "tranches_cumulatives" else BaremePaliers).model_validate(b)


def _entree(p: Partage, attributs: dict, jour: date) -> dict:
    # La convention dit le secteur : elle ne se montre que si le groupe montre le secteur.
    convention_visible = "secteur" in attributs
    principale = next((c for c in p.categories if c["categorie"] == "*"), p.categories[0])
    try:
        minimum = mois_d_ifc(referentiel_courant().convention(p.convention_code, jour).bareme, 20)
        ecart = mois_d_ifc(_bareme(principale["bareme"]), 20) / minimum - 1 if minimum else None
    except LookupError:
        ecart = None
    return {
        "id": p.id, "convention_code": p.convention_code if convention_visible else None,
        "ecart_convention_20_ans": ecart,
        "illustration": [{"anciennete": n, "par_categorie": {c["categorie"]: round(mois_d_ifc(_bareme(c["bareme"]), n), 2)
                                                             for c in p.categories}} for n in ANCIENNETES],
        "categories": p.categories,
    }


def consulter(session: Session, jour: date | None = None) -> dict:
    jour = jour or date.today()
    actifs = _partages(_actifs(session))
    groupes = []
    for attributs, membres in groupes_visibles(actifs):
        entrees = sorted((_entree(p, attributs, jour) for p in membres),
                         key=lambda e: -(e["ecart_convention_20_ans"] or 0))     # jamais l'ordre du partage
        groupes.append({
            **{k: attributs.get(k) for k in ("pays", "secteur", "taille")},
            "libelle": " · ".join(([SECTEURS[attributs["secteur"]]] if "secteur" in attributs else [])
                                  + [CEMAC[attributs["pays"]] if "pays" in attributs else "Afrique centrale (CEMAC)"]
                                  + ([TAILLES[attributs["taille"]]] if "taille" in attributs else [])),
            "entreprises": len({m.empreinte for m in membres}), "regimes": entrees,
        })
    return {"seuil": SEUIL, "entreprises": len({p.empreinte for p in actifs}), "groupes": groupes,
            "secteurs": SECTEURS, "tailles": TAILLES}
