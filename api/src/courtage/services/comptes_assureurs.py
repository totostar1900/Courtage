"""Le registre des comptes bancaires des assureurs, tenu par le courtier : la référence contre laquelle chaque appel
de prime est confronté (spec clôture du placement §3).

Un compte s'enregistre avec son **contre-appel** — qui, chez l'assureur, a confirmé ces coordonnées, à quel numéro,
quel jour — parce que c'est précisément un « nouveau RIB » reçu par courriel qui détourne un virement. Un changement
ajoute une ligne qui remplace la précédente ; l'ancienne reste, datée. Le compte en vigueur d'un assureur est la
ligne qu'aucune autre ne remplace.
"""
import re
import unicodedata
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import CompteAssureur, Utilisateur
from courtage.erreurs import ErreurMetier
from courtage.langue import t

from . import journaliser


def cle(assureur: str) -> str:
    """Le nom d'un assureur, pour le retrouver : sans accents, sans espaces ni ponctuation, en majuscules."""
    sans_accents = unicodedata.normalize("NFKD", assureur or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", sans_accents.upper())


def normaliser_iban(saisi: str) -> str:
    compte = re.sub(r"[\s.\-]", "", (saisi or "").upper())
    if not re.fullmatch(r"[A-Z0-9]{10,40}", compte):
        raise ErreurMetier("iban_invalide", t("IBAN ou RIB invalide : 10 à 40 lettres et chiffres.",
                                              "Invalid IBAN or account number: 10 to 40 letters and digits."), 422)
    return compte


def en_vigueur(session: Session, assureur: str) -> CompteAssureur | None:
    remplaces = select(CompteAssureur.remplace_id).where(CompteAssureur.remplace_id.is_not(None))
    return session.scalars(select(CompteAssureur).where(CompteAssureur.assureur_cle == cle(assureur),
                                                        CompteAssureur.id.not_in(remplaces))
                           .order_by(CompteAssureur.enregistre_le.desc()).limit(1)).first()


def enregistrer(session: Session, auteur: uuid.UUID, *, assureur: str, banque: str, titulaire: str, iban: str,
                bic: str | None, verifie_aupres: str, verifie_telephone: str, verifie_le: date,
                note: str | None, aujourd_hui: date) -> CompteAssureur:
    assureur, banque, titulaire = (assureur or "").strip(), (banque or "").strip(), (titulaire or "").strip()
    if len(cle(assureur)) < 2 or len(banque) < 2 or len(titulaire) < 2:
        raise ErreurMetier("champs_requis", t("L'assureur, la banque et le titulaire du compte sont requis.",
                                              "The insurer, the bank and the account holder are required."), 422)
    if len((verifie_aupres or "").strip()) < 2 or len(re.sub(r"\D", "", verifie_telephone or "")) < 6:
        raise ErreurMetier("contre_appel_requis",
                           t("Un compte s'enregistre après un contre-appel : qui, chez l'assureur, a confirmé ces "
                             "coordonnées, et à quel numéro (celui que vous connaissez, pas celui du courriel reçu).",
                             "An account is recorded after a call-back: who at the insurer confirmed these details, "
                             "and on which number (the one you know, not the one in the email received)."), 422)
    if verifie_le > aujourd_hui:
        raise ErreurMetier("date_future", t("Le contre-appel a déjà eu lieu : sa date ne peut pas être future.",
                                            "The call-back has already happened: its date cannot be in the future."), 422)
    actuel = en_vigueur(session, assureur)
    compte = CompteAssureur(
        assureur=assureur, assureur_cle=cle(assureur), banque=banque, titulaire=titulaire, iban=normaliser_iban(iban),
        bic=(bic or "").strip().upper() or None, verifie_aupres=verifie_aupres.strip(),
        verifie_telephone=verifie_telephone.strip(), verifie_le=verifie_le, note=(note or "").strip() or None,
        remplace_id=actuel.id if actuel else None, enregistre_par=auteur)
    session.add(compte)
    session.flush()
    journaliser(session, None, auteur, "compte_assureur.enregistre", compte.id,
                {"assureur": assureur, "remplace": str(actuel.id) if actuel else None})
    return compte


def en_clair(session: Session, c: CompteAssureur) -> dict:
    qui = session.get(Utilisateur, c.enregistre_par)
    return {"id": str(c.id), "assureur": c.assureur, "banque": c.banque, "titulaire": c.titulaire, "iban": c.iban,
            "bic": c.bic, "note": c.note, "remplace_id": str(c.remplace_id) if c.remplace_id else None,
            "contre_appel": {"aupres": c.verifie_aupres, "telephone": c.verifie_telephone,
                             "le": c.verifie_le.isoformat()},
            "enregistre_par": (qui.nom_affiche if qui else None) or "—", "enregistre_le": c.enregistre_le.isoformat()}


def registre(session: Session) -> list[dict]:
    """Chaque assureur avec son compte en vigueur et l'historique de ses changements, le plus récent d'abord."""
    lignes = list(session.scalars(select(CompteAssureur).order_by(CompteAssureur.enregistre_le.desc())))
    remplaces = {c.remplace_id for c in lignes if c.remplace_id}
    par_assureur: dict[str, dict] = {}
    for c in lignes:
        entree = par_assureur.setdefault(c.assureur_cle, {"assureur": c.assureur, "en_vigueur": None, "historique": []})
        if c.id not in remplaces and entree["en_vigueur"] is None:
            entree["en_vigueur"] = en_clair(session, c)
        else:
            entree["historique"].append(en_clair(session, c))
    return sorted(par_assureur.values(), key=lambda e: e["assureur"].lower())
