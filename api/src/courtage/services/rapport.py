"""Rapport d'étude IFC : rendu une fois à l'émission, scellé, conservé, vérifiable.

Le sceau est un HMAC-SHA256, sous une clé que seule la plateforme détient, de
ce que le papier affirme : le numéro, la nature, l'empreinte de l'étude et le
résumé public (organisation, date, dette…). Le PDF, rendu ensuite parce qu'il
imprime le sceau, reçoit sa propre empreinte et sa propre signature. La
vérification publique recalcule les deux : un résumé retouché en base, ou un
PDF retouché, ne passe plus.

Sans clé configurée, une clé de développement est utilisée et le rapport comme
la vérification disent « non probant ». En production, la clé est obligatoire
(`creer_app` refuse de démarrer sans elle).
"""
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime
from importlib.resources import files

from jinja2 import Environment, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from courtage.db import Document, Etude, Organisation, Sceau, Utilisateur
from courtage.erreurs import ErreurMetier, Introuvable
from courtage.referentiel import referentiel_courant

from . import etudes, fichiers

CLE_DE_DEVELOPPEMENT = b"courtage-cle-de-developpement-non-probante"
_ALPHABET = "ACDEFGHJKLMNPQRTUVWXY34679"   # sans 0/O, 1/I, 2/Z, 5/S, 8/B : lisible à voix haute


@dataclass(frozen=True)
class ConfigSceau:
    cle: bytes
    probant: bool
    url_publique: str

    @classmethod
    def depuis(cls, cle: bytes | None, url_publique: str | None) -> "ConfigSceau":
        return cls(cle=cle or CLE_DE_DEVELOPPEMENT, probant=cle is not None,
                   url_publique=(url_publique or "http://localhost:8000").rstrip("/"))


# --- Émission -----------------------------------------------------------------

def sceller(session: Session, org: Organisation, etude: Etude, config: ConfigSceau, aujourd_hui: date) -> Document:
    """Scelle une étude qui vient d'être émise et rend son PDF, dans la même transaction."""
    emetteur = session.get(Utilisateur, etude.emise_par)
    numero = _nouveau_numero(session)
    resume = {
        "organisation": org.nom, "pays": org.pays, "date_evaluation": etude.date_evaluation.isoformat(),
        "convention": etude.convention_code, "effectif": etude.resultats["totaux"]["effectif"],
        "dette": etude.resultats["totaux"]["dette"], "charge": etude.resultats["totaux"]["charge"],
        "cotisation_totale": etude.resultats["totaux"]["cotisation_totale"],
        "emis_le": etude.emise_le.date().isoformat(), "emetteur": nom_de(emetteur), "probant": config.probant,
    }
    return sceller_document(
        session, org, nature="etude_ifc", empreinte=etude.empreinte, resume=resume, config=config,
        gabarit="rapport_ifc.html", etude_id=etude.id,
        contexte=lambda numero, sceau: _contexte(session, org, etude, emetteur, numero, sceau, config, aujourd_hui),
        numero=numero)


def sceller_document(session: Session, org: Organisation, *, nature: str, empreinte: str, resume: dict,
                     config: ConfigSceau, gabarit: str, contexte, etude_id=None, fiche_id=None,
                     numero: str | None = None) -> Document:
    """Signe ce que le papier affirme, rend le PDF (qui imprime le sceau), le signe à son tour, le range.

    `contexte(numero, sceau)` fournit au gabarit ce qu'il affiche."""
    numero = numero or _nouveau_numero(session)
    sceau = _signer(config.cle, numero, nature, empreinte, resume)
    pdf = rendre_pdf(contexte(numero, sceau), gabarit)
    empreinte_document = hashlib.sha256(pdf).hexdigest()
    session.add(Sceau(numero=numero, nature=nature, empreinte=empreinte, sceau=sceau, resume=resume,
                      empreinte_document=empreinte_document,
                      sceau_document=_hmac(config.cle, f"{numero}|{empreinte_document}")))
    session.flush()
    document = Document(organisation_id=org.id, etude_id=etude_id, fiche_id=fiche_id, numero=numero, contenu=pdf,
                        empreinte_document=empreinte_document)
    session.add(document)
    session.flush()
    return document


def document_de(session: Session, etude: Etude) -> Document:
    document = session.scalars(select(Document).where(Document.etude_id == etude.id)).first()
    if document is None:
        raise ErreurMetier("rapport_indisponible", "Le rapport existe une fois l'étude émise.", 404)
    return document


# --- Vérification publique ----------------------------------------------------

def verifier(session: Session, numero: str, config: ConfigSceau) -> dict:
    s = _sceau(session, numero)
    authentique = (
        hmac.compare_digest(s.sceau.strip(), _signer(config.cle, s.numero, s.nature, s.empreinte.strip(), s.resume))
        and s.empreinte_document is not None
        and hmac.compare_digest(s.sceau_document.strip(), _hmac(config.cle, f"{s.numero}|{s.empreinte_document.strip()}"))
    )
    return {
        "numero": s.numero, "nature": s.nature, "emis_le": s.emis_le.isoformat(), "resume": s.resume,
        "authentique": authentique, "probant": authentique and bool(s.resume.get("probant")) and config.probant,
        "empreinte_document": s.empreinte_document.strip() if s.empreinte_document else None,
    }


def est_conforme(session: Session, numero: str, contenu: bytes) -> bool:
    s = _sceau(session, numero)
    return s.empreinte_document is not None and hmac.compare_digest(
        hashlib.sha256(contenu).hexdigest(), s.empreinte_document.strip())


# --- Rendu --------------------------------------------------------------------

def rendre_pdf(contexte: dict, gabarit: str = "rapport_ifc.html") -> bytes:
    from weasyprint import HTML  # import tardif : lourd, et inutile hors émission
    html = gabarits().get_template(gabarit).render(**contexte)
    return HTML(string=html).write_pdf()


def _contexte(session: Session, org: Organisation, etude: Etude, emetteur, numero: str, sceau: str,
              config: ConfigSceau, aujourd_hui: date) -> dict:
    e = etudes.en_clair(session, org, etude, aujourd_hui)
    convention = referentiel_courant().convention(etude.convention_code, etude.convention_du)
    fichier = fichiers.obtenir(session, etude.fichier_id)
    lignes = e["lignes"]
    n = len(lignes) or 1
    return {
        "org": org, "e": e, "convention": convention, "fichier": fichier,
        "masse_salariale": sum(l["salaire_annuel"] or 0 for l in fichier.lignes),
        "age_moyen": sum(l["age"] for l in lignes) / n,
        "anciennete_moyenne": sum(l["anciennete"] for l in lignes) / n,
        "avertissements": [a for a in e["anomalies"] if a["niveau"] == "avertissement"],
        "emetteur": nom_de(emetteur), "numero": numero, "sceau": sceau, "empreinte": etude.empreinte,
        "url_verification": f"{config.url_publique}/verifier/{numero}", "probant": config.probant,
        "emis_le": etude.emise_le,
    }


def gabarits() -> Environment:
    env = Environment(autoescape=select_autoescape(default=True))
    env.loader = _Chargeur()
    env.filters.update(montant=_montant, pct=_pct, date_fr=_date_fr, annees=_annees)
    return env


class _Chargeur:
    def load(self, environment, nom, globals=None):
        source = (files(__package__) / "gabarits" / nom).read_text("utf-8")
        return environment.from_string(source, globals)


def _montant(n) -> str:
    return f"{int(round(n)):,}".replace(",", " ") + " F"


def _pct(x, decimales=1) -> str:
    return f"{x * 100:.{decimales}f}".replace(".", ",") + " %"


def _date_fr(d) -> str:
    if isinstance(d, str):
        d = date.fromisoformat(d[:10])
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _annees(x) -> str:
    return f"{x:.1f}".replace(".", ",") + " ans"


# --- Sceaux -------------------------------------------------------------------

def _signer(cle: bytes, numero: str, nature: str, empreinte: str, resume: dict) -> str:
    canonique = json.dumps(resume, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _hmac(cle, f"{numero}|{nature}|{empreinte}|{canonique}")


def _hmac(cle: bytes, message: str) -> str:
    return hmac.new(cle, message.encode("utf-8"), hashlib.sha256).hexdigest()


def _nouveau_numero(session: Session) -> str:
    for _ in range(10):
        brut = "".join(secrets.choice(_ALPHABET) for _ in range(8))
        numero = f"RL-{brut[:4]}-{brut[4:]}"
        if session.get(Sceau, numero) is None:
            return numero
    raise RuntimeError("impossible d'allouer un numéro de sceau")


def _sceau(session: Session, numero: str) -> Sceau:
    s = session.get(Sceau, numero.strip().upper())
    if s is None:
        raise Introuvable("Document")
    return s


def nom_de(u: Utilisateur | None) -> str:
    if u is None:
        return "—"
    return u.nom_affiche or u.email or u.telephone or str(u.id)
