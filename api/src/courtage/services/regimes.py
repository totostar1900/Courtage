"""Régimes IFC : ce que l'entreprise verse, par catégorie de personnel, version après version.

La plateforme prend un régime TEL QUEL : un régime moins favorable que sa
convention est enregistré et signalé, jamais refusé. L'entreprise l'adopte
d'un seul acte ; si le régime n'est pas conforme, l'acte dit qu'elle l'a vu.
Le moteur retient toujours le plus favorable du régime et du plancher.

Le parcours d'une version (`etat_version`) :
- **projet** : enregistrée, pas adoptée. Elle se simule et s'étudie en brouillon ; aucune étude ne s'émet dessus.
  L'entreprise l'adopte ; ou on l'abandonne (motif) ; ou, si aucune étude ne s'en est servie, on la supprime.
- **à venir** : adoptée, sa date d'effet n'est pas arrivée.
- **en vigueur** : adoptée, la plus récente dont la date d'effet est passée. Les études s'appuient sur elle.
- **remplacée** : adoptée, puis relayée par une version adoptée plus récente, entrée en vigueur. Elle reste
  la base des études aux dates où elle s'appliquait.
- **abandonnée** : un projet non retenu. Elle reste lisible, avec son motif, et ne bouge plus.
Une version adoptée ne se supprime jamais : des études et des rapports scellés la citent.
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import Regles, mois_dus
from courtage.db import CategorieRegime, Etude, Organisation, Regime, VersionRegime
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.referentiel import Bareme, Convention, referentiel_courant

from . import journaliser

AUTRES = "*"
EVENEMENTS = {"retraite", "depart_anticipe", "licenciement_economique", "deces"}
ANCIENNETE_MAX_CONTROLEE = 50
_BAREME = TypeAdapter(Bareme)


@dataclass
class SaisieCategorie:
    categorie: str
    convention_code: str
    bareme: dict
    anciennete_minimale: int = 0
    plafond_mois: float | None = None
    arrondi: str = "annees"
    base_salaire: str = "dernier"
    avec_primes: bool = False
    evenements: tuple[str, ...] = ("retraite",)


# --- Écritures ----------------------------------------------------------------

def creer(session: Session, org: Organisation, auteur: uuid.UUID, nom: str) -> Regime:
    regime = Regime(organisation_id=org.id, nom=nom.strip(), cree_par=auteur)
    session.add(regime)
    session.flush()
    journaliser(session, org.id, auteur, "regime.cree", regime.id, {"nom": regime.nom})
    return regime


def nouvelle_version(session: Session, org: Organisation, regime: Regime, auteur: uuid.UUID, *,
                     en_vigueur_du: date, fondement: str, document_reference: str, note: str | None,
                     categories: list[SaisieCategorie]) -> VersionRegime:
    if not categories:
        raise ErreurMetier("regime_sans_categorie", "Un régime a au moins une catégorie (« * » pour tout le personnel).", 422)
    noms = [c.categorie.strip() for c in categories]
    if len(set(noms)) != len(noms):
        raise ErreurMetier("categorie_en_double", "Chaque catégorie n'apparaît qu'une fois.", 422)
    for c in categories:
        valider_categorie(org, c, en_vigueur_du)

    numero = (session.scalar(select(func.max(VersionRegime.numero)).where(VersionRegime.regime_id == regime.id)) or 0) + 1
    version = VersionRegime(organisation_id=org.id, regime_id=regime.id, numero=numero, en_vigueur_du=en_vigueur_du,
                            fondement=fondement, document_reference=document_reference.strip(), note=note,
                            cree_par=auteur)
    session.add(version)
    session.flush()
    for c in categories:
        session.add(CategorieRegime(
            organisation_id=org.id, version_id=version.id, categorie=c.categorie.strip(),
            convention_code=c.convention_code, bareme=_BAREME.validate_python(c.bareme).model_dump(mode="json"),
            anciennete_minimale=c.anciennete_minimale, plafond_mois=c.plafond_mois, arrondi=c.arrondi,
            base_salaire=c.base_salaire, avec_primes=c.avec_primes, evenements=list(c.evenements)))
    session.flush()
    journaliser(session, org.id, auteur, "regime.version_creee", version.id, {"regime_id": str(regime.id), "numero": numero})
    return version


def adopter(session: Session, version: VersionRegime, auteur: uuid.UUID, accepte_non_conformite: bool) -> VersionRegime:
    """L'entreprise adopte, d'un seul acte. Une non-conformité doit avoir été vue."""
    if version.statut == "adoptee":
        raise ErreurMetier("version_deja_adoptee", "Cette version est déjà adoptée.", 409)
    if version.statut == "abandonnee":
        raise ErreurMetier("version_abandonnee", "Cette version a été abandonnée : enregistrer une nouvelle version "
                                                 "pour la reprendre.", 409)
    releves = constats(session, version, version.en_vigueur_du)
    non_conforme = any(c["code"] == "sous_le_plancher" for c in releves)
    if non_conforme and not accepte_non_conformite:
        raise ErreurMetier("non_conformite_a_accepter",
                           "Ce régime donne moins que la convention collective pour certaines anciennetés. "
                           "Les salariés garderont droit au plancher, et l'évaluation le retiendra. "
                           "Confirmez que vous adoptez le régime en connaissance de cause.", 409,
                           {"constats": releves})
    version.statut = "adoptee"
    version.adoptee_par = auteur
    version.adoptee_le = datetime.now(timezone.utc)
    version.non_conformite_acceptee = non_conforme
    version.constats_a_l_adoption = releves
    session.flush()
    journaliser(session, version.organisation_id, auteur, "regime.version_adoptee", version.id,
                {"non_conformite_acceptee": non_conforme})
    return version


# --- Lectures -----------------------------------------------------------------

def obtenir_regime(session: Session, regime_id: uuid.UUID) -> Regime:
    r = session.get(Regime, regime_id)
    if r is None:
        raise Introuvable("Régime")
    return r


def obtenir_version(session: Session, version_id: uuid.UUID) -> VersionRegime:
    v = session.get(VersionRegime, version_id)
    if v is None:
        raise Introuvable("Version du régime")
    return v


def categories_de(session: Session, version: VersionRegime) -> list[CategorieRegime]:
    return list(session.scalars(select(CategorieRegime).where(CategorieRegime.version_id == version.id)
                                .order_by(CategorieRegime.categorie)))


def abandonner(session: Session, version: VersionRegime, auteur: uuid.UUID, motif: str) -> VersionRegime:
    """Un projet que l'entreprise ne retient pas : il reste lisible, avec son motif, et ne bouge plus."""
    if version.statut != "analyse":
        raise ErreurMetier("version_non_projet", "Seul un projet s'abandonne : une version adoptée se remplace par "
                                                 "une nouvelle version.", 409)
    if not (motif or "").strip():
        raise ErreurMetier("motif_requis", "Dire pourquoi ce projet n'est pas retenu.", 422)
    version.statut = "abandonnee"
    version.abandonnee_par = auteur
    version.abandonnee_le = datetime.now(timezone.utc)
    version.motif_abandon = motif.strip()
    session.flush()
    journaliser(session, version.organisation_id, auteur, "regime.version_abandonnee", version.id,
                {"motif": version.motif_abandon})
    return version


def etudes_de(session: Session, version: VersionRegime) -> int:
    return session.scalar(select(func.count()).select_from(Etude).where(Etude.regime_version_id == version.id)) or 0


def supprimer(session: Session, version: VersionRegime, auteur: uuid.UUID) -> bool:
    """Un projet dont aucune étude ne s'est servie disparaît ; son régime aussi s'il reste sans version.
    Rend vrai si le régime a été supprimé avec."""
    if version.statut != "analyse":
        raise ErreurMetier("version_non_projet", "Seul un projet se supprime. Une version adoptée est citée par des "
                                                 "études et des rapports : elle se remplace, elle ne disparaît pas.", 409)
    if n := etudes_de(session, version):
        raise ErreurMetier("version_utilisee", f"{n} étude{'s' if n > 1 else ''} s'appuie{'nt' if n > 1 else ''} sur "
                                               "ce projet : l'abandonner plutôt que le supprimer.", 409)
    regime_id, numero = version.regime_id, version.numero
    session.execute(delete(CategorieRegime).where(CategorieRegime.version_id == version.id))
    session.delete(version)
    session.flush()
    journaliser(session, version.organisation_id, auteur, "regime.version_supprimee", version.id,
                {"regime_id": str(regime_id), "numero": numero})
    reste = session.scalar(select(func.count()).select_from(VersionRegime).where(VersionRegime.regime_id == regime_id))
    if not reste:
        session.execute(delete(Regime).where(Regime.id == regime_id))
        journaliser(session, version.organisation_id, auteur, "regime.supprime", regime_id, {})
        return True
    return False


def etat_version(session: Session, version: VersionRegime, jour: date) -> dict:
    """Où en est la version au jour dit : projet, à venir, en vigueur, remplacée, abandonnée."""
    if version.statut == "abandonnee":
        return {"etat": "abandonnee"}
    if version.statut == "analyse":
        return {"etat": "projet"}
    if version.en_vigueur_du > jour:
        return {"etat": "a_venir"}
    relais = session.scalars(
        select(VersionRegime)
        .where(VersionRegime.regime_id == version.regime_id, VersionRegime.statut == "adoptee",
               VersionRegime.en_vigueur_du > version.en_vigueur_du, VersionRegime.en_vigueur_du <= jour)
        .order_by(VersionRegime.en_vigueur_du).limit(1)).first()
    if relais is None:
        return {"etat": "en_vigueur"}
    return {"etat": "remplacee", "remplacee_par": relais.numero, "jusqu_au": relais.en_vigueur_du.isoformat()}


def version_en_vigueur(session: Session, regime_id: uuid.UUID, jour: date) -> VersionRegime | None:
    """La dernière version adoptée dont la date d'effet précède le jour."""
    return session.scalars(
        select(VersionRegime)
        .where(VersionRegime.regime_id == regime_id, VersionRegime.statut == "adoptee",
               VersionRegime.en_vigueur_du <= jour)
        .order_by(VersionRegime.en_vigueur_du.desc()).limit(1)).first()


def lister(session: Session) -> list[tuple[Regime, list[VersionRegime]]]:
    regimes = session.scalars(select(Regime).order_by(Regime.cree_le)).all()
    return [(r, list(session.scalars(select(VersionRegime).where(VersionRegime.regime_id == r.id)
                                     .order_by(VersionRegime.numero)))) for r in regimes]


# --- Règles et constats -------------------------------------------------------

def regles(session: Session, version: VersionRegime, date_evaluation: date) -> dict[str, Regles]:
    """Les règles du moteur, chaque catégorie avec pour plancher la convention en vigueur à la date."""
    ref = referentiel_courant()
    resultat = {}
    for c in categories_de(session, version):
        try:
            convention = ref.convention(c.convention_code, date_evaluation)
        except LookupError as e:
            raise ErreurMetier("convention_introuvable", str(e), 422) from None
        resultat[c.categorie] = regles_de(c, convention)
    return resultat


def regles_plancher(session: Session, version: VersionRegime, date_evaluation: date) -> dict[str, Regles]:
    """La convention seule, catégorie par catégorie : ce que coûterait le plancher."""
    ref = referentiel_courant()
    return {c.categorie: Regles(bareme=ref.convention(c.convention_code, date_evaluation).bareme)
            for c in categories_de(session, version)}


def conventions_de(session: Session, version: VersionRegime, jour: date) -> list[Convention]:
    ref = referentiel_courant()
    return [ref.convention(code, jour) for code in sorted({c.convention_code for c in categories_de(session, version)})]


def constats(session: Session, version: VersionRegime, jour: date) -> list[dict]:
    """Ce que la plateforme relève sur une version, face aux conventions en vigueur au jour dit."""
    return constats_categories(categories_de(session, version), jour)


def constats_categories(categories, jour: date) -> list[dict]:
    """Les constats de légalité de catégories — enregistrées ou simplement saisies (simulation)."""
    ref = referentiel_courant()
    releves = []
    for c in categories:
        try:
            convention = ref.convention(c.convention_code, jour)
        except LookupError:
            releves.append(_constat("bloque", "convention_introuvable", c.categorie,
                                    f"Aucune version de {c.convention_code} en vigueur le {jour:%d/%m/%Y}."))
            continue
        regles_c = regles_de(c, convention)
        sous = [n for n in range(ANCIENNETE_MAX_CONTROLEE + 1) if mois_dus(regles_c, n)[1]]
        if sous:
            # « Attention », pas « Bloquant » : le régime s'enregistre et s'adopte tel quel, en connaissance de cause.
            releves.append(_constat(
                "avertit", "sous_le_plancher", c.categorie,
                f"{_libelle(c.categorie)} : le régime donne moins que {convention.libelle} "
                f"pour {_plages(sous)} d'ancienneté. Les salariés gardent droit au plancher.",
                {"anciennetes": sous, "convention": convention.code}))
        if c.base_salaire == "moyenne_12_mois":
            releves.append(_constat("avertit", "base_salaire_approchee", c.categorie,
                                    f"{_libelle(c.categorie)} : la base est la moyenne des 12 derniers mois ; "
                                    "l'évaluation retient le salaire courant du fichier."))
        autres = sorted(set(c.evenements) - {"retraite"})
        if autres:
            releves.append(_constat("avertit", "evenements_non_evalues", c.categorie,
                                    f"{_libelle(c.categorie)} : le régime couvre aussi {', '.join(autres)}, "
                                    "que l'évaluation ne chiffre pas encore.", {"evenements": autres}))
    return releves


def en_clair(session: Session, version: VersionRegime, jour: date | None = None) -> dict:
    regime = session.get(Regime, version.regime_id)
    return {
        "id": str(version.id), "regime_id": str(regime.id), "nom": regime.nom, "numero": version.numero,
        "en_vigueur_du": version.en_vigueur_du.isoformat(), "fondement": version.fondement,
        "document_reference": version.document_reference, "note": version.note, "statut": version.statut,
        "adoptee_le": version.adoptee_le.isoformat() if version.adoptee_le else None,
        "non_conformite_acceptee": version.non_conformite_acceptee,
        **etat_version(session, version, date.today()),
        "abandonnee_le": version.abandonnee_le.isoformat() if version.abandonnee_le else None,
        "motif_abandon": version.motif_abandon,
        "etudes": etudes_de(session, version),
        "categories": [{
            "categorie": c.categorie, "convention_code": c.convention_code, "bareme": c.bareme,
            "anciennete_minimale": c.anciennete_minimale, "plafond_mois": c.plafond_mois, "arrondi": c.arrondi,
            "base_salaire": c.base_salaire, "avec_primes": c.avec_primes, "evenements": list(c.evenements),
        } for c in categories_de(session, version)],
        "constats": constats(session, version, jour or version.en_vigueur_du),
    }


# --- Interne ------------------------------------------------------------------

def valider_categorie(org: Organisation, c: SaisieCategorie, jour: date) -> None:
    try:
        _BAREME.validate_python(c.bareme)
    except ValidationError as e:
        raise ErreurMetier("bareme_mal_forme", f"Catégorie « {c.categorie} » : barème mal formé.", 422,
                           {"erreurs": e.errors(include_url=False)}) from None
    try:
        convention = referentiel_courant().convention(c.convention_code, jour)
    except LookupError as e:
        raise ErreurMetier("convention_introuvable", str(e), 422) from None
    if convention.pays != org.pays:
        raise ErreurMetier("convention_autre_pays", f"{convention.code} n'est pas une convention de {org.pays}.", 422)
    if "retraite" not in c.evenements or not set(c.evenements) <= EVENEMENTS:
        raise ErreurMetier("evenements_invalides",
                           f"Événements admis : {', '.join(sorted(EVENEMENTS))} ; la retraite est toujours couverte.", 422)


def regles_de(c, convention: Convention) -> Regles:
    """Les règles du moteur pour une catégorie (enregistrée ou saisie), la convention pour plancher."""
    return Regles(bareme=_BAREME.validate_python(c.bareme), plancher=Regles(bareme=convention.bareme),
                  anciennete_minimale=c.anciennete_minimale, plafond_mois=c.plafond_mois, arrondi=c.arrondi)


def _libelle(categorie: str) -> str:
    return "Tout le personnel" if categorie == AUTRES else f"Catégorie « {categorie} »"


def _constat(niveau: str, code: str, categorie: str, message: str, details: dict | None = None) -> dict:
    return {"niveau": niveau, "code": code, "categorie": categorie, "message": message, "details": details or {}}


def _plages(anciennetes: list[int]) -> str:
    """[3, 4, 5, 9] → « 3 à 5 ans, 9 ans »."""
    plages, debut = [], anciennetes[0]
    for avant, n in zip(anciennetes, anciennetes[1:] + [None]):
        if n != avant + 1:
            plages.append(f"{debut} à {avant} ans" if debut != avant else f"{avant} ans")
            debut = n
    return ", ".join(plages)
