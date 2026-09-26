"""Le moteur Claude : le document tel quel (PDF ou texte), une réponse au format imposé, vérifiée ensuite.

Le modèle ne décide de rien : il lit et CITE. `proposer` (module parent)
vérifie chaque citation dans le texte lu localement ; une valeur sans passage
retrouvé est signalée. Le texte part chez Anthropic : l'écran le dit et demande
l'accord de la personne avant l'envoi ; la plateforme n'en garde que l'empreinte.
"""
import base64
import json

import anthropic

from . import CEMAC, Document, Extraction, ExtractionImpossible

MODELE = "claude-opus-5"

_NUL = lambda t: {"anyOf": [{"type": t}, {"type": "null"}]}  # noqa: E731


def _objet(proprietes: dict) -> dict:
    return {"type": "object", "properties": proprietes, "required": list(proprietes), "additionalProperties": False}


SCHEMA = _objet({
    "pays": _NUL("string"),
    "type_document": {"type": "string", "enum": ["accord_entreprise", "convention_collective", "contrat_travail",
                                                 "usage", "decision_direction", "autre"]},
    "intitule": _NUL("string"),
    "date_effet": _NUL("string"),
    "date_effet_citation": _NUL("string"),
    "convention_citee": _NUL("string"),
    "categories": {"type": "array", "items": _objet({
        "categorie": {"type": "string"},
        "tranches": {"type": "array", "items": _objet({"jusqu_a": _NUL("integer"), "mois_par_annee": {"type": "number"}})},
        "citation": {"type": "string"},
        "anciennete_minimale": _NUL("integer"),
        "anciennete_minimale_citation": _NUL("string"),
        "plafond_mois": _NUL("number"),
        "plafond_citation": _NUL("string"),
        "base_salaire": {"type": "string", "enum": ["dernier", "moyenne_12_mois", "inconnue"]},
        "base_salaire_citation": _NUL("string"),
        "avec_primes": _NUL("boolean"),
        "autres_citations": {"type": "array", "items": {"type": "string"}},
    })},
    "points_d_attention": {"type": "array", "items": _objet({"texte": {"type": "string"}, "citation": _NUL("string")})},
    "non_trouve": {"type": "array", "items": {"type": "string"}},
})

SYSTEME = f"""Tu lis un texte de droit du travail d'un pays d'Afrique centrale (accord d'entreprise, convention \
collective, contrat, note de la direction) pour une plateforme de courtage qui calcule les indemnités de fin de \
carrière (IFC, indemnité de départ à la retraite). Tu en extrais le barème de l'indemnité de départ à la RETRAITE, \
et rien d'autre : pas le licenciement, pas la démission.

Règles :
- Recopie mot pour mot, dans chaque champ « citation », le passage qui fonde la valeur : il sera recherché dans le \
texte. Si le barème s'étale sur plusieurs phrases, la première va dans « citation », les autres dans \
« autres_citations », chacune recopiée mot pour mot. Une valeur que le texte ne dit pas reste null et va dans « non_trouve ». N'invente rien, ne complète rien \
par ce que dirait « d'habitude » une convention.
- Barème : une liste de tranches cumulatives ; « mois_par_annee » est la fraction de mois de salaire par année \
d'ancienneté dans la tranche (25 % d'un mois = 0.25) ; « jusqu_a » est la dernière année de la tranche, null pour \
la dernière. « 30 % pour chacune des 5 premières années, 35 % de la 6e à la 10e, 40 % au-delà » donne \
[{{5, 0.30}}, {{10, 0.35}}, {{null, 0.40}}].
- Si le barème est exprimé autrement (mois fixes par palier d'ancienneté, somme forfaitaire), ne le convertis pas : \
décris-le dans « points_d_attention » avec sa citation, et laisse les tranches vides.
- Une catégorie par barème distinct (Cadres, Agents de maîtrise, …) ; « * » quand le barème vaut pour tout le personnel.
- « pays » : le code ISO à deux lettres du pays dont relève le texte s'il le dit ({", ".join(f"{k} {v}" for k, v in CEMAC.items())}, ou un autre), null sinon.
- « date_effet » au format AAAA-MM-JJ si le texte la donne.
- Signale dans « points_d_attention » ce qu'un actuaire devrait relire : conditions d'ancienneté, plafonds, \
majorations, base de salaire, renvois à un autre texte."""


class ExtracteurClaude:
    moteur = "claude"
    envoie_a_un_tiers = True

    def __init__(self, client: anthropic.Anthropic | None = None, modele: str = MODELE):
        self.client = client or anthropic.Anthropic()
        self.modele = modele

    def extraire(self, document: Document, pays_organisation: str) -> Extraction:
        if document.type_contenu == "application/pdf":
            bloc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                                   "data": base64.b64encode(document.contenu).decode()}}
        else:
            bloc = {"type": "document", "source": {"type": "text", "media_type": "text/plain", "data": document.texte}}
        try:
            reponse = self.client.beta.messages.create(
                model=self.modele,
                max_tokens=16000,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                thinking={"type": "adaptive"},
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
                system=SYSTEME,
                messages=[{"role": "user", "content": [
                    bloc,
                    {"type": "text", "text": f"L'entreprise est établie au {CEMAC.get(pays_organisation, pays_organisation)}. "
                                             f"Extrais le barème de départ à la retraite de ce document ({document.nom_fichier})."},
                ]}],
            )
        except anthropic.APIConnectionError as e:
            raise ExtractionImpossible("Le service de lecture est injoignable : réessayez plus tard.") from e
        except anthropic.RateLimitError as e:
            raise ExtractionImpossible("Le service de lecture est saturé : réessayez dans une minute.") from e
        except anthropic.APIStatusError as e:
            raise ExtractionImpossible(f"Le service de lecture a répondu une erreur ({e.status_code}).") from e
        if reponse.stop_reason == "refusal":
            raise ExtractionImpossible("Le service de lecture a décliné ce document.")
        if reponse.stop_reason == "max_tokens":
            raise ExtractionImpossible("Le document est trop long pour être lu en une fois.")
        texte = next((b.text for b in reponse.content if b.type == "text"), None)
        if texte is None:
            raise ExtractionImpossible("Le service de lecture n'a rien rendu.")
        try:
            return Extraction.model_validate(json.loads(texte))
        except (json.JSONDecodeError, ValueError) as e:
            raise ExtractionImpossible("La lecture a rendu une réponse illisible.") from e
