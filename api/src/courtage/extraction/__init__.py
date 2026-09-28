"""Extraction assistée : lire un texte existant (accord d'entreprise, convention) et PROPOSER un régime.

Rien de ce qui est extrait n'entre tel quel : la proposition préremplit le
formulaire d'une version de régime, qu'une personne relit, corrige et
enregistre ; l'analyse habituelle (plancher, pièges, coûts) suit. Chaque
valeur proposée porte la CITATION du passage d'où elle vient, et la
plateforme vérifie que ce passage est bien dans le texte : une valeur dont la
citation est introuvable est signalée, jamais reprise en silence.

Périmètre (décision du 26/09) : les pays de la CEMAC seulement. Un texte d'un
autre pays est signalé et rien n'en est repris.

Deux moteurs, interchangeables (`Extracteur`) : Claude, qui lit le PDF comme
un humain ; des règles, sans appel externe, qui ne reconnaissent que les
formulations les plus courantes.
"""
import re
import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

BASES = {"dernier": "dernier salaire", "moyenne_12_mois": "moyenne des 12 derniers mois"}
from courtage.langue import TRADUCTIONS, traduire  # noqa: E402
from courtage.referentiel import CEMAC, CEMAC_EN  # noqa: E402
TypeDocument = Literal["accord_entreprise", "convention_collective", "contrat_travail", "usage", "decision_direction",
                       "autre"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TrancheLue(_Strict):
    jusqu_a: int | None = Field(default=None, gt=0)
    mois_par_annee: float = Field(ge=0, le=3)


class CategorieLue(_Strict):
    categorie: str                                   # « * » pour tout le personnel
    tranches: list[TrancheLue]
    citation: str                                    # le passage qui fixe le barème
    anciennete_minimale: int | None = None
    anciennete_minimale_citation: str | None = None
    plafond_mois: float | None = None
    plafond_citation: str | None = None
    base_salaire: Literal["dernier", "moyenne_12_mois", "inconnue"] = "inconnue"
    base_salaire_citation: str | None = None
    avec_primes: bool | None = None
    autres_citations: list[str] = []                 # les autres passages du barème (une tranche par phrase)


class Attention(_Strict):
    texte: str
    citation: str | None = None


class Extraction(_Strict):
    pays: str | None = None                          # code ISO du pays dont relève le texte, s'il le dit
    type_document: TypeDocument = "autre"
    intitule: str | None = None
    date_effet: str | None = None                    # AAAA-MM-JJ
    date_effet_citation: str | None = None
    convention_citee: str | None = None
    categories: list[CategorieLue] = []
    points_d_attention: list[Attention] = []
    non_trouve: list[str] = []

    @field_validator("pays")
    @classmethod
    def _pays(cls, v):
        return v.strip().upper() if v else None


@dataclass
class Document:
    contenu: bytes
    nom_fichier: str
    type_contenu: Literal["application/pdf", "text/plain"]
    texte: str                                       # le texte lu localement : la référence des citations


class Extracteur(Protocol):
    moteur: str
    modele: str | None
    envoie_a_un_tiers: bool

    def extraire(self, document: Document, pays_organisation: str) -> Extraction: ...


class ExtractionImpossible(Exception):
    """Le moteur n'a rien pu lire (refus, réponse illisible, document vide)."""


# --- Lire le document --------------------------------------------------------------------

def lire_document(contenu: bytes, nom_fichier: str) -> Document:
    if contenu.startswith(b"%PDF"):
        from pypdf import PdfReader
        try:
            texte = "\n".join((p.extract_text() or "") for p in PdfReader(BytesIO(contenu)).pages)
        except Exception:                            # noqa: BLE001 — un PDF abîmé se dit, il ne plante pas
            texte = ""
        return Document(contenu, nom_fichier, "application/pdf", texte)
    try:
        texte = contenu.decode("utf-8")
    except UnicodeDecodeError:
        texte = contenu.decode("latin-1")
    return Document(contenu, nom_fichier, "text/plain", texte)


# --- Vérifier ce qui est proposé -----------------------------------------------------------

def _plat(t: str) -> str:
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = t.replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w%',.]+", " ", t)).strip()


def citation_retrouvee(citation: str | None, texte: str) -> bool | None:
    """La citation est-elle dans le texte (casse, accents, espaces et césures ignorés) ? None si texte vide."""
    if not citation:
        return False
    if not texte.strip():
        return None
    return _plat(citation) in _plat(texte.replace("-\n", ""))


@dataclass
class Proposition:
    """Ce que l'écran montre : la version à préremplir, et pour chaque valeur d'où elle vient."""
    extraction: Extraction
    version: dict
    verifications: list[dict] = field(default_factory=list)
    constats: list[dict] = field(default_factory=list)


def proposer(extraction: Extraction, document: Document, pays_organisation: str, convention_par_defaut: str | None,
             fondements: dict[str, str]) -> Proposition:
    constats, verifications = [], []
    texte = document.texte
    if not texte.strip():
        constats.append(_c("avertit", "texte_illisible", "Le texte du document n'a pas pu être lu localement (PDF "
                           "scanné ?) : aucune citation ne peut être vérifiée. Relisez chaque valeur."))
    if extraction.pays and extraction.pays not in CEMAC:
        constats.append(_c("bloque", "hors_cemac", f"Le texte relève d'un pays hors CEMAC ({extraction.pays}) : la "
                           "plateforme ne traite pour l'instant que les textes des pays de la CEMAC. Rien n'est repris."))
        return Proposition(extraction, {}, [], constats)
    if extraction.pays and extraction.pays != pays_organisation:
        constats.append(_c("avertit", "autre_pays", f"Le texte semble relever de {CEMAC.get(extraction.pays, extraction.pays)}, "
                           f"l'entreprise de {CEMAC.get(pays_organisation, pays_organisation)}."))

    def verifier(champ: str, valeur, citation):
        ok = citation_retrouvee(citation, texte)
        verifications.append({"champ": champ, "valeur": valeur, "citation": citation, "retrouvee": ok})
        return ok

    categories = []
    for c in extraction.categories:
        nom = c.categorie.strip() or "*"
        if not c.tranches:
            constats.append(_c("avertit", "bareme_absent", f"Catégorie « {nom} » : aucun barème lu."))
            continue
        tranches = sorted(c.tranches, key=lambda t: (t.jusqu_a is None, t.jusqu_a or 0))
        if tranches[-1].jusqu_a is not None:
            tranches.append(TrancheLue(jusqu_a=None, mois_par_annee=tranches[-1].mois_par_annee))
            constats.append(_c("avertit", "derniere_tranche_ouverte", f"Catégorie « {nom} » : le texte ne dit pas le "
                               "taux au-delà de la dernière tranche ; le dernier taux est prolongé, à vérifier."))
        retrouvees = [verifier(f"{nom} · barème", [t.model_dump() for t in tranches], c.citation)]
        retrouvees += [verifier(f"{nom} · barème (suite)", None, autre) for autre in c.autres_citations]
        if False in retrouvees:
            constats.append(_c("avertit", "citation_introuvable", f"Catégorie « {nom} » : le passage cité pour le "
                               "barème n'est pas dans le texte. Vérifiez chaque taux avant d'enregistrer."))
        for champ, valeur, citation in (("ancienneté minimale", c.anciennete_minimale, c.anciennete_minimale_citation),
                                        ("plafond (mois)", c.plafond_mois, c.plafond_citation),
                                        ("base de salaire", BASES.get(c.base_salaire),
                                         c.base_salaire_citation)):
            if valeur is not None and verifier(f"{nom} · {champ}", valeur, citation) is False:
                constats.append(_c("avertit", "citation_introuvable", f"Catégorie « {nom} » : {champ} sans passage "
                                   "retrouvé dans le texte."))
        categories.append({
            "categorie": nom, "convention_code": convention_par_defaut or "",
            "bareme": {"forme": "tranches_cumulatives", "tranches": [t.model_dump() for t in tranches]},
            "anciennete_minimale": c.anciennete_minimale or 0, "plafond_mois": c.plafond_mois, "arrondi": "annees",
            "base_salaire": "moyenne_12_mois" if c.base_salaire == "moyenne_12_mois" else "dernier",
            "avec_primes": bool(c.avec_primes), "evenements": ["retraite"],
        })
    if not categories:
        constats.append(_c("avertit", "rien_a_reprendre", "Aucun barème d'indemnité de départ à la retraite n'a été "
                           "trouvé dans ce texte."))
    if categories and "*" not in {c["categorie"] for c in categories}:
        constats.append(_c("informe", "sans_categorie_generale", "Le texte ne vise que certaines catégories : ajoutez « * » "
                           "pour le reste du personnel, ou il restera au plancher de la convention."))
    if extraction.date_effet:
        verifier("date d'effet", extraction.date_effet, extraction.date_effet_citation)
    for a in extraction.points_d_attention:
        constats.append(_c("informe", "a_relire", a.texte))
    for manque in extraction.non_trouve:
        constats.append(_c("informe", "non_trouve", f"Non trouvé dans le texte : {manque}."))
    fondement = extraction.type_document if extraction.type_document in fondements else "accord_entreprise"
    version = {
        "en_vigueur_du": extraction.date_effet if _date_iso(extraction.date_effet) else None,
        "fondement": fondement,
        "document_reference": (extraction.intitule or document.nom_fichier)[:300],
        "categories": categories,
    }
    return Proposition(extraction, version, verifications, constats)


def _date_iso(d: str | None) -> bool:
    return bool(d and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d))


def _c(niveau: str, code: str, message: str) -> dict:
    return {"niveau": niveau, "code": code, "message": message}


# --- L'anglais de l'écran ------------------------------------------------------------------
# Les constats d'une proposition s'enregistrent avec l'extraction (`ExtractionTexte.resultat`) : ils naissent en
# français, et `constats_en_clair` les traduit au moment de les rendre, par les motifs inscrits ici.

_PAYS_EN = {fr: CEMAC_EN[code] for code, fr in CEMAC.items()}
_CHAMPS_EN = {"ancienneté minimale": "minimum length of service", "plafond (mois)": "cap (months)",
              "base de salaire": "salary basis"}


class _Gabarit:
    def __init__(self, fonction):
        self.fonction = fonction

    def format(self, **groupes) -> str:
        return self.fonction(**groupes)


def _motif(francais: str) -> str:
    morceaux = re.split(r"\{(\w+)\}", francais)
    return "".join(re.escape(m) if i % 2 == 0 else f"(?P<{m}>.+?)" for i, m in enumerate(morceaux))


def _ajouter(code: str, francais: str, anglais) -> None:
    TRADUCTIONS.setdefault(code, []).append((_motif(francais), anglais))


_ajouter("texte_illisible", "Le texte du document n'a pas pu être lu localement (PDF scanné ?) : aucune citation ne "
         "peut être vérifiée. Relisez chaque valeur.",
         "The document's text could not be read locally (scanned PDF?): no quotation can be checked. Review every "
         "value.")
_ajouter("hors_cemac", "Le texte relève d'un pays hors CEMAC ({pays}) : la plateforme ne traite pour l'instant que "
         "les textes des pays de la CEMAC. Rien n'est repris.",
         "The text comes from a country outside CEMAC ({pays}): for now the platform only handles texts from CEMAC "
         "countries. Nothing is taken over.")
_ajouter("autre_pays", "Le texte semble relever de {texte}, l'entreprise de {entreprise}.",
         _Gabarit(lambda texte, entreprise: f"The text appears to come from {_PAYS_EN.get(texte, texte)}, the "
                                            f"company from {_PAYS_EN.get(entreprise, entreprise)}."))
_ajouter("bareme_absent", "Catégorie « {nom} » : aucun barème lu.", "Category “{nom}”: no scale read.")
_ajouter("derniere_tranche_ouverte", "Catégorie « {nom} » : le texte ne dit pas le taux au-delà de la dernière "
         "tranche ; le dernier taux est prolongé, à vérifier.",
         "Category “{nom}”: the text does not give the rate beyond the last band; the last rate is extended, to be "
         "checked.")
_ajouter("citation_introuvable", "Catégorie « {nom} » : le passage cité pour le barème n'est pas dans le texte. "
         "Vérifiez chaque taux avant d'enregistrer.",
         "Category “{nom}”: the passage quoted for the scale is not in the text. Check each rate before saving.")
_ajouter("citation_introuvable", "Catégorie « {nom} » : {champ} sans passage retrouvé dans le texte.",
         _Gabarit(lambda nom, champ: f"Category “{nom}”: {_CHAMPS_EN.get(champ, champ)} with no passage found in "
                                     "the text."))
_ajouter("rien_a_reprendre", "Aucun barème d'indemnité de départ à la retraite n'a été trouvé dans ce texte.",
         "No retirement benefit scale was found in this text.")
_ajouter("sans_categorie_generale", "Le texte ne vise que certaines catégories : ajoutez « * » pour le reste du "
         "personnel, ou il restera au plancher de la convention.",
         "The text covers only some categories: add “*” for the rest of the staff, or they will stay at the "
         "collective agreement floor.")
_ajouter("non_trouve", "Non trouvé dans le texte : {manque}.", "Not found in the text: {manque}.")
# Les refus du moteur de lecture (extraction/claude.py), rendus comme erreur `extraction_impossible`.
for _fr, _en in (
        ("Le service de lecture est injoignable : réessayez plus tard.",
         "The reading service cannot be reached: try again later."),
        ("Le service de lecture est saturé : réessayez dans une minute.",
         "The reading service is overloaded: try again in a minute."),
        ("Le service de lecture a répondu une erreur ({statut}).", "The reading service returned an error ({statut})."),
        ("Le service de lecture a décliné ce document.", "The reading service declined this document."),
        ("Le document est trop long pour être lu en une fois.", "The document is too long to be read in one go."),
        ("Le service de lecture n'a rien rendu.", "The reading service returned nothing."),
        ("La lecture a rendu une réponse illisible.", "The reading returned an unreadable response.")):
    _ajouter("extraction_impossible", _fr, _en)


def constats_en_clair(constats: list[dict]) -> list[dict]:
    """Des COPIES, message dans la langue de l'écran : l'enregistré reste en français."""
    return [{**c, "message": traduire(c.get("code"), c.get("message") or "")} for c in constats]


__all__ = ["CEMAC", "Attention", "CategorieLue", "Document", "Extracteur", "Extraction", "ExtractionImpossible",
           "Proposition", "TrancheLue", "ValidationError", "citation_retrouvee", "constats_en_clair", "lire_document",
           "proposer"]
