"""Nettoyer un dossier : l'entreprise garde ses documents, la plateforme ne garde que ce qui prouve.

Trois temps : télécharger l'archive (les documents scellés, les études en Excel, un sommaire), choisir ce qui part,
confirmer. Ce qui peut partir :
- **le personnel** : les fichiers s'allègent (lignes vidées, empreinte gardée) ou se suppriment quand rien d'émis ne
  les cite ;
- **les brouillons** : études en brouillon, versions de régime en brouillon ;
- **les études émises** et leur rapport, quand aucun cahier des charges ne les cite. Leur sceau reste : le numéro se
  vérifie toujours, pour la vie de l'entreprise.
Restent toujours : les sceaux et le journal (quelques kilo-octets), les versions adoptées citées, les cahiers, les
contrats, les départs. Le cycle de vie du dossier fait la même chose, d'office, à l'archivage.
"""
import io
import uuid
import zipfile
from datetime import date

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from courtage.db import Document, Etude, FicheRegime, FichierPersonnel, Organisation, Sceau, VersionRegime
from courtage.erreurs import ErreurMetier
from courtage.langue import t

from . import etudes, fichiers, journaliser, regimes

CONFIRMATION = "NETTOYER"


def _etudes_emises_supprimables(session: Session) -> list[Etude]:
    citees = select(FicheRegime.etude_id)
    return list(session.scalars(select(Etude).where(Etude.statut == "emise", Etude.id.not_in(citees))))


def inventaire(session: Session) -> dict:
    """Ce que le dossier contient, et ce que chaque choix ferait partir."""
    fs = fichiers.lister(session)
    emises = session.scalar(select(func.count()).select_from(Etude).where(Etude.statut == "emise")) or 0
    supprimables = _etudes_emises_supprimables(session)
    return {
        "fichiers": {"total": len(fs), "actifs": sum(1 for f in fs if f.vide_le is None),
                     "lignes": sum(len(f.lignes) for f in fs)},
        "brouillons": {
            "etudes": session.scalar(select(func.count()).select_from(Etude).where(Etude.statut == "brouillon")) or 0,
            "versions": session.scalar(select(func.count()).select_from(VersionRegime)
                                       .where(VersionRegime.statut == "analyse")) or 0},
        "etudes_emises": {"total": emises, "supprimables": len(supprimables),
                          "citees_par_un_cahier": emises - len(supprimables)},
        "documents": session.scalar(select(func.count()).select_from(Document)) or 0,
        "confirmation": CONFIRMATION,
    }


def archive(session: Session, org: Organisation, aujourd_hui: date) -> bytes:
    """Tout ce que l'entreprise voudra garder : chaque document scellé (PDF), chaque étude émise (Excel), un sommaire
    des numéros à vérifier."""
    from courtage import exports
    tampon = io.BytesIO()
    lignes = [f"Archive du dossier {org.nom}, le {aujourd_hui:%d/%m/%Y}.", "",
              "Chaque document porte un numéro, vérifiable à tout moment sur la page « Vérifier un document ».", ""]
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        for d in session.scalars(select(Document).order_by(Document.cree_le)):
            nature = session.scalar(select(Sceau.nature).where(Sceau.numero == d.numero)) or "document"
            nom = f"documents/{d.cree_le:%Y-%m-%d}-{nature}-{d.numero}.pdf"
            z.writestr(nom, d.contenu)
            lignes.append(f"{d.numero}  {nature}  {d.cree_le:%d/%m/%Y}  {nom}")
        for e in session.scalars(select(Etude).where(Etude.statut == "emise").order_by(Etude.date_evaluation)):
            clair = etudes.en_clair(session, org, e, aujourd_hui)
            z.writestr(f"etudes/etude-ifc-{e.date_evaluation.isoformat()}.xlsx", exports.etude(clair, org.nom))
        z.writestr("SOMMAIRE.txt", "\n".join(lignes) + "\n")
    return tampon.getvalue()


def nettoyer(session: Session, org: Organisation, auteur: uuid.UUID, *, fichiers_: str | None, brouillons: bool,
             etudes_emises: bool, confirmation: str) -> dict:
    if confirmation.strip().upper() != CONFIRMATION:
        raise ErreurMetier("confirmation_requise", t(f"Écrire « {CONFIRMATION} » pour confirmer.", f"Type “{CONFIRMATION}” to confirm."), 422)
    if fichiers_ not in (None, "alleger", "supprimer"):
        raise ErreurMetier("choix_invalide", t("Le personnel s'allège ou se supprime.", "Staff data is either lightened or deleted."), 422)
    fait = {"etudes_brouillon": 0, "versions_brouillon": 0, "etudes_emises": 0, "fichiers_alleges": 0,
            "fichiers_supprimes": 0}
    if brouillons:
        for v in list(session.scalars(select(VersionRegime).where(VersionRegime.statut == "analyse"))):
            fait["etudes_brouillon"] += regimes.suppression(session, v)["brouillons"]
            regimes.supprimer(session, v, auteur, "admin_client", "nettoyage du dossier")
            fait["versions_brouillon"] += 1
        for e in list(session.scalars(select(Etude).where(Etude.statut == "brouillon"))):
            etudes.supprimer(session, e, auteur)
            fait["etudes_brouillon"] += 1
    if etudes_emises:
        ids = [e.id for e in _etudes_emises_supprimables(session)]
        if ids:
            session.execute(text("SELECT set_config('app.nettoyage', 'oui', true)"))
            session.execute(delete(Document).where(Document.etude_id.in_(ids)))
            session.execute(delete(Etude).where(Etude.id.in_(ids)))
            session.execute(text("SELECT set_config('app.nettoyage', '', true)"))
            fait["etudes_emises"] = len(ids)
    if fichiers_:
        for f in list(session.scalars(select(FichierPersonnel))):
            u = fichiers.usages(session, f)
            if fichiers_ == "supprimer" and not u["etudes_emises"]:
                fichiers.supprimer(session, f, auteur)
                fait["fichiers_supprimes"] += 1
            elif f.vide_le is None:
                fichiers.alleger(session, f, auteur)
                fait["fichiers_alleges"] += 1
    session.flush()
    journaliser(session, org.id, auteur, "dossier.nettoye", org.id, fait)
    return fait
