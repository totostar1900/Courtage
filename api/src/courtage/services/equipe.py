"""L'équipe d'un dossier : qui la voit, qui la gère, et ce qu'on peut changer.

- **Les droits** : administrateur de l'entreprise, contributeur, lecture seule, conseiller. **La fonction** est libre.
- **Qui gère qui** : le conseiller (ou la plateforme) gère tout le monde ; l'administrateur de l'entreprise gère ses
  collègues (jamais un conseiller) ; les autres ne gèrent personne.
- **Garde-fous** : on ne retire ni ne rétrograde le dernier administrateur de l'entreprise ni le dernier conseiller.
  Un membre retiré garde son nom au journal, pour ce qu'il a fait. Le numéro de téléphone est l'identité de
  connexion : il ne se modifie pas ; on retire la personne et on l'inscrit avec son nouveau numéro.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from courtage.auth.telephone import normaliser
from courtage.db import Adhesion, Organisation, Utilisateur
from courtage.erreurs import ErreurMetier
from courtage.langue import t

from . import journaliser

DROITS_CLIENT = ("admin_client", "contributeur_client", "lecteur_client")
DROITS = (*DROITS_CLIENT, "conseiller")
LIBELLES = {"admin_client": "Administrateur de l'entreprise", "contributeur_client": "Contributeur",
            "lecteur_client": "Lecture seule", "conseiller": "Conseiller"}
_LIBELLES_EN = {"admin_client": "Company administrator", "contributeur_client": "Contributor",
                "lecteur_client": "Read-only", "conseiller": "Adviser"}
FONCTIONS = ("DRH", "DG", "DAF", "Directeur administratif", "Comptable", "Responsable paie", "Juriste",
             "Représentant du personnel", "Expert-comptable", "Commissaire aux comptes")


def libelle(role: str) -> str:
    """Le libellé d'un droit, dans la langue de la requête."""
    return t(LIBELLES[role], _LIBELLES_EN[role])


def droits_attribuables(role_appelant: str | None, admin_plateforme: bool) -> tuple[str, ...]:
    """Les droits que l'appelant peut donner : tous pour le conseiller et la plateforme, ceux de l'entreprise pour son
    administrateur, aucun pour les autres."""
    if admin_plateforme or role_appelant == "conseiller":
        return DROITS
    if role_appelant == "admin_client":
        return DROITS_CLIENT
    return ()


def _peut_gerer(role_appelant: str | None, admin_plateforme: bool, role_cible: str) -> bool:
    return role_cible in droits_attribuables(role_appelant, admin_plateforme)


def _compte(session: Session, org_id: uuid.UUID, role: str) -> int:
    return session.scalar(select(func.count()).select_from(Adhesion)
                          .where(Adhesion.organisation_id == org_id, Adhesion.role == role)) or 0


def lister(session: Session, org: Organisation, moi: Utilisateur, role_appelant: str | None) -> dict:
    rangs = session.execute(select(Utilisateur, Adhesion).join(Adhesion, Adhesion.utilisateur_id == Utilisateur.id)
                            .where(Adhesion.organisation_id == org.id).order_by(Adhesion.cree_le)).all()
    admin = moi.admin_plateforme
    membres = []
    for u, a in rangs:
        gere = _peut_gerer(role_appelant, admin, a.role)
        dernier = a.role in ("admin_client", "conseiller") and _compte(session, org.id, a.role) == 1
        membres.append({
            "id": str(u.id), "nom": u.nom_affiche or u.email or u.telephone, "email": u.email,
            "telephone": u.telephone, "role": a.role, "droits": libelle(a.role), "fonction": a.fonction,
            "moi": u.id == moi.id,
            "modifiable": gere,
            "retirable": gere and not dernier,
            "raison_retrait": None if not gere else (t(f"Le dernier {LIBELLES[a.role].lower()} du dossier reste.",
                                                       f"The last {_LIBELLES_EN[a.role].lower()} of the file stays.")
                                                     if dernier else None),
        })
    return {"membres": membres, "droits_attribuables": [{"role": r, "libelle": libelle(r)}
                                                        for r in droits_attribuables(role_appelant, admin)],
            "fonctions": list(FONCTIONS)}


def inscrire(session: Session, org: Organisation, auteur: Utilisateur, role_appelant: str | None, *, telephone: str,
             nom_affiche: str, role: str, fonction: str | None) -> dict:
    if not _peut_gerer(role_appelant, auteur.admin_plateforme, role):
        raise ErreurMetier("acces_refuse", t("Vous ne pouvez pas inscrire quelqu'un avec ces droits.", "You cannot add someone with these rights."), 403)
    try:
        telephone = normaliser(telephone)
    except ValueError:
        raise ErreurMetier("telephone_invalide", t("Numéro de téléphone invalide.", "Invalid phone number."), 422) from None
    membre = session.scalars(select(Utilisateur).where(Utilisateur.telephone == telephone)).first()
    if membre is None:
        membre = Utilisateur(telephone=telephone, nom_affiche=nom_affiche.strip())
        session.add(membre)
        session.flush()
    if session.get(Adhesion, (membre.id, org.id)) is not None:
        raise ErreurMetier("deja_membre", t("Cette personne est déjà membre du dossier.", "This person is already a member of the file."), 409)
    session.add(Adhesion(utilisateur_id=membre.id, organisation_id=org.id, role=role,
                         fonction=(fonction or "").strip() or None))
    session.flush()
    journaliser(session, org.id, auteur.id, "membre.inscrit", membre.id, {"role": role, "fonction": fonction})
    return {"utilisateur_id": str(membre.id), "telephone": telephone, "role": role}


def modifier(session: Session, org: Organisation, auteur: Utilisateur, role_appelant: str | None,
             cible_id: uuid.UUID, *, nom_affiche: str | None, fonction: str | None, role: str | None) -> None:
    a = _adhesion(session, org, cible_id)
    if not _peut_gerer(role_appelant, auteur.admin_plateforme, a.role):
        raise ErreurMetier("acces_refuse", t("Vous ne gérez pas ce membre.", "You do not manage this member."), 403)
    avant = {"role": a.role, "fonction": a.fonction}
    if role is not None and role != a.role:
        if not _peut_gerer(role_appelant, auteur.admin_plateforme, role):
            raise ErreurMetier("acces_refuse", t("Vous ne pouvez pas donner ces droits.", "You cannot grant these rights."), 403)
        if a.role in ("admin_client", "conseiller") and _compte(session, org.id, a.role) == 1:
            raise ErreurMetier("dernier_du_role", t(f"C'est le dernier {LIBELLES[a.role].lower()} du dossier : en "
                                                    "désigner un autre d'abord.",
                                                    f"This is the last {_LIBELLES_EN[a.role].lower()} of the file: "
                                                    "appoint another one first."), 409)
        a.role = role
    if fonction is not None:
        a.fonction = fonction.strip() or None
    if nom_affiche is not None and nom_affiche.strip():
        u = session.get(Utilisateur, cible_id)
        autres = session.scalar(select(func.count()).select_from(Adhesion)
                                .where(Adhesion.utilisateur_id == cible_id, Adhesion.organisation_id != org.id)) or 0
        if autres and nom_affiche.strip() != (u.nom_affiche or ""):
            raise ErreurMetier("nom_partage", t("Cette personne suit d'autres dossiers : son nom se change depuis son "
                                                "propre compte.", "This person follows other files: their name is "
                                                "changed from their own account."), 409)
        u.nom_affiche = nom_affiche.strip()
    session.flush()
    journaliser(session, org.id, auteur.id, "membre.modifie", cible_id,
                {"avant": avant, "apres": {"role": a.role, "fonction": a.fonction}})


def retirer(session: Session, org: Organisation, auteur: Utilisateur, role_appelant: str | None,
            cible_id: uuid.UUID) -> None:
    a = _adhesion(session, org, cible_id)
    if not _peut_gerer(role_appelant, auteur.admin_plateforme, a.role):
        raise ErreurMetier("acces_refuse", t("Vous ne gérez pas ce membre.", "You do not manage this member."), 403)
    if a.role in ("admin_client", "conseiller") and _compte(session, org.id, a.role) == 1:
        raise ErreurMetier("dernier_du_role", t(f"C'est le dernier {LIBELLES[a.role].lower()} du dossier : il reste.",
                                             f"This is the last {_LIBELLES_EN[a.role].lower()} of the file: they stay."), 409)
    session.delete(a)
    session.flush()
    journaliser(session, org.id, auteur.id, "membre.retire", cible_id, {"role": a.role, "fonction": a.fonction})


def _adhesion(session: Session, org: Organisation, cible_id: uuid.UUID) -> Adhesion:
    a = session.get(Adhesion, (cible_id, org.id))
    if a is None:
        raise ErreurMetier("introuvable", t("Ce membre ne suit pas le dossier.", "This member does not follow the file."), 404)
    return a
