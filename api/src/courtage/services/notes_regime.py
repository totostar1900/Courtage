"""Les deux notes d'une version adoptée : ce que l'adoption communique.

- **La note aux salariés** : ce que le régime verse au départ en retraite, catégorie par catégorie, en mois de
  salaire et en mots, avec le rappel que la convention reste un minimum. Aucun chiffre de dette, aucun nom.
- **La note aux assureurs** : le régime tel qu'il faut l'assurer (catégories, barèmes, conditions, événements
  couverts, conventions plancher) et la population par catégorie, sans nom ni salaire individuel.

Chacune est scellée à sa première émission (préfixe NR-), rangée dans `documents`, et rendue telle quelle ensuite :
une note émise cite la version, qui ne se supprime plus.
"""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.actuariat.ifc import mois_dus
from courtage.db import Document, FichierPersonnel, Organisation, Sceau, Utilisateur, VersionRegime
from courtage.erreurs import ErreurMetier
from courtage.referentiel import referentiel_courant

from . import journaliser, rapport, regimes

NATURES = {"salaries": ("note_regime_salaries", "note_salaries.html", "Note aux salariés"),
           "assureurs": ("note_regime_assureurs", "note_assureurs.html", "Note aux assureurs")}
ANCIENNETES = (5, 10, 15, 20, 25, 30)
FONDEMENTS = {"accord_entreprise": "Accord d'entreprise", "contrat_travail": "Contrats de travail", "usage": "Usage",
              "decision_direction": "Décision de la direction"}


def existante(session: Session, version: VersionRegime, nature: str) -> Document | None:
    return session.scalars(select(Document).join(Sceau, Sceau.numero == Document.numero)
                           .where(Document.version_id == version.id, Sceau.nature == NATURES[nature][0])).first()


def emettre(session: Session, org: Organisation, version: VersionRegime, nature: str, auteur,
            config: rapport.ConfigSceau, aujourd_hui: date) -> Document:
    """La note, scellée à la première demande ; la même ensuite."""
    if nature not in NATURES:
        raise ErreurMetier("note_inconnue", "Note inconnue.", 404)
    if version.statut != "adoptee":
        raise ErreurMetier("version_non_adoptee", "Une note se tire d'une version adoptée : l'adopter d'abord.", 409)
    if (d := existante(session, version, nature)) is not None:
        return d
    code, gabarit, titre = NATURES[nature]
    contenu = _contenu(session, org, version, nature, aujourd_hui)
    emetteur = session.get(Utilisateur, auteur)
    resume = {"organisation": org.nom, "pays": org.pays, "regime": contenu["regime"]["nom"],
              "version": version.numero, "en_vigueur_du": version.en_vigueur_du.isoformat(), "note": titre,
              "emis_le": aujourd_hui.isoformat(), "emetteur": rapport.nom_de(emetteur), "probant": config.probant}
    document = rapport.sceller_document(
        session, org, nature=code, empreinte=_empreinte(contenu), resume=resume, config=config, gabarit=gabarit,
        version_id=version.id, prefixe="NR",
        contexte=lambda numero, sceau: {
            "org": org, "c": contenu, "numero": numero, "sceau": sceau, "titre": titre,
            "url_verification": f"{config.url_publique}/verifier/{numero}", "probant": config.probant,
            "emetteur": rapport.nom_de(emetteur), "emis_le": aujourd_hui, "empreinte": _empreinte(contenu)})
    journaliser(session, org.id, auteur, f"regime.{code}", version.id, {"numero": document.numero})
    return document


def emises(session: Session, version: VersionRegime) -> dict:
    return {n: (d.numero if (d := existante(session, version, n)) else None) for n in NATURES}


def _empreinte(contenu: dict) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(contenu, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _contenu(session: Session, org: Organisation, version: VersionRegime, nature: str, jour: date) -> dict:
    regime = session.get(regimes.Regime, version.regime_id)
    ref = referentiel_courant()
    regles = regimes.regles(session, version, version.en_vigueur_du)
    categories = []
    for c in regimes.categories_de(session, version):
        convention = ref.convention(c.convention_code, version.en_vigueur_du)
        r = regles[c.categorie]
        categories.append({
            "categorie": "Tout le personnel" if c.categorie == "*" else c.categorie, "cle": c.categorie,
            "convention": convention.libelle, "convention_code": convention.code, "bareme": c.bareme,
            "anciennete_minimale": c.anciennete_minimale, "plafond_mois": c.plafond_mois,
            "base_salaire": "la moyenne des 12 derniers mois" if c.base_salaire == "moyenne_12_mois" else "le dernier salaire",
            "avec_primes": c.avec_primes, "evenements": list(c.evenements),
            "illustration": [{"anciennete": n, "mois": round(mois_dus(r, n)[0], 2),
                              "convention": round(mois_dus(regimes.Regles(bareme=convention.bareme), n)[0], 2)}
                             for n in ANCIENNETES],
        })
    contenu = {"organisation": {"nom": org.nom, "pays": org.pays},
               "regime": {"nom": regime.nom, "numero": version.numero, "en_vigueur_du": version.en_vigueur_du.isoformat(),
                          "fondement": FONDEMENTS.get(version.fondement, version.fondement),
                          "document_reference": version.document_reference},
               "categories": categories}
    if nature == "assureurs":
        contenu["constats"] = [c for c in regimes.constats(session, version, version.en_vigueur_du)]
        contenu["population"] = _population(session, [c["cle"] for c in categories])
    return contenu


def _population(session: Session, cles: list[str]) -> dict | None:
    """L'effectif par catégorie, tiré du dernier personnel déposé ; aucun nom, aucun salaire individuel."""
    f = session.scalars(select(FichierPersonnel).where(FichierPersonnel.vide_le.is_(None))
                        .order_by(FichierPersonnel.date_donnees.desc()).limit(1)).first()
    if f is None:
        return None
    effectifs: dict[str, int] = {}
    for ligne in f.lignes:
        cat = ligne.get("categorie") if ligne.get("categorie") in cles else "*"
        effectifs[cat] = effectifs.get(cat, 0) + 1
    return {"date_donnees": f.date_donnees.isoformat(), "total": len(f.lignes),
            "par_categorie": [{"categorie": "Autres salariés" if k == "*" else k, "effectif": n}
                              for k, n in sorted(effectifs.items(), key=lambda x: -x[1])]}
