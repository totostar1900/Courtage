"""Les réponses des assureurs au cahier des charges (placement) : confrontées, classées, choisies.

Chaque réponse est confrontée, critère par critère, aux conditions que le cahier
demandait : conforme, en écart (et de combien), ou non renseignée — ce qui n'est
pas « conforme ». Les réponses sont ensuite classées par le même calcul que la
comparaison d'offres (coût net actualisé, scénario central, provision interne
en référence). La RECOMMANDÉE est la moins chère des conformes.

Le choix appartient à l'entreprise : un par cahier, et motivé quand il ne se
porte pas sur la recommandée. La plateforme éclaire ; elle ne décide pas.
"""
import hashlib
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from courtage.db import ChoixFiche, FicheRegime, Organisation, ReponseFiche
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.financement import Offre

from . import etudes, financement, journaliser

CHAMPS = ("assureur", "recue_le", "taux_garanti", "participation_benefices", "frais_sur_cotisations",
          "frais_sur_encours", "delai_paiement_jours", "transfert_preavis_mois", "transfert_penalite",
          "accepte_etude_plateforme", "reporting_annuel", "historique_participation", "commentaire")
# (critère, libellé, condition du cahier, sens)
CRITERES = (
    ("taux_garanti", "Taux garanti", "taux_garanti_minimum", "min"),
    ("participation_benefices", "Participation aux bénéfices", "participation_benefices_minimum", "min"),
    ("frais_sur_cotisations", "Frais sur cotisations", "frais_sur_cotisations_maximum", "max"),
    ("frais_sur_encours", "Frais sur encours", "frais_sur_encours_maximum", "max"),
    ("delai_paiement_jours", "Délai de paiement (jours)", "delai_paiement_jours_maximum", "max"),
    ("transfert_preavis_mois", "Préavis de transfert (mois)", "transfert_preavis_mois_maximum", "max"),
    ("transfert_penalite", "Pénalité de transfert", "transfert_penalite_maximum", "max"),
    ("accepte_etude_plateforme", "L'étude de la plateforme sert de base", "base_etude_plateforme", "oui"),
    ("reporting_annuel", "Relevé annuel du fonds", "reporting_annuel", "oui"),
)
TAILLE_MAX_OFFRE = 10 * 1024 * 1024


def obtenir_fiche(session: Session, fiche_id: uuid.UUID) -> FicheRegime:
    f = session.get(FicheRegime, fiche_id)
    if f is None:
        raise Introuvable("Cahier des charges")
    return f


def choix(session: Session, fiche: FicheRegime) -> ChoixFiche | None:
    return session.scalars(select(ChoixFiche).where(ChoixFiche.fiche_id == fiche.id)).first()


def actives(session: Session, fiche: FicheRegime) -> list[ReponseFiche]:
    suivante = aliased(ReponseFiche)
    remplacees = select(suivante.remplace_id).where(suivante.remplace_id.is_not(None))
    return list(session.scalars(select(ReponseFiche).where(ReponseFiche.fiche_id == fiche.id,
                                                           ReponseFiche.retrait.is_(False),
                                                           ReponseFiche.id.not_in(remplacees))
                                .order_by(ReponseFiche.cree_le)))


# --- Écrire ------------------------------------------------------------------------------------

def enregistrer(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, donnees: dict, *,
                offre: tuple[str, bytes] | None = None, remplace: ReponseFiche | None = None,
                motif_correction: str | None = None) -> ReponseFiche:
    _ouverte(session, fiche)
    recue = donnees["recue_le"]
    if recue > date.today():
        raise ErreurMetier("date_a_venir", "Une réponse se saisit une fois reçue : pas de date à venir.", 422)
    if recue < fiche.emise_le.date():
        raise ErreurMetier("reponse_avant_cahier", "Une réponse ne précède pas l'émission du cahier des charges.", 422)
    nom = donnees["assureur"].strip()
    for r in actives(session, fiche):
        if r.assureur.strip().lower() == nom.lower() and (remplace is None or r.id != remplace.id):
            raise ErreurMetier("reponse_existante", f"{nom} a déjà une réponse à ce cahier : corrigez-la.", 409)
    champs_offre = {}
    if offre is not None:
        nom_fichier, contenu = offre
        if not contenu.startswith(b"%PDF"):
            raise ErreurMetier("type_de_piece", "L'offre de l'assureur se joint en PDF.", 422)
        if len(contenu) > TAILLE_MAX_OFFRE:
            raise ErreurMetier("piece_trop_lourde", "Une offre pèse 10 Mo au plus.", 422)
        champs_offre = {"offre_nom_fichier": nom_fichier[:200], "offre_contenu": contenu,
                        "offre_empreinte": hashlib.sha256(contenu).hexdigest()}
    elif remplace is not None and remplace.offre_contenu is not None:
        champs_offre = {"offre_nom_fichier": remplace.offre_nom_fichier, "offre_contenu": remplace.offre_contenu,
                        "offre_empreinte": remplace.offre_empreinte}
    r = ReponseFiche(organisation_id=org.id, fiche_id=fiche.id, **{k: donnees.get(k) for k in CHAMPS},
                     **champs_offre, remplace_id=remplace.id if remplace else None,
                     motif_correction=motif_correction, saisie_par=auteur)
    r.assureur = nom
    _inserer(session, r)
    journaliser(session, org.id, auteur, "reponse.corrigee" if remplace else "reponse.enregistree", r.id,
                {"fiche": str(fiche.id), "assureur": nom})
    return r


def corriger(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
             donnees: dict, motif: str, offre=None) -> ReponseFiche:
    return enregistrer(session, org, auteur, fiche, donnees, offre=offre, remplace=_active(session, fiche, reponse_id),
                       motif_correction=_motif(motif))


def retirer(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
            motif: str) -> ReponseFiche:
    _ouverte(session, fiche)
    a = _active(session, fiche, reponse_id)
    r = ReponseFiche(organisation_id=org.id, fiche_id=fiche.id, **{k: getattr(a, k) for k in CHAMPS},
                     remplace_id=a.id, retrait=True, motif_correction=_motif(motif), saisie_par=auteur)
    _inserer(session, r)
    journaliser(session, org.id, auteur, "reponse.retiree", r.id, {"retire": str(a.id)})
    return r


def choisir(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
            motif: str | None) -> ChoixFiche:
    _ouverte(session, fiche)
    r = _active(session, fiche, reponse_id)
    recommandee = comparer(session, fiche)["recommandee"]
    if str(r.id) != recommandee and not (motif or "").strip():
        raise ErreurMetier("motif_requis", "Ce n'est pas l'offre conforme la moins chère : dites pourquoi vous la "
                           "retenez (la raison figure au dossier).", 422)
    c = ChoixFiche(organisation_id=org.id, fiche_id=fiche.id, reponse_id=r.id, motif=(motif or "").strip() or None,
                   choisi_par=auteur)
    session.add(c)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("fiche_attribuee", "Ce cahier des charges est déjà attribué.", 409) from None
    journaliser(session, org.id, auteur, "fiche.attribuee", fiche.id, {"reponse": str(r.id), "assureur": r.assureur,
                                                                        "recommandee": str(r.id) == recommandee})
    return c


def _ouverte(session: Session, fiche: FicheRegime) -> None:
    if choix(session, fiche) is not None:
        raise ErreurMetier("fiche_attribuee", "Ce cahier des charges est attribué : il ne reçoit plus de réponse et "
                           "ne change plus de choix.", 409)


def _active(session: Session, fiche: FicheRegime, reponse_id: uuid.UUID) -> ReponseFiche:
    r = next((x for x in actives(session, fiche) if x.id == reponse_id), None)
    if r is None:
        raise ErreurMetier("reponse_inactive", "Cette réponse a été corrigée ou retirée, ou n'existe pas : prenez la "
                           "plus récente.", 409)
    return r


def _inserer(session: Session, r: ReponseFiche) -> None:
    session.add(r)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("reponse_inactive", "Cette réponse a déjà été corrigée ou retirée.", 409) from None


def _motif(texte: str | None) -> str:
    if not (texte or "").strip():
        raise ErreurMetier("motif_correction_requis", "Dites pourquoi la réponse est corrigée ou retirée.", 422)
    return texte.strip()


# --- Lire --------------------------------------------------------------------------------------

def conformite(r: ReponseFiche, conditions: dict) -> list[dict]:
    lignes = []
    for critere, libelle, cle, sens in CRITERES:
        demande = conditions.get(cle)
        if demande is None or (sens == "oui" and demande is False):
            continue
        offert = getattr(r, critere)
        if offert is None:
            ok = None
        elif sens == "min":
            ok = offert >= demande - 1e-12
        elif sens == "max":
            ok = offert <= demande + 1e-12
        else:
            ok = offert is True
        lignes.append({"critere": critere, "libelle": libelle, "sens": sens, "demande": demande, "offert": offert,
                       "conforme": ok})
    return lignes


def comparer(session: Session, fiche: FicheRegime, horizon: int = 10, amortissement: int = 3) -> dict:
    rs = actives(session, fiche)
    conformes = {r.id: all(c["conforme"] is True for c in conformite(r, fiche.conditions)) for r in rs}
    if not rs:
        return {"reponses": [], "comparaison": None, "recommandee": None, "rangs": {}}
    etude = etudes.obtenir(session, fiche.etude_id)
    offres = [Offre(nom=r.assureur, taux_garanti=r.taux_garanti, participation_benefices=r.participation_benefices,
                    frais_sur_cotisations=r.frais_sur_cotisations, frais_sur_encours=r.frais_sur_encours) for r in rs]
    resultat = financement.financer(etude, offres=offres, scenarios=None, horizon=horizon,
                                    amortissement_annees=amortissement, taux_actualisation=None, croissance_salaires=None)
    ordre = [n for n in resultat["classement"] if any(r.assureur == n for r in rs)]
    par_nom = {r.assureur: r for r in rs}
    reference = resultat["scenario_de_reference"]
    couts = {o["nom"]: next(s["cout_net_actualise"] for s in o["scenarios"] if s["scenario"] == reference)
             for o in resultat["offres"]}
    classees = [par_nom[n] for n in ordre]
    recommandee = next((r for r in classees if conformes[r.id]), None)
    return {"reponses": classees, "comparaison": resultat, "recommandee": str(recommandee.id) if recommandee else None,
            "rangs": {r.id: i + 1 for i, r in enumerate(classees)}, "couts": couts, "conformes": conformes}


def en_clair(r: ReponseFiche, fiche: FicheRegime, rang: int | None = None, cout: int | None = None) -> dict:
    lignes = conformite(r, fiche.conditions)
    return {
        "id": str(r.id), **{k: (getattr(r, k).isoformat() if isinstance(getattr(r, k), date) else getattr(r, k))
                            for k in CHAMPS},
        "conformite": lignes, "conforme": all(c["conforme"] is True for c in lignes),
        "tardive": r.recue_le > fiche.date_limite_reponse, "rang": rang, "cout_net_actualise": cout,
        "offre": {"nom_fichier": r.offre_nom_fichier, "empreinte": r.offre_empreinte.strip()} if r.offre_contenu else None,
        "remplace_id": str(r.remplace_id) if r.remplace_id else None, "motif_correction": r.motif_correction,
    }


def tout(session: Session, fiche: FicheRegime, horizon: int = 10, amortissement: int = 3) -> dict:
    c = comparer(session, fiche, horizon, amortissement)
    ch = choix(session, fiche)
    retenue = session.get(ReponseFiche, ch.reponse_id) if ch else None
    return {
        "fiche_id": str(fiche.id), "date_limite_reponse": fiche.date_limite_reponse.isoformat(),
        "conditions": fiche.conditions,
        "reponses": [en_clair(r, fiche, c["rangs"][r.id], c["couts"].get(r.assureur)) for r in c["reponses"]],
        "recommandee": c["recommandee"], "comparaison": c["comparaison"],
        "choix": {"reponse_id": str(ch.reponse_id), "assureur": retenue.assureur, "motif": ch.motif,
                  "choisi_le": ch.choisi_le.isoformat(), "recommandee": str(ch.reponse_id) == c["recommandee"]}
        if ch else None,
    }
