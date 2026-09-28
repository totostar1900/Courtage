"""Routes de l'API. Les droits se lisent sur la signature : `acces(...)` nomme les rôles admis."""
import unicodedata
import uuid
from datetime import date
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.auth.telephone import normaliser
from courtage.db import Adhesion, Contrat, Organisation, ReponseFiche, Utilisateur, contexte
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.financement import Offre, Scenario
from courtage.services import activation, alertes, messages, analyse, cycle, equipe, nettoyage, notes_regime, catalogue, contrats, dossiers, etudes, extractions, mandats, orientation, reponses, prestations, fiches, financement, fichiers, journaliser, rapport, regimes, simulation

from . import Acces, acces, identite, session_db
from .limites import limite

routeur = APIRouter()

CLIENT = ("admin_client", "contributeur_client", "conseiller")   # déposer, préparer : études, régimes en brouillon
ENTREPRISE = ("admin_client",)               # adopter son régime : l'entreprise est souveraine
CONSEIL = ("conseiller",)                    # émettre, fixer la rémunération
TOUS: tuple[str, ...] = ()                   # lire


class _Corps(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Moi, organisations, adhésions --------------------------------------------

@routeur.get("/moi")
def moi(session: Session = Depends(session_db, scope="function"), utilisateur: Utilisateur = Depends(identite)):
    rangs = session.execute(
        select(Organisation, Adhesion.role).join(Adhesion, Adhesion.organisation_id == Organisation.id)
        .where(Adhesion.utilisateur_id == utilisateur.id).order_by(Organisation.nom)).all()
    return {
        "id": str(utilisateur.id), "email": utilisateur.email, "telephone": utilisateur.telephone,
        "admin_plateforme": utilisateur.admin_plateforme,
        "organisations": [{"id": str(o.id), "nom": o.nom, "pays": o.pays, "role": r, "etat": o.etat,
                           "etat_depuis": o.etat_depuis.isoformat(), "activation": o.activation}
                          for o, r in rangs if o.etat not in ("archive", "supprime")],
    }


@routeur.get("/organisations/{organisation_id}/activation")
def lire_activation(a: Acces = Depends(acces(*TOUS))):
    """Où en est l'inscription, et ce que chaque capacité attend encore."""
    return activation.en_clair(a.session, a.organisation, date.today())


@routeur.post("/organisations/{organisation_id}/justificatifs", status_code=201)
async def deposer_justificatif(fichier: UploadFile = File(...), a: Acces = Depends(acces("admin_client", "contributeur_client"))):
    """Le document RCCM, pour que le courtier confirme l'inscription."""
    j = activation.deposer_rccm(a.session, a.organisation, a.utilisateur.id, await fichier.read(),
                                fichier.filename or "rccm", fichier.content_type or "")
    return {"id": str(j.id), "nom_fichier": j.nom_fichier}


@routeur.get("/organisations/{organisation_id}/justificatifs")
def lister_justificatifs(a: Acces = Depends(acces(*TOUS))):
    return activation.justificatifs(a.session)


@routeur.delete("/organisations/{organisation_id}/inscription")
def supprimer_inscription(confirmation: str = "", a: Acces = Depends(acces(*ENTREPRISE))):
    """Tant qu'elle attend (ou si elle a été refusée), l'entreprise retire son inscription : tout part."""
    if confirmation.strip().upper() not in ("SUPPRIMER", "DELETE"):
        raise ErreurMetier("confirmation_requise", "Écrire « SUPPRIMER » pour confirmer.", 422)
    return activation.effacer(a.session, a.organisation, a.utilisateur.id, "retirée par l'entreprise")


class NouveauMessage(_Corps):
    texte: str = Field(min_length=1, max_length=4000)


@routeur.get("/organisations/{organisation_id}/messages")
def lire_messages(a: Acces = Depends(acces(*TOUS))):
    return messages.lire(a.session, messages.cote_de(a.role, a.utilisateur.admin_plateforme))


@routeur.get("/organisations/{organisation_id}/messages/non-lus")
def messages_non_lus(a: Acces = Depends(acces(*TOUS))):
    return {"non_lus": messages.non_lus(a.session, messages.cote_de(a.role, a.utilisateur.admin_plateforme))}


@routeur.post("/organisations/{organisation_id}/messages", status_code=201)
def envoyer_message(corps: NouveauMessage, a: Acces = Depends(acces(*TOUS))):
    messages.envoyer(a.session, a.organisation.id, a.utilisateur.id,
                     messages.cote_de(a.role, a.utilisateur.admin_plateforme), corps.texte)
    return messages.lire(a.session, messages.cote_de(a.role, a.utilisateur.admin_plateforme))


@routeur.get("/alertes")
def alertes_de_mes_dossiers(session: Session = Depends(session_db, scope="function"),
                            utilisateur: Utilisateur = Depends(identite)):
    """Le décompte des alertes de chacun de mes dossiers, pour « Vos dossiers »."""
    decompte = {}
    for org in session.scalars(select(Organisation).join(Adhesion, Adhesion.organisation_id == Organisation.id)
                               .where(Adhesion.utilisateur_id == utilisateur.id)):
        if org.etat in ("archive", "supprime"):
            continue
        contexte(session.connection(), org.id)
        liste = alertes.du_dossier(session, org, date.today())
        decompte[str(org.id)] = {n: sum(a["niveau"] == n for a in liste) for n in ("grave", "attention", "info")}
    return decompte


@routeur.get("/organisations/{organisation_id}/alertes")
def alertes_du_dossier(a: Acces = Depends(acces(*TOUS))):
    return alertes.du_dossier(a.session, a.organisation, date.today())


class NouvelleOrganisation(_Corps):
    nom: str = Field(min_length=1)
    pays: str = Field(pattern=r"^[A-Z]{2}$")
    secteur: str | None = None
    suivre: bool = False                  # celui qui ouvre le dossier en devient le conseiller


@routeur.post("/organisations", status_code=201)
def creer_organisation(corps: NouvelleOrganisation, session: Session = Depends(session_db, scope="function"),
                       utilisateur: Utilisateur = Depends(identite)):
    if not utilisateur.admin_plateforme:
        raise ErreurMetier("acces_refuse", "Seule la plateforme ouvre un dossier client.", 403)
    org = Organisation(nom=corps.nom.strip(), pays=corps.pays, secteur=corps.secteur)
    session.add(org)
    session.flush()
    journaliser(session, None, utilisateur.id, "organisation.creee", org.id, {"nom": org.nom, "pays": org.pays})
    if corps.suivre:
        session.add(Adhesion(utilisateur_id=utilisateur.id, organisation_id=org.id, role="conseiller"))
        contexte(session.connection(), org.id)
        journaliser(session, org.id, utilisateur.id, "adhesion.ajoutee", utilisateur.id,
                    {"utilisateur_id": str(utilisateur.id), "role": "conseiller"})
    return {"id": str(org.id), "nom": org.nom, "pays": org.pays, "secteur": org.secteur}


class ChangementEtat(_Corps):
    action: Literal["suspendre", "cloturer", "reprendre", "supprimer"]
    motif_code: str | None = None
    motif: str | None = Field(default=None, max_length=500)


@routeur.get("/organisations/{organisation_id}/cycle")
def lire_cycle(a: Acces = Depends(acces(*TOUS))):
    """L'état du dossier, son histoire, et ce que le conseiller peut en faire."""
    return cycle.en_clair(a.session, a.organisation)


@routeur.post("/organisations/{organisation_id}/cycle")
def changer_cycle(corps: ChangementEtat, a: Acces = Depends(acces(*CONSEIL))):
    """Suspendre, clôturer, reprendre, supprimer (un dossier vide) : le conseiller seul, motif à l'appui."""
    cycle.changer(a.session, a.organisation, a.utilisateur.id, corps.action, corps.motif_code, corps.motif)
    if corps.action == "supprimer":
        return {"etat": "supprime"}
    return cycle.en_clair(a.session, a.organisation)


Droits = Literal["admin_client", "contributeur_client", "lecteur_client", "conseiller"]


@routeur.get("/organisations/{organisation_id}/nettoyage")
def lire_nettoyage(a: Acces = Depends(acces("admin_client", "conseiller"))):
    """Ce que le dossier contient, et ce que chaque choix du nettoyage ferait partir."""
    return nettoyage.inventaire(a.session)


@routeur.get("/organisations/{organisation_id}/archive")
def telecharger_archive(a: Acces = Depends(acces(*TOUS))):
    """Tout ce que l'entreprise voudra garder : documents scellés, études en Excel, sommaire des numéros."""
    journaliser(a.session, a.organisation.id, a.utilisateur.id, "dossier.archive_telechargee", a.organisation.id, {})
    nom = f"archive-{a.organisation.nom}-{date.today().isoformat()}.zip"
    return Response(nettoyage.archive(a.session, a.organisation, date.today()), media_type="application/zip",
                    headers=_piece_jointe(nom))


class Nettoyage(_Corps):
    fichiers: Literal["alleger", "supprimer"] | None = None
    brouillons: bool = False
    etudes_emises: bool = False
    confirmation: str = ""


@routeur.post("/organisations/{organisation_id}/nettoyage")
def nettoyer_dossier(corps: Nettoyage, a: Acces = Depends(acces("admin_client", "conseiller"))):
    """Faire partir ce qui a été choisi ; les sceaux et le journal restent."""
    return nettoyage.nettoyer(a.session, a.organisation, a.utilisateur.id, fichiers_=corps.fichiers,
                             brouillons=corps.brouillons, etudes_emises=corps.etudes_emises,
                             confirmation=corps.confirmation)


class NouvelleAdhesion(_Corps):
    utilisateur_id: uuid.UUID
    role: Droits


@routeur.post("/organisations/{organisation_id}/adhesions", status_code=201)
def ajouter_adhesion(organisation_id: uuid.UUID, corps: NouvelleAdhesion, session: Session = Depends(session_db, scope="function"),
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


def _role_de(session: Session, utilisateur: Utilisateur, organisation_id: uuid.UUID) -> str | None:
    return session.scalar(select(Adhesion.role).where(
        Adhesion.utilisateur_id == utilisateur.id, Adhesion.organisation_id == organisation_id))


@routeur.get("/organisations/{organisation_id}/equipe")
def lire_equipe(a: Acces = Depends(acces(*TOUS))):
    """Qui suit le dossier, ce que l'appelant peut y changer, et les droits qu'il peut donner."""
    return equipe.lister(a.session, a.organisation, a.utilisateur, a.role)


class NouveauMembre(_Corps):
    telephone: str = Field(min_length=1, max_length=30)
    nom_affiche: str = Field(min_length=1)
    role: Droits
    fonction: str | None = Field(default=None, max_length=80)


@routeur.post("/organisations/{organisation_id}/membres", status_code=201)
def inscrire_membre(organisation_id: uuid.UUID, corps: NouveauMembre, session: Session = Depends(session_db, scope="function"),
                    utilisateur: Utilisateur = Depends(identite)):
    """Inscrire quelqu'un par son numéro : le conseiller (ou la plateforme) tout le monde, l'administrateur de
    l'entreprise ses collègues."""
    org = session.get(Organisation, organisation_id)
    if org is None:
        raise ErreurMetier("introuvable", "Organisation introuvable.", 404)
    role = _role_de(session, utilisateur, organisation_id)
    if not (utilisateur.admin_plateforme or role):
        raise ErreurMetier("acces_refuse", "Vous n'êtes pas membre de cette organisation.", 403)
    cycle.exiger_ecriture(org)
    contexte(session.connection(), organisation_id)
    activation.exiger(session, org, "equipe")
    return equipe.inscrire(session, org, utilisateur, role, telephone=corps.telephone, nom_affiche=corps.nom_affiche,
                           role=corps.role, fonction=corps.fonction)


class ModificationMembre(_Corps):
    nom_affiche: str | None = Field(default=None, max_length=120)
    fonction: str | None = Field(default=None, max_length=80)
    role: Droits | None = None


@routeur.patch("/organisations/{organisation_id}/membres/{utilisateur_id}")
def modifier_membre(utilisateur_id: uuid.UUID, corps: ModificationMembre, a: Acces = Depends(acces(*TOUS))):
    if utilisateur_id != a.utilisateur.id or corps.role is not None:      # sa propre fonction, oui ; les droits, non
        activation.exiger(a.session, a.organisation, "equipe")
    equipe.modifier(a.session, a.organisation, a.utilisateur, a.role, utilisateur_id, **corps.model_dump())
    return equipe.lister(a.session, a.organisation, a.utilisateur, a.role)


@routeur.delete("/organisations/{organisation_id}/membres/{utilisateur_id}")
def retirer_membre(utilisateur_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    """Le membre quitte le dossier ; ce qu'il a fait reste au journal, sous son nom."""
    equipe.retirer(a.session, a.organisation, a.utilisateur, a.role, utilisateur_id)
    return equipe.lister(a.session, a.organisation, a.utilisateur, a.role)


# --- Contrats : courtage ou comparaison --------------------------------------------

class NouveauContrat(_Corps):
    en_vigueur_du: date
    service: Literal["courtage"] = "courtage"      # la plateforme ne fait plus que du courtage
    assureur: str | None = Field(default=None, max_length=200)
    numero_police: str | None = Field(default=None, max_length=100)
    date_effet_police: date | None = None
    mandat_reference: str | None = Field(default=None, max_length=300)
    note: str | None = Field(default=None, max_length=2000)


@routeur.post("/organisations/{organisation_id}/contrats", status_code=201)
def enregistrer_contrat(corps: NouveauContrat, a: Acces = Depends(acces(*CONSEIL))):
    return contrats.en_clair(contrats.enregistrer(a.session, a.organisation.id, a.utilisateur.id, **corps.model_dump()))


@routeur.delete("/organisations/{organisation_id}/contrats/{contrat_id}")
def supprimer_contrat(contrat_id: uuid.UUID, a: Acces = Depends(acces(*CONSEIL))):
    """Un contrat saisi par erreur, qu'aucun dossier ni aucun départ enregistré n'utilise."""
    c = a.session.get(Contrat, contrat_id)
    if c is None:
        raise Introuvable("Contrat")
    contrats.supprimer(a.session, c, a.utilisateur.id)
    return {"supprime": True}


# --- Accompagnement : la demande, le mandat proposé, signé ------------------------

class DemandeAccompagnement(_Corps):
    besoins: list[str] = Field(min_length=1, max_length=10)
    message: str | None = Field(default=None, max_length=2000)


class PropositionMandat(_Corps):
    perimetre: list[str] = Field(min_length=1, max_length=10)
    date_effet: date
    duree_mois: int = Field(ge=1, le=60)
    preavis_mois: int = Field(ge=1, le=12)
    exclusif: bool = True
    conditions: str | None = Field(default=None, max_length=3000)


class SignatureMandat(_Corps):
    nom: str = Field(min_length=1, max_length=200)
    fonction: str | None = Field(default=None, max_length=100)
    empreinte: str = Field(min_length=64, max_length=64)
    accepte: bool


class Motif(_Corps):
    motif: str | None = Field(default=None, max_length=1000)


@routeur.get("/organisations/{organisation_id}/mandats")
def lire_mandats(a: Acces = Depends(acces(*TOUS))):
    return mandats.tableau(a.session, a.organisation, date.today())


@routeur.post("/organisations/{organisation_id}/mandats", status_code=201)
def demander_accompagnement(corps: DemandeAccompagnement, a: Acces = Depends(acces("admin_client", "contributeur_client"))):
    m = mandats.demander(a.session, a.organisation, a.utilisateur.id, corps.besoins, corps.message, date.today())
    return mandats.en_clair(a.session, a.organisation, m)


@routeur.put("/organisations/{organisation_id}/mandats/{mandat_id}/proposition")
def proposer_mandat(mandat_id: uuid.UUID, corps: PropositionMandat, a: Acces = Depends(acces(*CONSEIL))):
    activation.exiger(a.session, a.organisation, "mandat")
    m = mandats.proposer(a.session, a.organisation, mandats.obtenir(a.session, mandat_id), a.utilisateur.id,
                         **corps.model_dump(), aujourd_hui=date.today())
    return mandats.en_clair(a.session, a.organisation, m)


@routeur.post("/organisations/{organisation_id}/mandats/{mandat_id}/signature")
def signer_mandat(mandat_id: uuid.UUID, corps: SignatureMandat, request: Request,
                  a: Acces = Depends(acces(*ENTREPRISE))):
    """L'administrateur de l'entreprise signe le texte qu'il a lu (son empreinte) : le mandat est scellé, le
    contrat « courtage » prend effet à sa date."""
    activation.exiger(a.session, a.organisation, "mandat")
    if not corps.accepte:
        raise ErreurMetier("acceptation_requise", "Cocher « J'ai lu et j'accepte ce mandat ».", 422)
    m = mandats.obtenir(a.session, mandat_id)
    mandats.signer(a.session, a.organisation, m, a.utilisateur.id, nom=corps.nom, fonction=corps.fonction,
                   empreinte_lue=corps.empreinte, config=request.app.state.sceau, aujourd_hui=date.today())
    return mandats.en_clair(a.session, a.organisation, m)


@routeur.post("/organisations/{organisation_id}/mandats/{mandat_id}/refus")
def refuser_mandat(mandat_id: uuid.UUID, corps: Motif, a: Acces = Depends(acces(*ENTREPRISE))):
    m = mandats.obtenir(a.session, mandat_id)
    mandats.clore(a.session, m, a.utilisateur.id, "refuse", corps.motif)
    return mandats.en_clair(a.session, a.organisation, m)


@routeur.post("/organisations/{organisation_id}/mandats/{mandat_id}/retrait")
def retirer_mandat(mandat_id: uuid.UUID, corps: Motif, a: Acces = Depends(acces(*CLIENT))):
    m = mandats.obtenir(a.session, mandat_id)
    mandats.clore(a.session, m, a.utilisateur.id, "retire", corps.motif)
    return mandats.en_clair(a.session, a.organisation, m)


@routeur.get("/organisations/{organisation_id}/mandats/{mandat_id}/pdf")
def telecharger_mandat(mandat_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    d = mandats.document_de(a.session, mandats.obtenir(a.session, mandat_id))
    if d is None:
        raise ErreurMetier("mandat_non_signe", "Le mandat scellé existe une fois signé.", 404)
    return Response(d.contenu, media_type=d.type_contenu, headers=_piece_jointe(f"mandat-courtage-{a.organisation.nom}-{d.numero}.pdf"))


@routeur.get("/organisations/{organisation_id}/contrats")
def lire_contrats(a: Acces = Depends(acces(*TOUS))):
    aujourd_hui = date.today()
    courant = contrats.service_a_la_date(a.session, aujourd_hui)
    return {
        "service": courant.service,
        "en_vigueur": contrats.en_clair(courant.contrat) if courant.contrat else None,
        "historique": [{**contrats.en_clair(c), "raison_de_garder": contrats.raison_de_garder(a.session, c)}
                       for c in contrats.historique(a.session)],
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


@routeur.get("/organisations/{organisation_id}/prestations/{prestation_id}/fiche-de-calcul")
def fiche_de_calcul(prestation_id: uuid.UUID, request: Request, a: Acces = Depends(acces(*CLIENT))):
    activation.exiger(a.session, a.organisation, "fiche_de_calcul")
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
    if request.app.state.extracteur.envoie_a_un_tiers:
        activation.exiger(a.session, a.organisation, "extraction_claude")
    return extractions.pour_un_regime(a.session, a.organisation, a.utilisateur.id, request.app.state.extracteur,
                                      contenu=await fichier.read(), nom_fichier=fichier.filename or "texte",
                                      consentement=consentement)


@routeur.post("/referentiel/extraction")
async def extraire_convention(request: Request, fichier: UploadFile = File(...), pays: str = Form(...),
                              consentement: bool = Form(default=False), session: Session = Depends(session_db, scope="function"),
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


@routeur.delete("/organisations/{organisation_id}/regimes/versions/{version_id}")
def supprimer_version(version_id: uuid.UUID, motif: str | None = None, a: Acces = Depends(acces(*CLIENT))):
    """Un brouillon, ou une version adoptée que rien ne cite (l'administrateur de l'entreprise, avec un motif) ; ses
    études en brouillon partent avec elle, et son régime s'il reste sans version."""
    regime_supprime = regimes.supprimer(a.session, regimes.obtenir_version(a.session, version_id), a.utilisateur.id,
                                        a.role, motif)
    return {"supprimee": True, "regime_supprime": regime_supprime}


@routeur.put("/organisations/{organisation_id}/regimes/versions/{version_id}")
def modifier_version(version_id: uuid.UUID, corps: NouvelleVersion, a: Acces = Depends(acces(*CLIENT))):
    """Un brouillon se corrige sur place, jusqu'à son adoption."""
    v = regimes.modifier_brouillon(
        a.session, a.organisation, regimes.obtenir_version(a.session, version_id), a.utilisateur.id,
        en_vigueur_du=corps.en_vigueur_du, fondement=corps.fondement, document_reference=corps.document_reference,
        note=corps.note, categories=[regimes.SaisieCategorie(**{**c.model_dump(), "evenements": tuple(c.evenements)})
                                     for c in corps.categories])
    return regimes.en_clair(a.session, v)


@routeur.post("/organisations/{organisation_id}/regimes/versions/{version_id}/duplication", status_code=201)
def dupliquer_version(version_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    """Un nouveau brouillon, copie de la version : c'est ainsi qu'évolue une version adoptée."""
    v = regimes.dupliquer(a.session, a.organisation, regimes.obtenir_version(a.session, version_id), a.utilisateur.id)
    return regimes.en_clair(a.session, v)


@routeur.post("/organisations/{organisation_id}/regimes/versions/{version_id}/notes/{nature}")
def emettre_note(version_id: uuid.UUID, nature: str, request: Request,
                 a: Acces = Depends(acces("admin_client", "conseiller"))):
    """La note aux salariés ou aux assureurs d'une version adoptée : scellée à la première demande, la même ensuite."""
    activation.exiger(a.session, a.organisation, "notes_regime")
    d = notes_regime.emettre(a.session, a.organisation, regimes.obtenir_version(a.session, version_id), nature,
                             a.utilisateur.id, request.app.state.sceau, date.today())
    return {"numero": d.numero}


@routeur.get("/organisations/{organisation_id}/regimes/versions/{version_id}/notes/{nature}")
def telecharger_note(version_id: uuid.UUID, nature: str, a: Acces = Depends(acces(*TOUS))):
    v = regimes.obtenir_version(a.session, version_id)
    d = notes_regime.existante(a.session, v, nature) if nature in notes_regime.NATURES else None
    if d is None:
        raise ErreurMetier("note_non_emise", "Cette note n'a pas encore été émise.", 404)
    nom = f"{notes_regime.NATURES[nature][2].lower().replace(' ', '-')}-{a.organisation.nom}-v{v.numero}-{d.numero}.pdf"
    return Response(d.contenu, media_type=d.type_contenu, headers=_piece_jointe(nom))


@routeur.get("/organisations/{organisation_id}/regimes/menage")
def lire_menage(a: Acces = Depends(acces(*CLIENT))):
    """Ce qui peut partir, avec sa raison et ce que coche la plateforme."""
    return {"jours_sans_decision": regimes.JOURS_SANS_DECISION,
            "candidats": regimes.menage(a.session, date.today(), a.role)}


class Menage(_Corps):
    versions: list[uuid.UUID] = Field(min_length=1)
    motif: str | None = Field(default=None, max_length=500)


@routeur.post("/organisations/{organisation_id}/regimes/menage")
def faire_le_menage(corps: Menage, a: Acces = Depends(acces(*CLIENT))):
    """Supprimer d'un coup les versions choisies, et les études en brouillon qui les retiennent."""
    return regimes.faire_le_menage(a.session, a.utilisateur.id, a.role, corps.versions, corps.motif)


# --- Le catalogue anonyme ------------------------------------------------------

class Partage(_Corps):
    secteur: str
    taille: Literal["moins_de_50", "50_a_250", "plus_de_250"]
    consentement: bool


@routeur.get("/catalogue/regimes")
def consulter_catalogue(session: Session = Depends(session_db, scope="function"),
                        utilisateur: Utilisateur = Depends(identite)):
    """Une entreprise confirmée (ou la plateforme) : des groupes d'au moins cinq entreprises, jamais une entreprise.
    Ni un visiteur, ni une inscription en attente : on ne compare qu'à des entreprises vérifiées."""
    if not utilisateur.admin_plateforme and not session.scalar(
            select(func.count()).select_from(Adhesion).join(Organisation, Organisation.id == Adhesion.organisation_id)
            .where(Adhesion.utilisateur_id == utilisateur.id, Organisation.activation == "confirmee")):
        raise ErreurMetier("inscription_non_confirmee", "Le catalogue anonyme s'ouvre une fois votre inscription "
                           "confirmée par votre conseiller.", 403, {"capacite": "catalogue"})
    return catalogue.consulter(session)


@routeur.get("/organisations/{organisation_id}/regimes/partages")
def partages_du_dossier(a: Acces = Depends(acces(*TOUS))):
    return catalogue.partages_de(a.session, a.organisation)


@routeur.post("/organisations/{organisation_id}/regimes/versions/{version_id}/partage", status_code=201)
def partager_version(version_id: uuid.UUID, corps: Partage, a: Acces = Depends(acces(*ENTREPRISE))):
    activation.exiger(a.session, a.organisation, "catalogue")
    if not corps.consentement:
        raise ErreurMetier("consentement_requis", "Le partage demande l'accord explicite de l'entreprise.", 422)
    lien = catalogue.partager(a.session, a.organisation, regimes.obtenir_version(a.session, version_id),
                              a.utilisateur.id, secteur=corps.secteur, taille=corps.taille)
    return {"partage_id": str(lien.partage_id), "version_id": str(lien.version_id)}


@routeur.post("/organisations/{organisation_id}/regimes/partages/{partage_id}/retrait")
def retirer_partage(partage_id: uuid.UUID, a: Acces = Depends(acces(*ENTREPRISE))):
    catalogue.retirer(a.session, a.organisation, partage_id, a.utilisateur.id)
    return {"partage_id": str(partage_id), "actif": False}


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
    hypotheses: dict[str, Any] = {}
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
    return [{**fichiers.en_clair(f), **fichiers.usages(a.session, f)} for f in fichiers.lister(a.session)]


@routeur.delete("/organisations/{organisation_id}/fichiers/{fichier_id}")
def supprimer_fichier(fichier_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    """Le fichier et ses études en brouillon ; cité par une étude émise, il s'allège plutôt."""
    return fichiers.supprimer(a.session, fichiers.obtenir(a.session, fichier_id), a.utilisateur.id)


@routeur.post("/organisations/{organisation_id}/fichiers/{fichier_id}/allegement")
def alleger_fichier(fichier_id: uuid.UUID, a: Acces = Depends(acces(*CLIENT))):
    """Vider les lignes, garder nom, date et empreinte ; les études émises restent prouvées."""
    return fichiers.alleger(a.session, fichiers.obtenir(a.session, fichier_id), a.utilisateur.id)


@routeur.get("/organisations/{organisation_id}/fichiers/{fichier_id}/telechargement")
def telecharger_fichier(fichier_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    """Le personnel déposé, tel que la plateforme le garde (sans nom), à corriger et redéposer."""
    from courtage.fichier.canevas import exporter
    f = fichiers.obtenir(a.session, fichier_id)
    journaliser(a.session, a.organisation.id, a.utilisateur.id, "fichier.telecharge", f.id, {})
    nom = f"personnel-{f.date_donnees.isoformat()}.xlsx"
    return Response(exporter(f.lignes, f.anomalies, date_donnees=f.date_donnees, nom_fichier=f.nom_fichier),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})


# --- Études -------------------------------------------------------------------

class ParametresEtude(_Corps):
    fichier_id: uuid.UUID
    date_evaluation: date
    convention_code: str | None = None
    fonds_disponible: int = Field(ge=0)
    hypotheses: dict[str, Any] = {}
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
         "emise_le": e.emise_le.isoformat() if e.emise_le else None,
         "raison_de_garder": etudes.raison_de_garder(a.session, e)}
        for e in etudes.lister(a.session)
    ]


@routeur.get("/organisations/{organisation_id}/etudes/{etude_id}")
def lire_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    return etudes.en_clair(a.session, a.organisation, etudes.obtenir(a.session, etude_id), date.today())


@routeur.get("/organisations/{organisation_id}/etudes/{etude_id}/export")
def exporter_etude(etude_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    """L'étude en Excel : synthèse, échéancier, catégories, sensibilités, salariés (par matricule)."""
    activation.exiger(a.session, a.organisation, "export_etude")
    from courtage import exports
    e = etudes.en_clair(a.session, a.organisation, etudes.obtenir(a.session, etude_id), date.today())
    journaliser(a.session, a.organisation.id, a.utilisateur.id, "etude.exportee", etude_id, {})
    return _xlsx(exports.etude(e, a.organisation.nom), f"etude-ifc-{e['date_evaluation']}.xlsx")


def _xlsx(contenu: bytes, nom: str) -> Response:
    return Response(contenu, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="{nom}"'})


@routeur.put("/organisations/{organisation_id}/etudes/{etude_id}")
def recalculer_etude(etude_id: uuid.UUID, corps: ParametresEtude, a: Acces = Depends(acces(*CLIENT))):
    e = etudes.recalculer(a.session, a.organisation, etudes.obtenir(a.session, etude_id), a.utilisateur.id,
                          _saisie(corps))
    return etudes.en_clair(a.session, a.organisation, e, date.today())


@routeur.delete("/organisations/{organisation_id}/etudes/{etude_id}", status_code=204)
def supprimer_etude(etude_id: uuid.UUID, confirmation: str | None = None, a: Acces = Depends(acces(*CLIENT))):
    """Un brouillon : l'équipe. Une étude émise : l'administrateur ou le conseiller, sur confirmation écrite."""
    e = etudes.obtenir(a.session, etude_id)
    if e.statut == "emise" and a.role not in ("admin_client", "conseiller"):
        raise ErreurMetier("droit_insuffisant", "Seuls l'administrateur et le conseiller suppriment une étude émise.", 403)
    etudes.supprimer(a.session, e, a.utilisateur.id, confirmation=confirmation)
    return Response(status_code=204)


@routeur.post("/organisations/{organisation_id}/etudes/{etude_id}/emission")
def emettre_etude(etude_id: uuid.UUID, request: Request, a: Acces = Depends(acces(*CONSEIL))):
    """Émettre, sceller et rendre le rapport : un seul acte. Si le rapport échoue, rien n'est émis."""
    activation.exiger(a.session, a.organisation, "rapport_scelle")
    cycle.exiger_emission(a.organisation)
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
    activation.exiger(a.session, a.organisation, "cahier")
    cycle.exiger_emission(a.organisation)
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


@routeur.get("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/export")
def exporter_reponses(fiche_id: uuid.UUID, a: Acces = Depends(acces(*TOUS))):
    """Les réponses des assureurs en Excel : comparaison, conformité, scénarios, cahier des charges."""
    from courtage import exports
    t = reponses.tout(a.session, reponses.obtenir_fiche(a.session, fiche_id))
    journaliser(a.session, a.organisation.id, a.utilisateur.id, "reponses.exportees", fiche_id, {})
    return _xlsx(exports.reponses(t, a.organisation.nom), "reponses-assureurs.xlsx")


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses", status_code=201)
async def saisir_reponse(fiche_id: uuid.UUID, donnees: str = Form(...), offre: UploadFile | None = File(default=None),
                         a: Acces = Depends(acces(*CONSEIL))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    r = reponses.enregistrer(a.session, a.organisation, a.utilisateur.id, fiche, _donnees(donnees, SaisieReponse),
                             offre=await _offre(offre))
    return reponses.en_clair(r, fiche)


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/{reponse_id}/correction", status_code=201)
async def corriger_reponse(fiche_id: uuid.UUID, reponse_id: uuid.UUID, donnees: str = Form(...),
                           offre: UploadFile | None = File(default=None), a: Acces = Depends(acces(*CONSEIL))):
    fiche = reponses.obtenir_fiche(a.session, fiche_id)
    d = _donnees(donnees, CorrectionReponse)
    motif = d.pop("motif_correction")
    r = reponses.corriger(a.session, a.organisation, a.utilisateur.id, fiche, reponse_id, d, motif,
                          offre=await _offre(offre))
    return reponses.en_clair(r, fiche)


@routeur.post("/organisations/{organisation_id}/fiches/{fiche_id}/reponses/{reponse_id}/retrait", status_code=201)
def retirer_reponse(fiche_id: uuid.UUID, reponse_id: uuid.UUID, corps: Retrait, a: Acces = Depends(acces(*CONSEIL))):
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
def verifier_document(numero: str, request: Request, session: Session = Depends(session_db, scope="function")):
    return rapport.verifier(session, numero, request.app.state.sceau)


@routeur.post("/verifier/{numero}", dependencies=[Depends(limite("verification"))])
async def verifier_fichier(numero: str, document: UploadFile = File(...), session: Session = Depends(session_db, scope="function")):
    """Le fichier présenté est-il l'original, octet pour octet ?"""
    return {"numero": numero, "conforme": rapport.est_conforme(session, numero, await document.read())}
