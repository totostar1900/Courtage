"""Routes de l'API. Les droits se lisent sur la signature : `acces(...)` nomme les rôles admis."""
import unicodedata
import uuid
from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.auth.telephone import normaliser
from courtage.db import Adhesion, Organisation, ReponseFiche, Utilisateur, contexte
from courtage.erreurs import ErreurMetier
from courtage.financement import Offre, Scenario
from courtage.services import analyse, contrats, dossiers, etudes, extractions, orientation, reponses, prestations, fiches, financement, fichiers, journaliser, rapport, regimes, remuneration, simulation

from . import Acces, acces, identite, session_db
from .limites import limite

routeur = APIRouter()

CLIENT = ("admin_client", "conseiller")      # déposer, lancer une étude, décrire un régime
ENTREPRISE = ("admin_client",)               # adopter son régime : l'entreprise est souveraine
CONSEIL = ("conseiller",)                    # émettre, fixer la rémunération
TOUS: tuple[str, ...] = ()                   # lire


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Moi, organisations, adhésions --------------------------------------------

@routeur.get("/moi")
def moi(session: Session = Depends(session_db), utilisateur: Utilisateur = Depends(identite)):
    rangs = session.execute(
        select(Organisation, Adhesion.role).join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == utilisateur.id).order_by(Organisation.nom)).all()
    return {
        "id": str(utilisateur.id), "email": utilisateur.email, "telephone": utilisateur.telephone,
        "admin_plateforme": utilisateur.admin_plateforme,
        "organisations": [{"id": str(o.id), "nom": o.nom, "pays": o.pays, "role": r} for o, r in rangs],
    }


class NouvelleOrganisation(_Corps):
    nom: str = Field(min_length=1)
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    secteur: str | None = None


@routeur.post("/organisations", status_code=201)
def creer_organisation(corps: NouvelleOrganisation, session: Session = Depends(session_db),
                       utilisateur: Utilisateur = Depends(identite)):
    if not utilisateur.admin_plateforme:
        raise ErreurMetier("acces_refuse", "Seule la plateforme ouvre un dossier client.", 403)
    org = Organisation(nom=corps.nom.strip(), pays=corps.pays, secteur=corps.secteur)
    session.add(org)
    session.flush()
    journaliser(session, None, utilisateur.id, "organisation.creee", org.id, {"nom": org.nom, "pays": org.pays})
    return {"id": str(org.id), "nom": org.nom, "pays": org.pays, "secteur": org.secteur}


class NouvelleAdhesion(_Corps):
    utilisateur_id: uuid.UUID
    role: Literal["admin_client", "lecteur_client", "conseiller"]


@routeur.post("/organisations/{organisation_id}/adhesions", status_code=201)
def ajouter_adhesion(organisation_id: uuid.UUID, corps: NouvelleAdhesion, session: Session = Depends(session_db),
                     utilisateur: Utilisateur = Depends(identite)):
    role_appelant = session.scalar(select(Adhesion.role).where(
        Adhesion.utilisateur_id == utilisateur.id, Adhesion.organisation_id == organisation_id))
    if not (utilisateur.admin_plateforme or role_appelant == "conseiller"):
        raise ErreurMetier("acces_refuse", "Seuls la plateforme et le conseiller du dossier ajoutent un membre.", 403)
    if session.get(Organisation, organisation_id) is None or session.get(Utilisateur, corps.utilisateur_id) is None:
        raise ErreurMetier("introuvable", "Organisation ou utilisateur introuvable.", 404)
    if session.get(Adhesion, (corps.utilisateur_id, organisation_id)) is not None:
        raise ErreurMetier("deja_membre", "Cet utilisateur est déjà membre de l'organisation.", 409)
    session.add(Adhesion(utilisateur_id=corps.utilisateur_id, organisation_id=organisation_id, role=corps.role))
    adhesion = {"utilisateur_id": str(corps.utilisateur_id), "role": corps.role}
    contexte(session.connection(), organisation_id)
    journaliser(session, organisation_id, utilisateur.id, "adhesion.ajoutee", corps.utilisateur_id, adhesion)
    return adhesion


@routeur.get("/organisations/{organisation_id}/equipe")
def equipe(a: Acces = Depends(acces(*TOUS))):
    """Qui suit le dossier : le client voit son conseiller, et le conseiller ses interlocuteurs."""
    rangs = a.session.execute(select(Utilisateur, Adhesion.role).join(Adhesion, Adhesion.utilisateur_id == Utilisateur.id)
                              .where(Adhesion.organisation_id == a.organisation.id)).all()
    return [{"id": str(u.id), "nom": u.nom_affiche or u.email or u.telephone, "email": u.email,
             "telephone": u.telephone, "role": r} for u, r in rangs]


class NouveauMembre(_Corps):
    telephone: str = Field(min_length=1, max_length=30)
    nom_affiche: str = Field(min_length=1)
    role: Literal["admin_client", "lecteur_client", "conseiller"]


@routeur.post("/organisations/{organisation_id}/membres", status_code=201)
def inscrire_membre(organisation_id: uuid.UUID, corps: NouveauMembre, session: Session = Depends(session_db),
                    utilisateur: Utilisateur = Depends(identite)):
    """Inscrire quelqu'un par son numéro : il se connectera avec le code qu'il recevra."""
    role_appelant = session.scalar(select(Adhesion.role).where(
        Adhesion.utilisateur_id == utilisateur.id, Adhesion.organisation_id == organisation_id))
    if not (utilisateur.admin_plateforme or role_appelant == "conseiller"):
        raise ErreurMetier("acces_refuse", "Seuls la plateforme et le conseiller du dossier inscrivent un membre.", 403)
    if session.get(Organisation, organisation_id) is None:
        raise ErreurMetier("introuvable", "Organisation introuvable.", 404)
    try:
        telephone = normaliser(corps.telephone)
    except ValueError:
        raise ErreurMetier("telephone_invalide", "Numéro de téléphone invalide.", 422) from None
    membre = session.scalars(select(Utilisateur).where(Utilisateur.telephone == telephone)).first()
    if membre is None:
        membre = Utilisateur(telephone=telephone, nom_affiche=corps.nom_affiche.strip())
        session.add(membre)
        session.flush()
    if session.get(Adhesion, (membre.id, organisation_id)) is not None:
        raise ErreurMetier("deja_membre", "Cette personne est déjà membre du dossier.", 409)
    session.add(Adhesion(utilisateur_id=membre.id, organisation_id=organisation_id, role=corps.role))
    contexte(session.connection(), organisation_id)
    journaliser(session, organisation_id, utilisateur.id, "membre.inscrit", membre.id, {"role": corps.role})
    return {"utilisateur_id": str(membre.id), "telephone": telephone, "role": corps.role}


# --- Rémunération -------------------------------------------------------------

class NouvellesConditions(_Corps):
    en_vigueur_du: date
    mode: Literal["honoraires", "commission", "mixte"]
    honoraires_etude_ifc: int = Field(default=0, ge=0)
    honoraires_par_salarie: int = Field(default=0, ge=0)
    commission_bps: int = Field(default=0, ge=0, le=10000)
    note: str | None = None


@routeur.post("/organisations/{organisation_id}/remuneration", status_code=201)
def fixer_remuneration(corps: NouvellesConditions, a: Acces = Depends(acces(*CONSEIL))):
    c = remuneration.fixer(a.session, a.organisation.id, a.utilisateur.id, **corps.model_dump())
    return remuneration.en_clair(c)


@routeur.get("/organisations/{organisation_id}/remuneration")
def lire_remuneration(a: Acces = Depends(acces(*TOUS))):
    courantes = remuneration.en_vigueur(a.session, date.today())
    return {
        "en_vigueur": remuneration.en_clair(courantes) if courantes else None,
        "historique": [remuneration.en_clair(c) for c in remuneration.historique(a.session)],
    }


# --- Contrats : courtage ou comparaison --------------------------------------------

class NouveauContrat(_Corps):
    en_vigueur_du: date
    service: Literal["courtage", "comparaison"]
    assureur: str | None = Field(default=None, max_length=200)
    numero_police: str | None = Field(default=None, max_length=100)
    date_effet_police: date | None = None
    mandat_reference: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=2000)


@routeur.post("/organisations/{organisation_id}/contrats", status_code=201)
def enregistrer_contrat(corps: NouveauContrat, a: Acces = Depends(acces(*CONSEIL))):
    return contrats.en_clair(contrats.enregistrer(a.session, a.organisation.id, a.utilisateur.id, **corps.model_dump()))


@routeur.get("/organisations/{organisation_id}/contrats")
def lire_contrats(a: Acces = Depends(acces(*TOUS))):
    aujourd_hui = date.today()
    courant = contrats.service_a_la_date(a.session, aujourd_hui)
    return {
        "service": courant.service,
        "en_vigueur": contrats.en_clair(courant.contrat) if courant.contrat else None,
        "historique": [contrats.en_clair(c) for c in contrats.historique(a.session)],
        "constats": contrats.constats(a.session, aujourd_hui),
    }


# --- Prestations : un départ, sans identité ----------------------------------------------
# Aucun champ ne nomme une personne, et `extra="forbid"` refuse qu'on en ajoute un.

class NouvellePrestation(_Corps):
    matricule: str = Field(min_length=1, max_length=50)
    motif: Literal["retraite", "demission", "licenciement", "deces", "autre"]
    date_embauche: date
    date_depart: date
    salaire_mensuel_reference: int = Field(ge=0)
    categorie: str | None = Field(default=None, max_length=100)
    date_naissance: date | None = None
    verse: int | None = Field(default=None, ge=0)
    part_fonds_demandee: int | None = Field(default=None, ge=0)
    part_fonds_payee: int | None = Field(default=None, ge=0)
    payee_le: date | None = None
    soldee: bool = False
    note: str | None = Field(default=None, max_length=2000)
    convention_code: str | None = None

    def saisie(self) -> prestations.Saisie:
        return prestations.Saisie(**self.model_dump())


class CorrectionPrestation(NouvellePrestation):
    motif_correction: str = Field(max_length=500)


class AnnulationPrestation(_Corps):
    motif_correction: str = Field(max_length=500)


class PaiementDeclare(_Corps):
    part_fonds_demandee: int | None = Field(default=None, ge=0)
    part_fonds_payee: int = Field(gt=0)
    payee_le: date


@routeur.get("/organisations/{organisation_id}/prestations")
def lister_prestations(a: Acces = Depends(acces(*TOUS))):
    ps = prestations.actives(a.session)
    presences = prestations.presences(a.session)
    ouverts = dossiers.par_depart(a.session)

    def ligne(p):
        d = ouverts.get((p.matricule, p.date_depart))
        return {**prestations.en_clair(a.session, p, presences), "dossier": dossiers.resume(a.session, d) if d else None}
    return {"prestations": [ligne(p) for p in ps], "totaux": prestations.totaux(ps)}


@routeur.post("/organisations/{organisation_id}/prestations/apercu")
def apercu_prestation(corps: NouvellePrestation, a: Acces = Depends(acces(*CLIENT))):
    """Le dû et les constats d'une saisie, avant de l'enregistrer."""
    return prestations.apercu(a.session, corps.saisie())


@routeur.post("/organisations/{organisation_id}/prestations/import")
async def importer_prestations(fichier: UploadFile = File(...), convention_code: str | None = Form(default=None),
                               enregistrer: bool = Form(default=False), a: Acces = Depends(acces(*CLIENT))):
    r = prestations.importer(a.session, a.organisation, a.utilisateur.id, contenu=await fichier.read(),
                             nom_fichier=fichier.filename or "departs", convention_code=convention_code or None,
                             enregistrer_=enregistrer)
    return JSONResponse(r, status_code=201 if enregistrer else 200)


@routeur.post("/organisations/{organisation_id}/prestations", status_code=201)
def enregistrer_prestation(corps: NouvellePrestation, a: Acces = Depends(acces(*CLIENT))):
    p = prestations.enregistrer(a.session, a.organisation, a.utilisateur.id, corps.saisie())
    return prestations.en_clair(a.session, p)


@routeur.post("/organisations/{organisation_id}/prestations/{prestation_id}/correction", status_code=201)
def corriger_prestation(prestation_id: uuid.UUID, corps: CorrectionPrestation, a: Acces = Depends(acces(*CLIENT))):
    donnees = corps.model_dump()
    motif = donnees.pop("motif_correction")
    p = prestations.corriger(a.session, a.organisation, a.utilisateur.id, prestation_id,
                             prestations.Saisie(**donnees), motif)
    return prestations.en_clair(a.session, p)


@routeur.get("/organisations/{organisation_id}/prestations/{prestation_id}/orientation")
def orienter_prestation(prestation_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    return orientation.orienter(a.session, prestation_id)


@routeur.get("/organisations/{organisation_id}/prestations/{prestation_id}/fiche-de-calcul")
def fiche_de_calcul(prestation_id: uuid.UUID, request: Request, a: Acces = Depends(acces(*CLIENT))):
    d = orientation.fiche_de_calcul(a.session, a.organisation, a.utilisateur.id, prestation_id,
                                    request.app.state.sceau, date.today())
    return Response(d.contenu, media_type="application/pdf",
                    headers={**_piece_jointe(f"fiche-de-calcul-{d.numero}.pdf"), "X-Numero-Document": d.numero})


@routeur.post("/organisations/{organisation_id}/prestations/{prestation_id}/paiement", status_code=201)
def declarer_paiement(prestation_id: uuid.UUID, corps: PaiementDeclare, a: Acces = Depends(acces(*CLIENT))):
    p = prestations.declarer_paiement(a.session, a.organisation, a.utilisateur.id, prestation_id, **corps.model_dump())
    return prestations.en_clair(a.session, p)


@routeur.post("/organisations/{organisation_id}/prestations/{prestation_id}/annulation", status_code=201)
def annuler_prestation(prestation_id: uuid.UUID, corps: AnnulationPrestation, a: Acces = Depends(acces(*CLIENT))):
    p = prestations.annuler(a.session, a.organisation, a.utilisateur.id, prestation_id, corps.motif_correction)
    return prestations.en_clair(a.session, p)


# --- Courtage : dossiers de prise en charge -------------------------------------------------
# L'identité d'un bénéficiaire ne se lit que dans UN dossier, et seulement par l'entreprise et son
# conseiller ; aucune liste ne la porte. Chaque lecture efface d'abord ce qui est échu.

VOIENT_L_IDENTITE = ("admin_client", "conseiller")


class Identite(_Corps):
    qualite: Literal["salarie", "ayant_droit"] = "salarie"
    nom: str = Field(min_length=1, max_length=200)
    prenoms: str | None = Field(default=None, max_length=200)
    date_naissance: date | None = None
    piece_type: Literal["cni", "passeport", "carte_sejour", "autre"]
    piece_numero: str = Field(min_length=1, max_length=60)
    telephone: str | None = Field(default=None, max_length=30)
    moyen_paiement: Literal["virement", "mobile_money", "cheque"]
    coordonnees_paiement: str | None = Field(default=None, max_length=120)


class NouveauDossier(_Corps):
    prestation_id: uuid.UUID
    montant_demande: int = Field(gt=0)
    beneficiaire: Identite


class Verification(_Corps):
    conforme: bool
    motif: str | None = Field(default=None, max_length=1000)


class Transmission(_Corps):
    le: date | None = None


class Reponse(_Corps):
    paye: bool
    montant: int | None = Field(default=None, ge=0)
    le: date | None = None
    motif: str | None = Field(default=None, max_length=1000)


def _dossier(a: Acces, dossier_id: uuid.UUID, statut: int = 200):
    d = dossiers.obtenir(a.session, dossier_id)
    corps = dossiers.en_clair(a.session, d, voir_identite=a.role in VOIENT_L_IDENTITE, aujourd_hui=date.today())
    return JSONResponse(corps, status_code=statut)


@routeur.get("/organisations/{organisation_id}/dossiers")
def lister_dossiers(a: Acces = Depends(acces(*TOUS))):
    dossiers.effacer_echus(a.session, date.today())
    return [dossiers.en_clair(a.session, d, voir_identite=False, aujourd_hui=date.today())
            for d in dossiers.lister(a.session)]


@routeur.post("/organisations/{organisation_id}/dossiers")
def ouvrir_dossier(corps: NouveauDossier, a: Acces = Depends(acces(*ENTREPRISE))):
    d = dossiers.ouvrir(a.session, a.organisation, a.utilisateur.id, prestation_id=corps.prestation_id,
                        montant_demande=corps.montant_demande, beneficiaire=corps.beneficiaire.model_dump(),
                        aujourd_hui=date.today())
    return _dossier(a, d.id, 201)


@routeur.get("/organisations/{organisation_id}/dossiers/{dossier_id}")
def lire_dossier(dossier_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    dossiers.effacer_echus(a.session, date.today())
    return _dossier(a, dossier_id)


@routeur.post("/organisations/{organisation_id}/dossiers/{dossier_id}/pieces")
async def ajouter_piece(dossier_id: uuid.UUID, fichier: UploadFile = File(...), nature: str = Form(...),
                        a: Acces = Depends(acces(*CLIENT))):
    d = dossiers.obtenir(a.session, dossier_id)
    dossiers.ajouter_piece(a.session, a.organisation, a.utilisateur.id, d, nature=nature,
                           nom_fichier=fichier.filename or "piece", contenu=await fichier.read())
    return _dossier(a, dossier_id, 201)


@routeur.get("/organisations/{organisation_id}/dossiers/{dossier_id}/pieces/{piece_id}")
def telecharger_piece(dossier_id: uuid.UUID, piece_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    p = dossiers.piece(a.session, dossiers.obtenir(a.session, dossier_id), piece_id)
    return Response(p.contenu, media_type=p.type_contenu, headers=_piece_jointe(p.nom_fichier))


@routeur.get("/organisations/{organisation_id}/dossiers/{dossier_id}/document")
def telecharger_dossier(dossier_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    p = dossiers.document(a.session, dossiers.obtenir(a.session, dossier_id))
    return Response(p.contenu, media_type="application/pdf", headers=_piece_jointe(p.nom_fichier))


@routeur.post("/organisations/{organisation_id}/dossiers/{dossier_id}/verification")
def verifier_dossier(dossier_id: uuid.UUID, corps: Verification, a: Acces = Depends(acces(*CONSEIL))):
    dossiers.verifier(a.session, a.organisation, a.utilisateur.id, dossiers.obtenir(a.session, dossier_id),
                      conforme=corps.conforme, motif=corps.motif, aujourd_hui=date.today())
    return _dossier(a, dossier_id, 201)


@routeur.post("/organisations/{organisation_id}/dossiers/{dossier_id}/resoumission")
def resoumettre_dossier(dossier_id: uuid.UUID, a: Acces = Depends(acces(*ENTREPRISE))):
    dossiers.resoumettre(a.session, a.organisation, a.utilisateur.id, dossiers.obtenir(a.session, dossier_id),
                         date.today())
    return _dossier(a, dossier_id, 201)


@routeur.post("/organisations/{organisation_id}/dossiers/{dossier_id}/transmission")
def transmettre_dossier(dossier_id: uuid.UUID, corps: Transmission, request: Request,
                        a: Acces = Depends(acces(*CONSEIL))):
    dossiers.transmettre(a.session, a.organisation, a.utilisateur.id, dossiers.obtenir(a.session, dossier_id),
                         le=corps.le or date.today(), config=request.app.state.sceau, aujourd_hui=date.today())
    return _dossier(a, dossier_id, 201)


@routeur.post("/organisations/{organisation_id}/dossiers/{dossier_id}/reponse")
def repondre_dossier(dossier_id: uuid.UUID, corps: Reponse, a: Acces = Depends(acces(*CONSEIL))):
    dossiers.repondre(a.session, a.organisation, a.utilisateur.id, dossiers.obtenir(a.session, dossier_id),
                      paye=corps.paye, montant=corps.montant, le=corps.le or date.today(), motif=corps.motif)
    return _dossier(a, dossier_id, 201)


# --- Extraction assistée d'un texte existant ------------------------------------------------

@routeur.get("/extraction/mode")
def mode_extraction(request: Request, _: Utilisateur = Depends(identite)):
    return extractions.mode(request.app.state.extracteur)


@routeur.post("/organisations/{organisation_id}/regimes/extraction", status_code=201)
async def extraire_regime(request: Request, fichier: UploadFile = File(...), consentement: bool = Form(default=False),
                          a: Acces = Depends(acces(*CLIENT))):
    return extractions.pour_un_regime(a.session, a.organisation, a.utilisateur.id, request.app.state.extracteur,
                                      contenu=await fichier.read(), nom_fichier=fichier.filename or "texte",
                                      consentement=consentement)


@routeur.post("/referentiel/extraction")
async def extraire_convention(request: Request, fichier: UploadFile = File(...), pays: str = Form(...),
                              consentement: bool = Form(default=False), session: Session = Depends(session_db),
                              utilisateur: Utilisateur = Depends(identite)):
    if not utilisateur.admin_plateforme:
        raise ErreurMetier("acces_refuse", "Le référentiel se tient par la plateforme.", 403)
    return extractions.pour_le_referentiel(utilisateur.id, request.app.state.extracteur, session,
                                           contenu=await fichier.read(), nom_fichier=fichier.filename or "texte",
                                           consentement=consentement, pays=pays.strip().upper())


# --- Régimes ------------------------------------------------------------------

class NouveauRegime(_Corps):
    nom: str = Field(min_length=1)


class CategorieSaisie(_Corps):
    categorie: str = Field(min_length=1)
    convention_code: str
    bareme: dict
    anciennete_minimale: int = Field(default=0, ge=0)
    plafond_mois: float | None = Field(default=None, gt=0)
    arrondi: Literal["annees", "mois"] = "annees"
    base_salaire: Literal["dernier", "moyenne_12_mois"] = "dernier"
    avec_primes: bool = False
    evenements: list[str] = ["retraite"]


class NouvelleVersion(_Corps):
    en_vigueur_du: date
    fondement: Literal["accord_entreprise", "contrat_travail", "usage", "decision_direction"]
    document_reference: str = Field(min_length=1)
    note: str | None = None
    categories: list[CategorieSaisie]


class Adoption(_Corps):
    accepte_non_conformite: bool = False


@routeur.post("/organisations/{organisation_id}/regimes", status_code=201)
def creer_regime(corps: NouveauRegime, a: Acces = Depends(acces(*CLIENT))):
    r = regimes.creer(a.session, a.organisation, a.utilisateur.id, corps.nom)
    return {"id": str(r.id), "nom": r.nom, "versions": []}


@routeur.get("/organisations/{organisation_id}/regimes")
def lister_regimes(a: Acces = Depends(acces(*TOUS))):
    return [{"id": str(r.id), "nom": r.nom, "versions": [regimes.en_clair(a.session, v) for v in versions]}
            for r, versions in regimes.lister(a.session)]


# Chemins littéraux (« versions/… ») AVANT les chemins à paramètre du même routeur.
@routeur.get("/organisations/{organisation_id}/regimes/versions/{version_id}")
def lire_version(version_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    return regimes.en_clair(a.session, regimes.obtenir_version(a.session, version_id))


@routeur.get("/organisations/{organisation_id}/regimes/versions/{version_id}/analyse")
def analyser_version(version_id: uuid.UUID, fichier_id: uuid.UUID | None = None, date_evaluation: date | None = None,
                     a: Acces = Depends(acces(*TOUS))):
    """Légalité, nature, pièges ; et, avec un fichier du personnel, les coûts."""
    return analyse.analyser_version(a.session, a.organisation, regimes.obtenir_version(a.session, version_id),
                                    fichier_id=fichier_id, date_evaluation=date_evaluation)


@routeur.post("/organisations/{organisation_id}/regimes/versions/{version_id}/adoption")
def adopter_version(version_id: uuid.UUID, corps: Adoption, a: Acces = Depends(acces(*ENTREPRISE))):
    v = regimes.adopter(a.session, regimes.obtenir_version(a.session, version_id), a.utilisateur.id,
                        corps.accepte_non_conformite)
    return regimes.en_clair(a.session, v)


@routeur.post("/organisations/{organisation_id}/regimes/{regime_id}/versions", status_code=201)
def creer_version(regime_id: uuid.UUID, corps: NouvelleVersion, a: Acces = Depends(acces(*CLIENT))):
    v = regimes.nouvelle_version(
        a.session, a.organisation, regimes.obtenir_regime(a.session, regime_id), a.utilisateur.id,
        en_vigueur_du=corps.en_vigueur_du, fondement=corps.fondement, document_reference=corps.document_reference,
        note=corps.note, categories=[regimes.SaisieCategorie(**{**c.model_dump(), "evenements": tuple(c.evenements)})
                                     for c in corps.categories])
    return regimes.en_clair(a.session, v)


# --- Simulations ---------------------------------------------------------------

class VarianteSaisie(_Corps):
    nom: str = Field(min_length=1)
    regime_version_id: uuid.UUID | None = None
    categories: list[CategorieSaisie] | None = None


class ParametresSimulation(_Corps):
    fichier_id: uuid.UUID
    date_evaluation: date
    convention_code: str
    fonds_disponible: int = Field(default=0, ge=0)
    hypotheses: dict[str, float] = {}
    variantes: list[VarianteSaisie] = []


@routeur.post("/organisations/{organisation_id}/simulations")
def simuler(corps: ParametresSimulation, a: Acces = Depends(acces(*TOUS))):
    """Un calcul, rien d'enregistré : la convention seule, puis chaque variante."""
    variantes = [simulation.Variante(
        nom=v.nom, regime_version_id=v.regime_version_id,
        categories=None if v.categories is None else [
            regimes.SaisieCategorie(**{**c.model_dump(), "evenements": tuple(c.evenements)}) for c in v.categories])
        for v in corps.variantes]
    return simulation.simuler(a.session, a.organisation, fichier_id=corps.fichier_id,
                              date_evaluation=corps.date_evaluation, convention_code=corps.convention_code,
                              fonds_disponible=corps.fonds_disponible, hypotheses=corps.hypotheses,
                              variantes=variantes)


# --- Fichiers -----------------------------------------------------------------

@routeur.post("/organisations/{organisation_id}/fichiers", status_code=201)
async def deposer_fichier(fichier: UploadFile = File(...), date_donnees: date = Form(...),
                          periodicite: Literal["mensuel", "annuel"] | None = Form(default=None),
                          a: Acces = Depends(acces(*CLIENT))):
    contenu = await fichier.read()
    f, lecture = fichiers.deposer(a.session, a.organisation.id, a.utilisateur.id, contenu=contenu,
                                  nom_fichier=fichier.filename or "fichier", date_donnees=date_donnees,
                                  periodicite=periodicite)
    return {**fichiers.en_clair(f), "colonnes": lecture.colonnes, "colonnes_ignorees": lecture.colonnes_ignorees}


@routeur.get("/organisations/{organisation_id}/fichiers")
def lister_fichiers(a: Acces = Depends(acces(*TOUS))):
    return [fichiers.en_clair(f) for f in fichiers.lister(a.session)]


# --- Études -------------------------------------------------------------------

class ParametresEtude(_Corps):
    fichier_id: uuid.UUID
    date_evaluation: date
    convention_code: str | None = None
    fonds_disponible: int = Field(ge=0)
    hypotheses: dict[str, float] = {}
    justification: str | None = None
    regime_version_id: uuid.UUID | None = None


def _saisie(p: ParametresEtude) -> etudes.Saisie:
    return etudes.Saisie(**p.model_dump())


@routeur.post("/organisations/{organisation_id}/etudes", status_code=201)
def creer_etude(corps: ParametresEtude, a: Acces = Depends(acces(*CLIENT))):
    e = etudes.creer(a.session, a.organisation, a.utilisateur.id, _saisie(corps))
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.get("/organisations/{organisation_id}/etudes")
def lister_etudes(a: Acces = Depends(acces(*TOUS))):
    return [
        {"id": str(e.id), "statut": e.statut, "date_evaluation": e.date_evaluation.isoformat(),
         "convention_code": e.convention_code, "dette": e.resultats["totaux"]["dette"],
         "emise_le": e.emise_le.isoformat() if e.emise_le else None}
        for e in etudes.lister(a.session)
    ]


@routeur.get("/organisations/{organisation_id}/etudes/{etude_id}")
def lire_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    return etudes.en_clair(a.session, a.organisation, etudes.obtenir(a.session, etude_id), date.today())


@routeur.put("/organisations/{organisation_id}/etudes/{etude_id}")
def recalculer_etude(etude_id: uuid.UUID, corps: ParametresEtude, a: Acces = Depends(acces(*CLIENT))):
    e = etudes.recalculer(a.session, a.organisation, etudes.obtenir(a.session, etude_id), a.utilisateur.id,
                          _saisie(corps))
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.delete("/organisations/{organisation_id}/etudes/{etude_id}", status_code=204)
def supprimer_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    etudes.supprimer(a.session, etudes.obtenir(a.session, etude_id), a.utilisateur.id)
    return Response(status_code=204)


@routeur.post("/organisations/{organisation_id}/etudes/{etude_id}/emission")
def emettre_etude(etude_id: uuid.UUID, request: Request, a: Acces = Depends(acces(*CONSEIL))):
    """Émettre, sceller et rendre le rapport : un seul acte. Si le rapport échoue, rien n'est émis."""
    e = etudes.emettre(a.session, a.organisation, etudes.obtenir(a.session, etude_id), a.utilisateur.id, date.today())
    document = rapport.sceller(a.session, a.organisation, e, request.app.state.sceau, date.today())
    journaliser(a.session, a.organisation.id, a.utilisateur.id, "rapport.scelle", document.numero, {"etude_id": str(e.id)})
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.get("/organisations/{organisation_id}/etudes/{etude_id}/rapport")
def telecharger_rapport(etude_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    e = etudes.obtenir(a.session, etude_id)
    document = rapport.document_de(a.session, e)
    nom = f"etude-ifc-{a.organisation.nom}-{e.date_evaluation.isoformat()}-{document.numero}.pdf"
    return Response(document.contenu, media_type=document.type_contenu, headers=_piece_jointe(nom))


# --- Financement ---------------------------------------------------------------

class OffreSaisie(_Corps):
    nom: str = Field(min_length=1)
    taux_garanti: float = Field(default=0.0, ge=-0.05, le=0.2)
    participation_benefices: float = Field(default=0.0, ge=0, le=1)
    frais_sur_cotisations: float = Field(default=0.0, ge=0, le=0.2)
    frais_sur_encours: float = Field(default=0.0, ge=0, le=0.2)
    interne: bool = False


class ScenarioSaisi(_Corps):
    nom: str = Field(min_length=1)
    rendement: float = Field(ge=-0.1, le=0.3)


class ParametresFinancement(_Corps):
    horizon: int = Field(default=10, ge=1, le=40)
    amortissement_annees: int = Field(default=1, ge=1, le=40)
    taux_actualisation: float | None = Field(default=None, ge=-0.05, le=0.2)
    croissance_salaires: float | None = Field(default=None, ge=-0.05, le=0.2)
    offres: list[OffreSaisie] = []
    scenarios: list[ScenarioSaisi] | None = None


@routeur.post("/organisations/{organisation_id}/etudes/{etude_id}/financement")
def financer_etude(etude_id: uuid.UUID, corps: ParametresFinancement, a: Acces = Depends(acces(*TOUS))):
    """Projection du fonds sous chaque offre et chaque scénario ; rien d'enregistré."""
    return financement.financer(
        etudes.obtenir(a.session, etude_id), offres=[Offre(**o.model_dump()) for o in corps.offres],
        scenarios=[Scenario(**x.model_dump()) for x in corps.scenarios] if corps.scenarios else None,
        horizon=corps.horizon, amortissement_annees=corps.amortissement_annees,
        taux_actualisation=corps.taux_actualisation, croissance_salaires=corps.croissance_salaires)


# --- Fiches régime (cahier des charges) -----------------------------------------

class ConditionsDemandees(_Corps):
    taux_garanti_minimum: float | None = Field(default=None, ge=-0.05, le=0.2)
    participation_benefices_minimum: float | None = Field(default=None, ge=0, le=1)
    frais_sur_cotisations_maximum: float | None = Field(default=None, ge=0, le=0.2)
    frais_sur_encours_maximum: float | None = Field(default=None, ge=0, le=0.2)
    transfert_preavis_mois_maximum: int | None = Field(default=None, ge=0, le=24)
    transfert_penalite_maximum: float | None = Field(default=None, ge=0, le=0.2)
    delai_paiement_jours_maximum: int | None = Field(default=None, ge=1, le=365)
    base_etude_plateforme: bool = True
    reporting_annuel: bool = True
    note: str | None = None


class NouvelleFiche(_Corps):
    etude_id: uuid.UUID
    date_limite_reponse: date
    conditions: ConditionsDemandees


@routeur.post("/organisations/{organisation_id}/fiches", status_code=201)
def emettre_fiche(corps: NouvelleFiche, request: Request, a: Acces = Depends(acces(*CONSEIL))):
    """Le cahier des charges : émis, scellé, rendu, en un seul acte."""
    f, document = fiches.emettre(a.session, a.organisation, a.utilisateur.id, etude_id=corps.etude_id,
                                 conditions=corps.conditions.model_dump(), date_limite_reponse=corps.date_limite_reponse,
                                 config=request.app.state.sceau, aujourd_hui=date.today())
    return fiches.en_clair(f, document.numero)


# --- Réponses des assureurs au cahier des charges --------------------------------------------

class SaisieReponse(_Corps):
    assureur: str = Field(min_length=1, max_length=200)
    recue_le: date
    taux_garanti: float = Field(ge=-0.05, le=0.2)
    participation_benefices: float = Field(ge=0, le=1)
    frais_sur_cotisations: float = Field(ge=0, le=0.2)
    frais_sur_encours: float = Field(ge=0, le=0.2)
    delai_paiement_jours: int | None = Field(default=None, ge=1, le=365)
    transfert_preavis_mois: int | None = Field(default=None, ge=0, le=60)
    transfert_penalite: float | None = Field(default=None, ge=0, le=1)
    accepte_etude_plateforme: bool | None = None
    reporting_annuel: bool | None = None
    historique_participation: str | None = Field(default=None, max_length=500)
    commentaire: str | None = Field(default=None, max_length=2000)


class CorrectionReponse(SaisieReponse):
    motif_correction: str = Field(max_length=500)


class Retrait(_Corps):
    motif_correction: str = Field(max_length=500)


class Choix(_Corps):
    reponse_id: uuid.UUID
    motif: str | None = Field(default=None, max_length=1000)


def _donnees(brut: str, modele):
    """Une réponse arrive en multipart (l'offre PDF à côté) : la grille est un champ JSON, validé ici."""
    try:
        return modele.model_validate_json(brut).model_dump()
    except ValidationError as e:
        raise ErreurMetier("donnees_invalides", "Réponse illisible : vérifiez les champs de la grille.", 422,
                           {"erreurs": [{"champ": ".".join(map(str, x["loc"])), "message": x["msg"]} for x in e.errors()]}) from None


async def _offre(offre: UploadFile | None):
    return (offre.filename or "offre.pdf", await offre.read()) if offre is not None else None


@routeur.get("/organisations/{organisation_id}/fiches/{fiche_id}/reponses")
def lire_reponses(fiche_id: uuid.UUID, horizon: int = 10, amortissement: int = 3, a: Acces = Depends(acces(*TOUS))):
    return reponses.tout(a.session, reponses.obtenir_fiche(a.session, fiche_id), horizon, amortissement)


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses", status_code=201)
async def saisir_reponse(fiche_id: uuid.UUID, donnees: str = Form(...), offre: UploadFile | None = File(default=None),
                         a: Acces = Depends(acces(*CLIENT))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    r = reponses.enregistrer(a.session, a.organisation, a.utilisateur.id, fiche, _donnees(donnees, SaisieReponse),
                             offre=await _offre(offre))
    return reponses.en_clair(r, fiche)


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/{reponse_id}/correction", status_code=201)
async def corriger_reponse(fiche_id: uuid.UUID, reponse_id: uuid.UUID, donnees: str = Form(...),
                           offre: UploadFile | None = File(default=None), a: Acces = Depends(acces(*CLIENT))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    d = _donnees(donnees, CorrectionReponse)
    motif = d.pop("motif_correction")
    r = reponses.corriger(a.session, a.organisation, a.utilisateur.id, fiche, reponse_id, d, motif,
                          offre=await _offre(offre))
    return reponses.en_clair(r, fiche)


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/{reponse_id}/retrait", status_code=201)
def retirer_reponse(fiche_id: uuid.UUID, reponse_id: uuid.UUID, corps: Retrait, a: Acces = Depends(acces(*CLIENT))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    r = reponses.retirer(a.session, a.organisation, a.utilisateur.id, fiche, reponse_id, corps.motif_correction)
    return reponses.en_clair(r, fiche)


@routeur.get("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/{reponse_id}/offre")
def telecharger_offre(fiche_id: uuid.UUID, reponse_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    r = a.session.get(ReponseFiche, reponse_id)
    if r is None or r.fiche_id != fiche_id or r.offre_contenu is None:
        raise ErreurMetier("offre_indisponible", "Aucune offre jointe à cette réponse.", 404)
    return Response(r.offre_contenu, media_type="application/pdf", headers=_piece_jointe(r.offre_nom_fichier or "offre.pdf"))


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/choix", status_code=201)
def choisir_reponse(fiche_id: uuid.UUID, corps: Choix, a: Acces = Depends(acces(*ENTREPRISE))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    reponses.choisir(a.session, a.organisation, a.utilisateur.id, fiche, corps.reponse_id, corps.motif)
    return reponses.tout(a.session, fiche)


@routeur.get("/organisations/{organisation_id}/fiches")
def lister_fiches(a: Acces = Depends(acces(*TOUS))):
    return [{k: v for k, v in fiches.en_clair(f, n).items() if k != "contenu"} for f, n in fiches.lister(a.session)]


@routeur.get("/organisations/{organisation_id}/fiches/{fiche_id}")
def lire_fiche(fiche_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    f, document = fiches.obtenir(a.session, fiche_id)
    return fiches.en_clair(f, document.numero)


@routeur.get("/organisations/{organisation_id}/fiches/{fiche_id}/document")
def telecharger_fiche(fiche_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    f, document = fiches.obtenir(a.session, fiche_id)
    nom = f"cahier-des-charges-{a.organisation.nom}-{document.numero}.pdf"
    return Response(document.contenu, media_type=document.type_contenu, headers=_piece_jointe(nom))


def _piece_jointe(nom: str) -> dict:
    """Un nom de fichier sûr dans un en-tête HTTP : une version ASCII, et l'originale en UTF-8 (RFC 5987).
    Un nom d'organisation accentué (« Société ») cassait l'en-tête, qui n'admet que le latin-1."""
    nom = nom.replace(" ", "-")
    ascii_ = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode() or "document.pdf"
    return {"Content-Disposition": f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nom)}"}


# --- Vérification publique (sans compte) --------------------------------------

@routeur.get("/verifier/{numero}", dependencies=[Depends(limite("verification"))])
def verifier_document(numero: str, request: Request, session: Session = Depends(session_db)):
    return rapport.verifier(session, numero, request.app.state.sceau)


@routeur.post("/verifier/{numero}", dependencies=[Depends(limite("verification"))])
async def verifier_fichier(numero: str, document: UploadFile = File(...), session: Session = Depends(session_db)):
    """Le fichier présenté est-il l'original, octet pour octet ?"""
    return {"numero": numero, "conforme": rapport.est_conforme(session, numero, await document.read())}
