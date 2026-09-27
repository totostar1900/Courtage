"""Régimes IFC : ce que l'entreprise verse, par catégorie de personnel, version après version.

La plateforme prend un régime TEL QUEL : un régime moins favorable que sa
convention est enregistré et signalé, jamais refusé. L'entreprise l'adopte
d'un seul acte ; si le régime n'est pas conforme, l'acte dit qu'elle l'a vu.
Le moteur retient toujours le plus favorable du régime et du plancher.

Une version est un **brouillon** (`analyse`) ou une version **adoptée**, rien d'autre :
- le brouillon se modifie sur place, se duplique, s'analyse, s'adopte ; il se supprime, et ses études en brouillon
  partent avec lui ;
- adoptée, elle est figée parce qu'elle a été communiquée (notes aux salariés et aux assureurs). Pour la changer, on
  la duplique en brouillon. Elle se supprime tant que rien ne la cite : une étude émise, un cahier des charges, un
  partage au catalogue ou une note émise la retiennent.
Les dates (s'applique depuis, à partir de, remplacée le) sont une information, pas un statut : `application`.
Conception : docs/specs/2026-09-27-versions-de-regime-design.md.
"""
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import Regles, mois_dus
from courtage.db import (CategorieRegime, Document, Etude, FicheRegime, Organisation, PartageRegime, Regime,
                         VersionRegime)
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
    _valider_categories(org, categories, en_vigueur_du)

    numero = (session.scalar(select(func.max(VersionRegime.numero)).where(VersionRegime.regime_id == regime.id)) or 0) + 1
    version = VersionRegime(organisation_id=org.id, regime_id=regime.id, numero=numero, en_vigueur_du=en_vigueur_du,
                            fondement=fondement, document_reference=document_reference.strip(), note=note,
                            cree_par=auteur)
    session.add(version)
    session.flush()
    _ajouter_categories(session, org, version, categories)
    journaliser(session, org.id, auteur, "regime.version_creee", version.id, {"regime_id": str(regime.id), "numero": numero})
    return version


def adopter(session: Session, version: VersionRegime, auteur: uuid.UUID, accepte_non_conformite: bool) -> VersionRegime:
    """L'entreprise adopte, d'un seul acte. Une non-conformité doit avoir été vue."""
    if version.statut == "adoptee":
        raise ErreurMetier("version_deja_adoptee", "Cette version est déjà adoptée.", 409)
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


JOURS_SANS_DECISION = 90      # au-delà, un brouillon est proposé au ménage


def etudes_de(session: Session, version: VersionRegime) -> int:
    return session.scalar(select(func.count()).select_from(Etude).where(Etude.regime_version_id == version.id)) or 0


def citations(session: Session, version: VersionRegime) -> dict:
    """Ce qui cite une version : les études (émises, qui la retiennent ; en brouillon, qui partent avec elle), les
    cahiers des charges, les partages au catalogue, les notes émises."""
    etudes = session.execute(select(Etude.id, Etude.statut, Etude.date_evaluation)
                             .where(Etude.regime_version_id == version.id)).all()
    compter = lambda modele, colonne: session.scalar(  # noqa: E731
        select(func.count()).select_from(modele).where(colonne == version.id)) or 0
    return {
        "etudes_emises": sum(1 for e in etudes if e.statut == "emise"),
        "brouillons": [{"id": str(e.id), "date_evaluation": e.date_evaluation.isoformat()}
                       for e in etudes if e.statut == "brouillon"],
        "cahiers": compter(FicheRegime, FicheRegime.regime_version_id),
        "partages": compter(PartageRegime, PartageRegime.version_id),
        "notes": compter(Document, Document.version_id),
    }


def suppression(session: Session, version: VersionRegime, c: dict | None = None) -> dict:
    """Un brouillon se supprime toujours ; une version adoptée, tant que rien ne la cite (la DRH seule, avec un motif :
    c'est revenir sur sa décision). Les études en brouillon qui la citent partent avec elle."""
    c = c or citations(session, version)
    adoptee = version.statut == "adoptee"
    raisons = []
    for n, un, plusieurs in ((c["etudes_emises"], "une étude émise", "études émises"),
                             (c["cahiers"], "un cahier des charges", "cahiers des charges"),
                             (c["notes"], "une note émise", "notes émises"),
                             (c["partages"], "un partage au catalogue", "partages au catalogue")):
        if n:
            raisons.append(un if n == 1 else f"{n} {plusieurs}")
    if raisons:
        return {"possible": False, "reservee_entreprise": adoptee, "brouillons": len(c["brouillons"]),
                "raison": "Citée par " + ", ".join(raisons) + " : elle reste."}
    return {"possible": True, "reservee_entreprise": adoptee, "brouillons": len(c["brouillons"]), "raison": None}


def supprimer(session: Session, version: VersionRegime, auteur: uuid.UUID, role: str, motif: str | None = None) -> bool:
    """Supprime la version (et ses études en brouillon) ; son régime aussi s'il reste sans version. Rend vrai si le
    régime est parti avec."""
    c = citations(session, version)
    s = suppression(session, version, c)
    if not s["possible"]:
        raise ErreurMetier("version_citee", s["raison"], 409)
    if s["reservee_entreprise"]:
        if role != "admin_client":
            raise ErreurMetier("acces_refuse", "Supprimer une version adoptée, c'est revenir sur la décision de "
                                               "l'entreprise : l'administrateur de l'entreprise seul le peut.", 403)
        if not (motif or "").strip():
            raise ErreurMetier("motif_requis", "Dire pourquoi la version adoptée est supprimée.", 422)
    from . import etudes as service_etudes
    for b in c["brouillons"]:
        service_etudes.supprimer(session, session.get(Etude, uuid.UUID(b["id"])), auteur)
    regime_id, numero, statut = version.regime_id, version.numero, version.statut
    session.delete(version)                      # ses catégories suivent (ON DELETE CASCADE)
    session.flush()
    journaliser(session, version.organisation_id, auteur, "regime.version_supprimee", version.id,
                {"regime_id": str(regime_id), "numero": numero, "statut": statut,
                 "brouillons": len(c["brouillons"]), "motif": (motif or "").strip() or None})
    reste = session.scalar(select(func.count()).select_from(VersionRegime).where(VersionRegime.regime_id == regime_id))
    if not reste:
        session.execute(delete(Regime).where(Regime.id == regime_id))
        journaliser(session, version.organisation_id, auteur, "regime.supprime", regime_id, {})
        return True
    return False


def modifier_brouillon(session: Session, org: Organisation, version: VersionRegime, auteur: uuid.UUID, *,
                       en_vigueur_du: date, fondement: str, document_reference: str, note: str | None,
                       categories: list[SaisieCategorie]) -> VersionRegime:
    """Un brouillon se corrige sur place, jusqu'à son adoption : une retouche n'ajoute pas une version."""
    if version.statut != "analyse":
        raise ErreurMetier("version_adoptee", "Une version adoptée ne se modifie plus : la dupliquer en brouillon.", 409)
    _valider_categories(org, categories, en_vigueur_du)
    version.en_vigueur_du, version.fondement = en_vigueur_du, fondement
    version.document_reference, version.note = document_reference.strip(), note
    session.execute(delete(CategorieRegime).where(CategorieRegime.version_id == version.id))
    session.flush()
    _ajouter_categories(session, org, version, categories)
    journaliser(session, org.id, auteur, "regime.version_modifiee", version.id, {"numero": version.numero})
    return version


def dupliquer(session: Session, org: Organisation, version: VersionRegime, auteur: uuid.UUID) -> VersionRegime:
    """Un nouveau brouillon, copie de la version : la façon de faire évoluer une version adoptée."""
    categories = [SaisieCategorie(
        categorie=c.categorie, convention_code=c.convention_code, bareme=c.bareme,
        anciennete_minimale=c.anciennete_minimale, plafond_mois=c.plafond_mois, arrondi=c.arrondi,
        base_salaire=c.base_salaire, avec_primes=c.avec_primes, evenements=tuple(c.evenements))
        for c in categories_de(session, version)]
    copie = nouvelle_version(session, org, session.get(Regime, version.regime_id), auteur,
                             en_vigueur_du=version.en_vigueur_du, fondement=version.fondement,
                             document_reference=version.document_reference, note=version.note, categories=categories)
    journaliser(session, org.id, auteur, "regime.version_dupliquee", copie.id, {"depuis": version.numero})
    return copie


def menage(session: Session, jour: date, role: str) -> list[dict]:
    """Ce qui peut partir, avec sa raison. Coché d'office : les brouillons sans décision depuis `JOURS_SANS_DECISION`
    jours. Une version adoptée que rien ne cite est proposée, jamais cochée (c'est revenir sur une décision), et à
    l'administrateur de l'entreprise seulement."""
    candidats = []
    for regime, versions in lister(session):
        for v in versions:
            c = citations(session, v)
            s = suppression(session, v, c)
            if not s["possible"] or (s["reservee_entreprise"] and role != "admin_client"):
                continue
            age = (jour - v.cree_le.date()).days
            if v.statut == "analyse":
                depuis = "créé aujourd'hui" if age < 1 else f"sans décision depuis {age} jour{'s' if age > 1 else ''}"
                raison, coche = f"brouillon {depuis}", age >= JOURS_SANS_DECISION
            else:
                raison, coche = f"adoptée le {v.adoptee_le:%d/%m/%Y}, citée par rien : revenir sur cette décision", False
            if c["brouillons"]:
                n = len(c["brouillons"])
                raison += f" ; {n} étude{'s' if n > 1 else ''} en brouillon {'partiront' if n > 1 else 'partira'} avec"
            candidats.append({"version_id": str(v.id), "regime": regime.nom, "numero": v.numero, "statut": v.statut,
                              "raison": raison, "coche": coche, "brouillons": c["brouillons"],
                              "motif_requis": s["reservee_entreprise"]})
    return candidats


def faire_le_menage(session: Session, auteur: uuid.UUID, role: str, version_ids: list[uuid.UUID],
                    motif: str | None) -> dict:
    retenus = {c["version_id"]: c for c in menage(session, date.today(), role)}
    inconnues = [str(i) for i in version_ids if str(i) not in retenus]
    if inconnues:
        raise ErreurMetier("hors_menage", "Certaines versions ne peuvent pas partir : " + ", ".join(inconnues), 409)
    brouillons = 0
    for i in version_ids:
        brouillons += len(retenus[str(i)]["brouillons"])
        supprimer(session, obtenir_version(session, i), auteur, role, motif)
    return {"versions": len(version_ids), "brouillons": brouillons}


def _nature_note(session: Session, numero: str) -> str | None:
    from courtage.db import Sceau
    nature = session.scalar(select(Sceau.nature).where(Sceau.numero == numero))
    return {"note_regime_salaries": "salaries", "note_regime_assureurs": "assureurs"}.get(nature)


def application(session: Session, version: VersionRegime, jour: date) -> dict | None:
    """Une information, pas un statut : depuis quand une version adoptée s'applique, à partir de quand, jusqu'à
    quand. Rien pour un brouillon."""
    if version.statut != "adoptee":
        return None
    relais = session.scalars(
        select(VersionRegime)
        .where(VersionRegime.regime_id == version.regime_id, VersionRegime.statut == "adoptee",
               VersionRegime.en_vigueur_du > version.en_vigueur_du)
        .order_by(VersionRegime.en_vigueur_du).limit(1)).first()
    return {"a_venir": version.en_vigueur_du > jour, "depuis": version.en_vigueur_du.isoformat(),
            "remplacee_le": relais.en_vigueur_du.isoformat() if relais else None,
            "remplacee_par": relais.numero if relais else None,
            "en_cours": version.en_vigueur_du <= jour and (relais is None or relais.en_vigueur_du > jour)}


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
        "application": application(session, version, date.today()),
        "etudes": etudes_de(session, version),
        "citations": (c := citations(session, version)),
        "suppression": suppression(session, version, c),
        "notes": {n: next((d.numero for d in session.scalars(select(Document).where(Document.version_id == version.id))
                           if _nature_note(session, d.numero) == n), None) for n in ("salaries", "assureurs")},
        "categories": [{
            "categorie": c.categorie, "convention_code": c.convention_code, "bareme": c.bareme,
            "anciennete_minimale": c.anciennete_minimale, "plafond_mois": c.plafond_mois, "arrondi": c.arrondi,
            "base_salaire": c.base_salaire, "avec_primes": c.avec_primes, "evenements": list(c.evenements),
        } for c in categories_de(session, version)],
        "constats": constats(session, version, jour or version.en_vigueur_du),
    }


# --- Interne ------------------------------------------------------------------

def _valider_categories(org: Organisation, categories: list[SaisieCategorie], jour: date) -> None:
    if not categories:
        raise ErreurMetier("regime_sans_categorie", "Un régime a au moins une catégorie (« * » pour tout le personnel).", 422)
    noms = [c.categorie.strip() for c in categories]
    if len(set(noms)) != len(noms):
        raise ErreurMetier("categorie_en_double", "Chaque catégorie n'apparaît qu'une fois.", 422)
    for c in categories:
        valider_categorie(org, c, jour)


def _ajouter_categories(session: Session, org: Organisation, version: VersionRegime,
                        categories: list[SaisieCategorie]) -> None:
    for c in categories:
        session.add(CategorieRegime(
            organisation_id=org.id, version_id=version.id, categorie=c.categorie.strip(),
            convention_code=c.convention_code, bareme=_BAREME.validate_python(c.bareme).model_dump(mode="json"),
            anciennete_minimale=c.anciennete_minimale, plafond_mois=c.plafond_mois, arrondi=c.arrondi,
            base_salaire=c.base_salaire, avec_primes=c.avec_primes, evenements=list(c.evenements)))
    session.flush()


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
