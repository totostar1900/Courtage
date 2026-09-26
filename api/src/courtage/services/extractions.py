"""Extraction assistée (module `courtage.extraction`) : le branchement sur un dossier client et sur le référentiel.

Pour un CLIENT : la proposition préremplit une version de régime, que la
personne relit et enregistre par la voie habituelle. Pour la PLATEFORME : la
proposition est un fichier de convention du référentiel, au statut « à valider »,
à relire contre le texte primaire avant d'entrer dans `referentiel/donnees/`.

Dans les deux cas : pays de la CEMAC seulement ; un moteur qui envoie le texte à
un tiers ne part qu'avec l'accord explicite de la personne ; seule l'empreinte
du document est gardée.
"""
import hashlib
import re
import unicodedata
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Etude, ExtractionTexte, Organisation
from courtage.erreurs import ErreurMetier
from courtage.extraction import CEMAC, Extracteur, ExtractionImpossible, citation_retrouvee, lire_document, proposer
from courtage.referentiel import referentiel_courant

from . import journaliser

TAILLE_MAX = 10 * 1024 * 1024
FONDEMENTS = {"accord_entreprise": "Accord d'entreprise", "contrat_travail": "Contrats de travail", "usage": "Usage",
              "decision_direction": "Décision de la direction"}


def mode(extracteur: Extracteur) -> dict:
    return {"moteur": extracteur.moteur, "modele": extracteur.modele, "envoie_a_un_tiers": extracteur.envoie_a_un_tiers,
            "pays_couverts": CEMAC}


def _lire(extracteur: Extracteur, contenu: bytes, nom_fichier: str, pays: str, consentement: bool):
    if pays not in CEMAC:
        raise ErreurMetier("hors_cemac", "L'extraction assistée ne traite pour l'instant que les textes des pays de la "
                           "CEMAC.", 409)
    if extracteur.envoie_a_un_tiers and not consentement:
        raise ErreurMetier("consentement_requis", "Ce moteur envoie le texte à un service tiers pour lecture : il faut "
                           "votre accord explicite.", 422)
    if len(contenu) > TAILLE_MAX:
        raise ErreurMetier("document_trop_lourd", "Un document pèse 10 Mo au plus.", 422)
    extension = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    if not contenu.startswith(b"%PDF") and extension not in ("txt", "md"):
        raise ErreurMetier("format_non_pris_en_charge", "Envoyez le texte en PDF (ou en texte brut).", 422)
    document = lire_document(contenu, nom_fichier)
    try:
        extraction = extracteur.extraire(document, pays)
    except ExtractionImpossible as e:
        raise ErreurMetier("extraction_impossible", str(e), 502) from None
    return document, extraction


def pour_un_regime(session: Session, org: Organisation, auteur: uuid.UUID, extracteur: Extracteur, *, contenu: bytes,
                   nom_fichier: str, consentement: bool) -> dict:
    document, extraction = _lire(extracteur, contenu, nom_fichier, org.pays, consentement)
    p = proposer(extraction, document, org.pays, _convention_par_defaut(session, org.pays), FONDEMENTS)
    resultat = {"extraction": extraction.model_dump(mode="json"), "version": p.version,
                "verifications": p.verifications, "constats": p.constats}
    trace = ExtractionTexte(organisation_id=org.id, nom_fichier=nom_fichier[:200],
                            empreinte=hashlib.sha256(contenu).hexdigest(), taille=len(contenu),
                            moteur=extracteur.moteur, modele=extracteur.modele,
                            envoye_a_un_tiers=extracteur.envoie_a_un_tiers, resultat=resultat, cree_par=auteur)
    session.add(trace)
    session.flush()
    journaliser(session, org.id, auteur, "regime.extraction", trace.id,
                {"moteur": extracteur.moteur, "envoye_a_un_tiers": extracteur.envoie_a_un_tiers,
                 "categories": len(p.version.get("categories", []))})
    return {"id": str(trace.id), **mode(extracteur), **resultat}


def _convention_par_defaut(session: Session, pays: str) -> str | None:
    """La convention de la dernière étude ; sinon celle du pays si elle est seule ; sinon au choix de la personne."""
    etude = session.scalars(select(Etude).order_by(Etude.cree_le.desc()).limit(1)).first()
    if etude is not None:
        return etude.convention_code
    du_pays = {c.code for c in referentiel_courant().conventions_du_pays(pays, date.today()) if c.statut == "valide"}
    return du_pays.pop() if len(du_pays) == 1 else None


def pour_le_referentiel(auteur: uuid.UUID, extracteur: Extracteur, session: Session, *, contenu: bytes,
                        nom_fichier: str, consentement: bool, pays: str) -> dict:
    """Une convention collective d'un pays de la CEMAC, proposée pour le référentiel — au statut « à valider »."""
    document, extraction = _lire(extracteur, contenu, nom_fichier, pays, consentement)
    if extraction.pays and extraction.pays != pays:
        raise ErreurMetier("autre_pays", f"Le texte relève de {CEMAC.get(extraction.pays, extraction.pays)}, pas de "
                           f"{CEMAC[pays]}.", 422)
    p = proposer(extraction, document, pays, None, FONDEMENTS)
    generale = next((c for c in p.version.get("categories", []) if c["categorie"] == "*"),
                    (p.version.get("categories") or [None])[0])
    retrouvees = sum(1 for v in p.verifications if v["retrouvee"])
    convention = None
    if generale is not None:
        convention = {
            "pays": pays, "code": f"{pays}_{_slug(extraction.intitule or nom_fichier)}"[:40],
            "libelle": extraction.intitule or nom_fichier, "statut": "a_valider",
            "en_vigueur_du": extraction.date_effet or None, "en_vigueur_au": None,
            "sources": [{"titre": nom_fichier, "url": None, "consulte_le": date.today().isoformat()}],
            "verification": f"Extraction assistée ({extracteur.moteur}{f', {extracteur.modele}' if extracteur.modele else ''}) "
                            f"le {date.today():%d/%m/%Y} : {retrouvees} passage(s) cité(s) sur {len(p.verifications)} "
                            "retrouvé(s) dans le texte. À valider par relecture du texte primaire.",
            "notes": [a.texte for a in extraction.points_d_attention]
                     + [f"Catégorie « {c['categorie']} » : barème distinct, non repris." for c in p.version["categories"]
                        if c is not generale],
            "bareme": generale["bareme"],
        }
    journaliser(session, None, auteur, "referentiel.extraction", pays,
                {"moteur": extracteur.moteur, "fichier": hashlib.sha256(contenu).hexdigest()})
    return {**mode(extracteur), "convention": convention, "verifications": p.verifications, "constats": p.constats,
            "extraction": extraction.model_dump(mode="json")}


def _slug(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode().upper()
    mots = [m for m in re.findall(r"[A-Z0-9]+", t) if m not in {"CONVENTION", "COLLECTIVE", "NATIONALE", "DE", "DU",
                                                                  "DES", "LA", "LE", "LES", "ET", "D", "L", "AU"}]
    return "_".join(mots[:3]) or "CONVENTION"
