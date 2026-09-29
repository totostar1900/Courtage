"""La clôture du placement : la police, ses pièces, les appels de prime, les virements déclarés, les relevés du fonds.

**La plateforme ne paie rien.** Les primes partent par virement, de la banque de l'entreprise au compte de
l'assureur ; ici, on range l'appel, on montre ses coordonnées à l'écran, on reçoit la déclaration du virement et la
quittance. Chaque appel est confronté au registre des comptes (`comptes_assureurs`) : un compte différent ou inconnu
se lève par un contre-appel, jamais par un clic — c'est le moment que vise la fraude au changement de RIB.

Le statut d'une police se CALCULE sur ses faits (pièces, signature, première prime encaissée, date d'effet) ; rien ne
se coche à la main. Spécification : docs/specs/2026-09-29-cloture-du-placement-design.md.
"""
import hashlib
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from courtage.db import AppelPrime, ChoixFiche, Etude, Organisation, PiecePolice, Police, ReponseFiche, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.langue import t

from . import avis, comptes_assureurs, journaliser

PERIODICITES = ("annuelle", "semestrielle", "trimestrielle", "mensuelle", "unique")
NATURES = ("police", "police_signee", "avenant", "appel", "avis_virement", "quittance", "releve")
NATURES_DE_L_APPEL = ("appel", "avis_virement", "quittance")
TYPES = {"application/pdf", "image/jpeg", "image/png"}
TAILLE_MAX = 10 * 1024 * 1024


def _libelles() -> dict[str, str]:
    return {"retenue": t("Offre retenue", "Offer chosen"), "recue": t("Police reçue", "Policy received"),
            "signee": t("Signée", "Signed"),
            "premiere_prime": t("Première prime encaissée", "First premium received"),
            "en_vigueur": t("En vigueur", "In force")}


# --- La police -------------------------------------------------------------------------------

def obtenir(session: Session, police_id: uuid.UUID) -> Police:
    p = session.get(Police, police_id)
    if p is None:
        raise Introuvable("Police")
    return p


def creer(session: Session, org: Organisation, auteur: uuid.UUID, *, choix_id: uuid.UUID | None,
          assureur: str | None, date_effet: date, periodicite: str, numero_police: str | None) -> Police:
    """Depuis l'offre choisie (l'assureur en est repris), ou à la main pour un contrat placé autrement."""
    if periodicite not in PERIODICITES:
        raise ErreurMetier("periodicite_inconnue", t("Périodicité : annuelle, semestrielle, trimestrielle, mensuelle "
                                                      "ou prime unique.", "Frequency: annual, half-yearly, quarterly, "
                                                      "monthly or single premium."), 422)
    if choix_id is not None:
        choix = session.get(ChoixFiche, choix_id)
        if choix is None:
            raise Introuvable("Choix")
        assureur = session.get(ReponseFiche, choix.reponse_id).assureur
    assureur = (assureur or "").strip()
    if len(assureur) < 2:
        raise ErreurMetier("assureur_requis", t("Nommer l'assureur.", "Name the insurer."), 422)
    p = Police(organisation_id=org.id, choix_id=choix_id, assureur=assureur, date_effet=date_effet,
               periodicite=periodicite, numero_police=(numero_police or "").strip() or None, cree_par=auteur)
    session.add(p)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError:
        raise ErreurMetier("police_existante", t("Une police existe déjà pour cette offre.",
                                                 "A policy already exists for this offer."), 409) from None
    journaliser(session, org.id, auteur, "police.creee", p.id, {"assureur": assureur, "choix": str(choix_id) if choix_id else None})
    return p


def numeroter(session: Session, org: Organisation, auteur: uuid.UUID, p: Police, numero_police: str) -> Police:
    numero = (numero_police or "").strip()
    if not numero:
        raise ErreurMetier("numero_requis", t("Le numéro de la police.", "The policy number."), 422)
    p.numero_police = numero
    session.flush()
    journaliser(session, org.id, auteur, "police.numerotee", p.id, {"numero": numero})
    return p


def deposer(session: Session, org: Organisation, auteur: uuid.UUID, p: Police, *, nature: str, contenu: bytes,
            nom_fichier: str, type_contenu: str, appel: AppelPrime | None = None, releve_le: date | None = None,
            montant_fonds: int | None = None, aujourd_hui: date) -> PiecePolice:
    if nature not in NATURES:
        raise ErreurMetier("nature_inconnue", t("Nature de pièce inconnue.", "Unknown document type."), 422)
    if type_contenu not in TYPES:
        raise ErreurMetier("format_refuse", t("Un PDF, un JPEG ou un PNG.", "A PDF, JPEG or PNG."), 422)
    if not contenu or len(contenu) > TAILLE_MAX:
        raise ErreurMetier("taille_refusee", t("Un fichier de 10 Mo au plus.", "A file of 10 MB at most."), 422)
    if (nature in NATURES_DE_L_APPEL) != (appel is not None):
        raise ErreurMetier("appel_requis" if appel is None else "appel_inattendu",
                           t("Un appel, un avis de virement ou une quittance se rattache à un appel de prime ; les "
                             "autres pièces, à la police.",
                             "A premium call, a transfer advice or a receipt belongs to a premium call; other "
                             "documents belong to the policy."), 422)
    if appel is not None and appel.police_id != p.id:
        raise Introuvable("Appel de prime")
    if nature == "releve":
        if releve_le is None or montant_fonds is None or montant_fonds < 0:
            raise ErreurMetier("releve_incomplet", t("Un relevé porte sa date et le montant du fonds qu'il affiche.",
                                                     "A statement carries its date and the fund amount it shows."), 422)
        if releve_le > aujourd_hui:
            raise ErreurMetier("date_future", t("Un relevé ne peut pas être daté du futur.",
                                                "A statement cannot be dated in the future."), 422)
    else:
        releve_le = montant_fonds = None
    piece = PiecePolice(organisation_id=org.id, police_id=p.id, appel_id=appel.id if appel else None, nature=nature,
                        nom_fichier=(nom_fichier or nature)[:200], type_contenu=type_contenu, contenu=contenu,
                        empreinte=hashlib.sha256(contenu).hexdigest(), releve_le=releve_le,
                        montant_fonds=montant_fonds, depose_par=auteur)
    session.add(piece)
    session.flush()
    journaliser(session, org.id, auteur, f"police.piece_{nature}", p.id, {"piece": str(piece.id), "empreinte": piece.empreinte})
    if nature == "police":
        avis.prevoir(session, "police_recue", avis.entreprise(session, org.id), auteur=auteur, org=org.id,
                     entreprise=org.nom, assureur=p.assureur)
    return piece


def piece(session: Session, p: Police, piece_id: uuid.UUID) -> PiecePolice:
    x = session.get(PiecePolice, piece_id)
    if x is None or x.police_id != p.id:
        raise Introuvable("Pièce")
    return x


def signer(session: Session, org: Organisation, auteur: uuid.UUID, p: Police, *, signee_le: date,
           aujourd_hui: date) -> Police:
    """La police se signe chez l'assureur ; ici, on déclare la date. Il faut l'avoir reçue d'abord."""
    if p.signee_le is not None:
        raise ErreurMetier("deja_signee", t("La signature de cette police est déjà enregistrée.",
                                            "This policy's signature is already recorded."), 409)
    if not _pieces(session, p, "police"):
        raise ErreurMetier("police_non_recue", t("Déposer d'abord la police reçue de l'assureur.",
                                                 "First upload the policy received from the insurer."), 409)
    if signee_le > aujourd_hui:
        raise ErreurMetier("date_future", t("La signature a eu lieu : sa date ne peut pas être future.",
                                            "The signature has taken place: its date cannot be in the future."), 422)
    p.signee_le, p.signee_par = signee_le, auteur
    session.flush()
    journaliser(session, org.id, auteur, "police.signee", p.id, {"le": signee_le.isoformat()})
    return p


def _pieces(session: Session, p: Police, *natures: str) -> list[PiecePolice]:
    return list(session.scalars(select(PiecePolice).where(PiecePolice.police_id == p.id, PiecePolice.nature.in_(natures))
                                .order_by(PiecePolice.depose_le)))


def _appels(session: Session, p: Police) -> list[AppelPrime]:
    return list(session.scalars(select(AppelPrime).where(AppelPrime.police_id == p.id)
                                .order_by(AppelPrime.echeance, AppelPrime.cree_le)))


def statut(session: Session, p: Police, aujourd_hui: date) -> dict:
    """Les étapes, chacune faite ou non avec sa date ; le statut est la dernière étape faite."""
    recue = _pieces(session, p, "police")
    premiere = next((a for a in _appels(session, p) if a.premiere), None)
    encaissee = premiere.encaisse_le if premiere and premiere.confirme_le else None
    en_vigueur = (max(p.signee_le, encaissee, p.date_effet)
                  if p.signee_le and encaissee and p.date_effet <= aujourd_hui else None)
    faits = [("retenue", p.cree_le.date()), ("recue", recue[0].depose_le.date() if recue else None),
             ("signee", p.signee_le), ("premiere_prime", encaissee), ("en_vigueur", en_vigueur)]
    libelles = _libelles()
    etapes = [{"code": c, "libelle": libelles[c], "fait": le is not None, "le": le.isoformat() if le else None}
              for c, le in faits]
    courant = [e for e in etapes if e["fait"]][-1]
    return {"code": courant["code"], "libelle": courant["libelle"], "etapes": etapes}


# --- Les appels de prime ------------------------------------------------------------------------

def obtenir_appel(session: Session, appel_id: uuid.UUID) -> AppelPrime:
    a = session.get(AppelPrime, appel_id)
    if a is None:
        raise Introuvable("Appel de prime")
    return a


def enregistrer_appel(session: Session, org: Organisation, auteur: uuid.UUID, p: Police, *, reference: str,
                      montant: int, echeance: date, premiere: bool, banque: str, titulaire: str, iban: str,
                      bic: str | None) -> AppelPrime:
    """L'appel reçu de l'assureur, avec les coordonnées qu'il porte, confrontées au compte du registre."""
    reference, banque, titulaire = (reference or "").strip(), (banque or "").strip(), (titulaire or "").strip()
    if not reference or len(banque) < 2 or len(titulaire) < 2:
        raise ErreurMetier("champs_requis", t("La référence de l'appel, la banque et le titulaire du compte.",
                                              "The call reference, the bank and the account holder."), 422)
    if montant <= 0:
        raise ErreurMetier("montant_requis", t("Le montant appelé, en F CFA.", "The amount called, in CFA francs."), 422)
    iban = comptes_assureurs.normaliser_iban(iban)
    compte = comptes_assureurs.en_vigueur(session, p.assureur)
    controle = "non_enregistre" if compte is None else ("conforme" if compte.iban == iban else "modifie")
    a = AppelPrime(organisation_id=org.id, police_id=p.id, reference=reference, montant=montant, echeance=echeance,
                   premiere=premiere, banque=banque, titulaire=titulaire, iban=iban,
                   bic=(bic or "").strip().upper() or None, compte_id=compte.id if compte else None, controle=controle,
                   cree_par=auteur)
    session.add(a)
    try:
        with session.begin_nested():
            session.flush()
    except IntegrityError as e:
        premiere_en_double = "appels_prime_une_premiere" in str(e.orig)
        raise ErreurMetier("premiere_existante" if premiere_en_double else "appel_existant",
                           t("Cette police a déjà son appel de première prime." if premiere_en_double
                             else "Un appel porte déjà cette référence sur cette police.",
                             "This policy already has its first-premium call." if premiere_en_double
                             else "A call already has this reference on this policy."), 409) from None
    journaliser(session, org.id, auteur, "appel.enregistre", a.id, {"montant": montant, "controle": controle})
    avis.prevoir(session, "appel_prime", avis.entreprise(session, org.id, ("admin_client", "contributeur_client")),
                 auteur=auteur, org=org.id, entreprise=org.nom)
    return a


def contre_appel(session: Session, org: Organisation, auteur: uuid.UUID, a: AppelPrime, *, aupres: str,
                 telephone: str, le: date, aujourd_hui: date) -> AppelPrime:
    """Le conseiller a rappelé l'assureur, au numéro qu'il connaît, et fait confirmer les coordonnées de l'appel."""
    if a.controle == "conforme":
        raise ErreurMetier("deja_conforme", t("Ces coordonnées sont celles du registre : pas de contre-appel à faire.",
                                              "These details match the register: no call-back needed."), 409)
    if a.contre_appel is not None:
        raise ErreurMetier("contre_appel_fait", t("Le contre-appel de cet appel est déjà enregistré.",
                                                  "This call's call-back is already recorded."), 409)
    if len((aupres or "").strip()) < 2 or sum(ch.isdigit() for ch in telephone or "") < 6:
        raise ErreurMetier("contre_appel_requis", t("Qui avez-vous eu, et à quel numéro ?",
                                                    "Who did you speak to, and on which number?"), 422)
    if le > aujourd_hui:
        raise ErreurMetier("date_future", t("Le contre-appel a eu lieu : sa date ne peut pas être future.",
                                            "The call-back has happened: its date cannot be in the future."), 422)
    qui = session.get(Utilisateur, auteur)
    a.contre_appel = {"aupres": aupres.strip(), "telephone": telephone.strip(), "le": le.isoformat(),
                      "par": (qui.nom_affiche if qui else None) or "—"}
    a.contre_appel_le = datetime.now(timezone.utc)
    session.flush()
    journaliser(session, org.id, auteur, "appel.contre_appel", a.id, {"aupres": aupres.strip(), "le": le.isoformat()})
    return a


def declarer(session: Session, org: Organisation, auteur: uuid.UUID, a: AppelPrime, *, vire_le: date, montant: int,
             reference: str | None, aujourd_hui: date) -> AppelPrime:
    """L'entreprise a viré depuis sa banque : elle le déclare. Un montant différent est un constat, pas un refus."""
    if a.declare_le is not None:
        raise ErreurMetier("deja_declare", t("Le virement de cet appel est déjà déclaré.",
                                             "The transfer for this call is already declared."), 409)
    if vire_le > aujourd_hui:
        raise ErreurMetier("date_future", t("Déclarer un virement une fois fait : sa date ne peut pas être future.",
                                            "Declare a transfer once made: its date cannot be in the future."), 422)
    if montant <= 0:
        raise ErreurMetier("montant_requis", t("Le montant viré, en F CFA.", "The amount transferred, in CFA francs."), 422)
    a.vire_le, a.montant_vire = vire_le, montant
    a.reference_virement = (reference or "").strip() or None
    a.declare_par, a.declare_le = auteur, datetime.now(timezone.utc)
    session.flush()
    journaliser(session, org.id, auteur, "appel.virement_declare", a.id,
                {"montant": montant, "avant_contre_appel": _a_confirmer(a)})
    avis.prevoir(session, "virement_declare", avis.conseillers(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom)
    return a


def confirmer(session: Session, org: Organisation, auteur: uuid.UUID, a: AppelPrime, *, encaisse_le: date,
              aujourd_hui: date) -> AppelPrime:
    """L'assureur a encaissé : sa quittance (ou son relevé) est déposée sur l'appel. Sans pièce, pas de confirmation."""
    if a.confirme_le is not None:
        raise ErreurMetier("deja_confirme", t("L'encaissement de cet appel est déjà confirmé.",
                                              "Receipt of this call is already confirmed."), 409)
    if _a_confirmer(a):
        raise ErreurMetier("contre_appel_requis", t("Les coordonnées de cet appel n'ont pas été confirmées par un "
                                                    "contre-appel : le faire d'abord.",
                                                    "This call's bank details have not been confirmed by a call-back: "
                                                    "do that first."), 409)
    if not session.scalar(select(PiecePolice.id).where(PiecePolice.appel_id == a.id, PiecePolice.nature == "quittance")):
        raise ErreurMetier("quittance_requise", t("Déposer la quittance de l'assureur sur cet appel.",
                                                  "Upload the insurer's receipt on this call."), 409)
    if encaisse_le > aujourd_hui:
        raise ErreurMetier("date_future", t("L'encaissement a eu lieu : sa date ne peut pas être future.",
                                            "The receipt has happened: its date cannot be in the future."), 422)
    a.encaisse_le, a.confirme_par, a.confirme_le = encaisse_le, auteur, datetime.now(timezone.utc)
    session.flush()
    journaliser(session, org.id, auteur, "appel.encaisse", a.id, {"le": encaisse_le.isoformat()})
    avis.prevoir(session, "encaissement_confirme", avis.entreprise(session, org.id), auteur=auteur, org=org.id,
                 entreprise=org.nom)
    return a


def _a_confirmer(a: AppelPrime) -> bool:
    """Les coordonnées de l'appel ne sont pas celles du registre, et personne ne les a fait confirmer."""
    return a.controle != "conforme" and a.contre_appel is None


def etat_appel(a: AppelPrime, aujourd_hui: date) -> str:
    if a.confirme_le:
        return "encaisse"
    if a.declare_le:
        return "declare"
    return "en_retard" if a.echeance < aujourd_hui else "a_payer"


# --- Lire -------------------------------------------------------------------------------------

def _piece_en_clair(x: PiecePolice) -> dict:
    return {"id": str(x.id), "nature": x.nature, "nom_fichier": x.nom_fichier, "depose_le": x.depose_le.isoformat(),
            "appel_id": str(x.appel_id) if x.appel_id else None,
            "releve_le": x.releve_le.isoformat() if x.releve_le else None, "montant_fonds": x.montant_fonds}


def appel_en_clair(session: Session, a: AppelPrime, aujourd_hui: date) -> dict:
    return {
        "id": str(a.id), "reference": a.reference, "montant": a.montant, "echeance": a.echeance.isoformat(),
        "premiere": a.premiere, "etat": etat_appel(a, aujourd_hui),
        "coordonnees": {"banque": a.banque, "titulaire": a.titulaire, "iban": a.iban, "bic": a.bic},
        "controle": a.controle, "ne_pas_payer": _a_confirmer(a) and not a.declare_le and not a.confirme_le,
        "a_confirmer": _a_confirmer(a), "contre_appel": a.contre_appel,
        "virement": None if not a.declare_le else {
            "le": a.vire_le.isoformat(), "montant": a.montant_vire, "reference": a.reference_virement,
            "ecart": a.montant_vire - a.montant},
        "encaisse_le": a.encaisse_le.isoformat() if a.encaisse_le else None,
        "pieces": [_piece_en_clair(x) for x in session.scalars(
            select(PiecePolice).where(PiecePolice.appel_id == a.id).order_by(PiecePolice.depose_le))],
    }


def police_en_clair(session: Session, p: Police, aujourd_hui: date) -> dict:
    return {
        "id": str(p.id), "assureur": p.assureur, "numero_police": p.numero_police,
        "date_effet": p.date_effet.isoformat(), "periodicite": p.periodicite,
        "signee_le": p.signee_le.isoformat() if p.signee_le else None, "choix_id": str(p.choix_id) if p.choix_id else None,
        "statut": statut(session, p, aujourd_hui),
        "pieces": [_piece_en_clair(x) for x in _pieces(session, p, "police", "police_signee", "avenant")],
        "appels": [appel_en_clair(session, a, aujourd_hui) for a in _appels(session, p)],
        "releves": rapprochement(session, p),
    }


def rapprochement(session: Session, p: Police) -> dict:
    """Les relevés de l'assureur, le plus récent d'abord, rapprochés des primes encaissées à leur date et du fonds que
    retient la dernière étude émise. Un écart est un constat."""
    releves = sorted(_pieces(session, p, "releve"), key=lambda x: (x.releve_le, x.depose_le), reverse=True)
    appels = _appels(session, p)
    etude = session.scalars(select(Etude).where(Etude.statut == "emise")
                            .order_by(Etude.date_evaluation.desc(), Etude.emise_le.desc()).limit(1)).first()
    lignes = []
    for r in releves:
        encaissees = sum(a.montant for a in appels if a.confirme_le and a.encaisse_le and a.encaisse_le <= r.releve_le)
        lignes.append({**_piece_en_clair(r), "primes_encaissees": encaissees})
    return {"releves": lignes, "etude": None if etude is None else {
                "id": str(etude.id), "date_evaluation": etude.date_evaluation.isoformat(),
                "fonds_disponible": etude.fonds_disponible,
                "ecart": (lignes[0]["montant_fonds"] - etude.fonds_disponible) if lignes else None}}


def tableau(session: Session, aujourd_hui: date) -> dict:
    polices = list(session.scalars(select(Police).order_by(Police.cree_le.desc())))
    places = {p.choix_id for p in polices if p.choix_id}
    choix = [{"id": str(c.id), "assureur": r.assureur, "fiche_id": str(c.fiche_id), "choisi_le": c.choisi_le.isoformat()}
             for c, r in session.execute(select(ChoixFiche, ReponseFiche)
                                         .join(ReponseFiche, ReponseFiche.id == ChoixFiche.reponse_id)
                                         .order_by(ChoixFiche.choisi_le.desc()))
             if c.id not in places]
    return {"polices": [police_en_clair(session, p, aujourd_hui) for p in polices], "offres_a_placer": choix,
            "periodicites": list(PERIODICITES)}


def alertes(session: Session, aujourd_hui: date) -> list[tuple[str, str, str, str, str]]:
    """(niveau, code, titre, détail, pour) — lues par `services.alertes`."""
    sortie = []
    for p in session.scalars(select(Police)):
        if _pieces(session, p, "police") and p.signee_le is None:
            sortie.append(("attention", "police_a_signer", t("Une police est à signer", "A policy is to be signed"),
                           t(f"La police {p.assureur} est reçue : la signer avec l'assureur, puis en déclarer la date.",
                             f"The {p.assureur} policy has been received: sign it with the insurer, then record the date."),
                           "entreprise"))
        for a in _appels(session, p):
            e = etat_appel(a, aujourd_hui)
            if _a_confirmer(a) and e != "encaisse":
                sortie.append(("grave", "coordonnees_a_confirmer",
                               t("Coordonnées bancaires à confirmer", "Bank details to confirm"),
                               t(f"L'appel {a.reference} ({p.assureur}) porte un compte "
                                 f"{'différent de celui du registre' if a.controle == 'modifie' else 'absent du registre'}"
                                 " : rappeler l'assureur au numéro connu avant tout virement.",
                                 f"Call {a.reference} ({p.assureur}) carries an account "
                                 f"{'different from the one in the register' if a.controle == 'modifie' else 'missing from the register'}"
                                 ": call the insurer back on the known number before any transfer."), "conseiller"))
            if e == "en_retard":
                sortie.append(("grave", "prime_en_retard", t("Une prime est en retard", "A premium is overdue"),
                               t(f"L'appel {a.reference} ({p.assureur}) était dû le {a.echeance:%d/%m/%Y} ; aucun virement "
                                 "n'est déclaré.", f"Call {a.reference} ({p.assureur}) was due on {a.echeance:%d/%m/%Y}; "
                                 "no transfer has been declared."), "entreprise"))
            elif e == "declare":
                sortie.append(("attention", "encaissement_a_confirmer",
                               t("Un virement est à rapprocher", "A transfer is to be reconciled"),
                               t(f"Virement déclaré le {a.vire_le:%d/%m/%Y} pour l'appel {a.reference} : déposer la "
                                 "quittance de l'assureur pour confirmer l'encaissement.",
                                 f"Transfer declared on {a.vire_le:%d/%m/%Y} for call {a.reference}: upload the "
                                 "insurer's receipt to confirm."), "conseiller"))
    return sortie
