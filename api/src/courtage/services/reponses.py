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
from courtage.langue import t

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
                motif_correction: str | None = None, consultation_id: uuid.UUID | None = None,
                pour_comparaison: bool = False) -> ReponseFiche:
    """`auteur` : le conseiller qui saisit ; vide quand l'assureur dépose lui-même par son lien (`consultation_id`).
    `pour_comparaison` : un devis que l'entreprise a reçu directement et ajoute pour comparer ; classé, jamais retenu."""
    _ouverte(session, fiche)
    recue = donnees["recue_le"]
    if recue > date.today():
        raise ErreurMetier("date_a_venir", t("Une réponse se saisit une fois reçue : pas de date à venir.",
                                              "A response is entered once received: no future date."), 422)
    if recue < fiche.emise_le.date() and not pour_comparaison:     # un devis reçu directement peut précéder le cahier
        raise ErreurMetier("reponse_avant_cahier", t("Une réponse ne précède pas l'émission du cahier des charges.",
                                                      "A response cannot be dated before the tender specifications "
                                                      "were issued."), 422)
    nom = donnees["assureur"].strip()
    for r in actives(session, fiche):
        if r.assureur.strip().lower() == nom.lower() and (remplace is None or r.id != remplace.id):
            raise ErreurMetier("reponse_existante", t(f"{nom} a déjà une réponse à ce cahier : corrigez-la.",
                                                       f"{nom} already has a response to these specifications: "
                                                       "correct it."), 409)
    champs_offre = {}
    if offre is not None:
        nom_fichier, contenu = offre
        if not contenu.startswith(b"%PDF"):
            raise ErreurMetier("type_de_piece", t("L'offre de l'assureur se joint en PDF.",
                                                   "The insurer's offer must be attached as a PDF."), 422)
        if len(contenu) > TAILLE_MAX_OFFRE:
            raise ErreurMetier("piece_trop_lourde", t("Une offre pèse 10 Mo au plus.",
                                                       "An offer can be 10 MB at most."), 422)
        champs_offre = {"offre_nom_fichier": nom_fichier[:200], "offre_contenu": contenu,
                        "offre_empreinte": hashlib.sha256(contenu).hexdigest()}
    elif remplace is not None and remplace.offre_contenu is not None:
        champs_offre = {"offre_nom_fichier": remplace.offre_nom_fichier, "offre_contenu": remplace.offre_contenu,
                        "offre_empreinte": remplace.offre_empreinte}
    r = ReponseFiche(organisation_id=org.id, fiche_id=fiche.id, **{k: donnees.get(k) for k in CHAMPS},
                     **champs_offre, remplace_id=remplace.id if remplace else None,
                     motif_correction=motif_correction, saisie_par=auteur, consultation_id=consultation_id,
                     pour_comparaison=pour_comparaison or bool(remplace and remplace.pour_comparaison))
    r.assureur = nom
    _inserer(session, r)
    journaliser(session, org.id, auteur, "reponse.corrigee" if remplace else "reponse.enregistree", r.id,
                {"fiche": str(fiche.id), "assureur": nom})
    return r


def ajouter_pour_comparaison(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, donnees: dict,
                             offre: tuple[str, bytes] | None = None) -> ReponseFiche:
    """L'entreprise ajoute un devis reçu directement, pour le comparer aux offres que son conseiller lui a apportées.
    Pas avant : la comparaison commence avec les offres du conseiller."""
    if not any(not r.pour_comparaison for r in actives(session, fiche)):
        raise ErreurMetier("aucune_offre_du_conseiller",
                           t("La comparaison s'ouvre avec les offres que votre conseiller vous apporte : aucune n'est "
                             "encore arrivée.",
                             "The comparison opens with the offers your adviser brings you: none has arrived yet."), 409)
    return enregistrer(session, org, auteur, fiche, donnees, offre=offre, pour_comparaison=True)


def retirer_comparaison(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime,
                        reponse_id: uuid.UUID) -> ReponseFiche:
    """L'entreprise retire l'offre qu'elle avait ajoutée ; jamais une offre de la consultation."""
    if not _active(session, fiche, reponse_id).pour_comparaison:
        raise ErreurMetier("acces_refuse", t("Seul le conseiller retire une offre de la consultation.",
                                             "Only the adviser withdraws an offer from the tender."), 403)
    return retirer(session, org, auteur, fiche, reponse_id, "Retirée par l'entreprise (offre pour comparaison).")


def corriger(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
             donnees: dict, motif: str, offre=None) -> ReponseFiche:
    return enregistrer(session, org, auteur, fiche, donnees, offre=offre, remplace=_active(session, fiche, reponse_id),
                       motif_correction=_motif(motif))


def retirer(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
            motif: str) -> ReponseFiche:
    _ouverte(session, fiche)
    a = _active(session, fiche, reponse_id)
    r = ReponseFiche(organisation_id=org.id, fiche_id=fiche.id, **{k: getattr(a, k) for k in CHAMPS},
                     remplace_id=a.id, retrait=True, motif_correction=_motif(motif), saisie_par=auteur,
                     pour_comparaison=a.pour_comparaison)
    _inserer(session, r)
    journaliser(session, org.id, auteur, "reponse.retiree", r.id, {"retire": str(a.id)})
    return r


def choisir(session: Session, org: Organisation, auteur: uuid.UUID, fiche: FicheRegime, reponse_id: uuid.UUID,
            motif: str | None) -> ChoixFiche:
    _ouverte(session, fiche)
    r = _active(session, fiche, reponse_id)
    if r.pour_comparaison:
        raise ErreurMetier("offre_pour_comparaison",
                           t("Une offre ajoutée pour comparaison ne se retient pas : demandez à votre conseiller de "
                             "consulter cet assureur, son offre entrera alors dans la consultation.",
                             "An offer added for comparison cannot be chosen: ask your adviser to consult this "
                             "insurer, and its offer will then enter the tender."), 409)
    recommandee = comparer(session, fiche)["recommandee"]
    if str(r.id) != recommandee and not (motif or "").strip():
        raise ErreurMetier("motif_requis", t("Ce n'est pas l'offre conforme au meilleur rendement net : dites pourquoi "
                                             "vous la retenez (la raison figure au dossier).",
                                             "This is not the compliant offer with the best net return: say why you "
                                             "are choosing it (the reason goes on file)."), 422)
    c = ChoixFiche(organisation_id=org.id, fiche_id=fiche.id, reponse_id=r.id, motif=(motif or "").strip() or None,
                   choisi_par=auteur)
    session.add(c)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("fiche_attribuee", t("Ce cahier des charges est déjà attribué.",
                                                 "These tender specifications have already been awarded."),
                           409) from None
    journaliser(session, org.id, auteur, "fiche.attribuee", fiche.id, {"reponse": str(r.id), "assureur": r.assureur,
                                                                        "recommandee": str(r.id) == recommandee})
    from . import avis
    avis.prevoir(session, "offre_choisie", avis.conseillers(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom, fiche=fiche.id)
    return c


def _ouverte(session: Session, fiche: FicheRegime) -> None:
    if choix(session, fiche) is not None:
        raise ErreurMetier("fiche_attribuee", t("Ce cahier des charges est attribué : il ne reçoit plus de réponse et "
                                                "ne change plus de choix.",
                                                "These tender specifications have been awarded: they take no more "
                                                "responses and the choice no longer changes."), 409)


def _active(session: Session, fiche: FicheRegime, reponse_id: uuid.UUID) -> ReponseFiche:
    r = next((x for x in actives(session, fiche) if x.id == reponse_id), None)
    if r is None:
        raise ErreurMetier("reponse_inactive", t("Cette réponse a été corrigée ou retirée, ou n'existe pas : prenez la "
                                                 "plus récente.",
                                                 "This response has been corrected or withdrawn, or does not exist: "
                                                 "use the most recent one."), 409)
    return r


def _inserer(session: Session, r: ReponseFiche) -> None:
    session.add(r)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("reponse_inactive", t("Cette réponse a déjà été corrigée ou retirée.",
                                                  "This response has already been corrected or withdrawn."),
                           409) from None


def _motif(texte: str | None) -> str:
    if not (texte or "").strip():
        raise ErreurMetier("motif_correction_requis", t("Dites pourquoi la réponse est corrigée ou retirée.",
                                                         "Say why the response is being corrected or withdrawn."),
                           422)
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
        return {"reponses": [], "comparaison": None, "recommandee": None, "rangs": {}, "couts": {}, "rendements": {}}
    etude = etudes.obtenir(session, fiche.etude_id)
    offres = [Offre(nom=r.assureur, taux_garanti=r.taux_garanti, participation_benefices=r.participation_benefices,
                    frais_sur_cotisations=r.frais_sur_cotisations, frais_sur_encours=r.frais_sur_encours) for r in rs]
    resultat = financement.financer(etude, offres=offres, scenarios=None, horizon=horizon,
                                    amortissement_annees=amortissement, taux_actualisation=None, croissance_salaires=None)
    # Le classement : par rendement net décroissant (ce que l'offre rapporte au fonds, tous frais payés).
    ordre = [n for n in resultat["classement_rendement"] if any(r.assureur == n for r in rs)]
    par_nom = {r.assureur: r for r in rs}
    reference = resultat["scenario_de_reference"]
    de_reference = {o["nom"]: next(s for s in o["scenarios"] if s["scenario"] == reference) for o in resultat["offres"]}
    couts = {n: s["cout_net_actualise"] for n, s in de_reference.items()}
    rendements = {n: {"rendement_net": s["rendement_net"], "taux_servi": s["taux_servi"]} for n, s in de_reference.items()}
    classees = [par_nom[n] for n in ordre]
    # La recommandée : la meilleure des conformes que la consultation a apportées (une offre ajoutée pour comparaison
    # se classe, elle ne se recommande pas).
    recommandee = next((r for r in classees if conformes[r.id] and not r.pour_comparaison), None)
    return {"reponses": classees, "comparaison": resultat, "recommandee": str(recommandee.id) if recommandee else None,
            "rangs": {r.id: i + 1 for i, r in enumerate(classees)}, "couts": couts, "rendements": rendements,
            "conformes": conformes}


def en_clair(r: ReponseFiche, fiche: FicheRegime, rang: int | None = None, cout: int | None = None,
             rendement: dict | None = None) -> dict:
    lignes = conformite(r, fiche.conditions)
    return {
        "id": str(r.id), **{k: (getattr(r, k).isoformat() if isinstance(getattr(r, k), date) else getattr(r, k))
                            for k in CHAMPS},
        "conformite": lignes, "conforme": all(c["conforme"] is True for c in lignes),
        "tardive": r.recue_le > fiche.date_limite_reponse, "rang": rang, "cout_net_actualise": cout,
        "offre": {"nom_fichier": r.offre_nom_fichier, "empreinte": r.offre_empreinte.strip()} if r.offre_contenu else None,
        "remplace_id": str(r.remplace_id) if r.remplace_id else None, "motif_correction": r.motif_correction,
        "deposee_par_assureur": r.consultation_id is not None, "pour_comparaison": r.pour_comparaison,
        "rendement_net": (rendement or {}).get("rendement_net"), "taux_servi": (rendement or {}).get("taux_servi"),
    }


def tout(session: Session, fiche: FicheRegime, horizon: int = 10, amortissement: int = 3) -> dict:
    c = comparer(session, fiche, horizon, amortissement)
    ch = choix(session, fiche)
    retenue = session.get(ReponseFiche, ch.reponse_id) if ch else None
    return {
        "fiche_id": str(fiche.id), "date_limite_reponse": fiche.date_limite_reponse.isoformat(),
        "conditions": fiche.conditions,
        "reponses": [en_clair(r, fiche, c["rangs"][r.id], c["couts"].get(r.assureur), c["rendements"].get(r.assureur))
                     for r in c["reponses"]],
        "recommandee": c["recommandee"], "comparaison": c["comparaison"],
        "choix": {"reponse_id": str(ch.reponse_id), "assureur": retenue.assureur, "motif": ch.motif,
                  "choisi_le": ch.choisi_le.isoformat(), "recommandee": str(ch.reponse_id) == c["recommandee"]}
        if ch else None,
    }
