"""Le moteur à règles : aucun appel externe, les formulations les plus courantes seulement.

Il lit, clause par clause, « X % (d'un mois de salaire) pour chacune des N
premières années », « de la Ae à la Be année », « au-delà de la Ne année »,
et prend la clause elle-même pour citation. Il ne distingue pas les catégories
et le dit : c'est une aide à la saisie, pas une lecture.
"""
import re
import unicodedata

from . import Attention, CategorieLue, Document, Extraction, TrancheLue

PAYS = {"cameroun": "CM", "camerounais": "CM", "gabon": "GA", "gabonais": "GA", "tchad": "TD", "tchadien": "TD",
        "centrafrique": "CF", "centrafricain": "CF", "guinee equatoriale": "GQ", "congo": "CG", "congolais": "CG",
        "cote d'ivoire": "CI", "ivoirien": "CI", "senegal": "SN", "madagascar": "MG", "malgache": "MG"}
MOIS = {m: i for i, m in enumerate(("janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
                                    "septembre", "octobre", "novembre", "decembre"), start=1)}

_TAUX = r"(\d{1,3}(?:[.,]\d+)?)\s*%"
_N = r"(\d{1,2})"


def _plat(t: str) -> str:
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower().replace("’", "'")


def _nombre(x: str) -> float:
    return float(x.replace(",", "."))


class ExtracteurRegles:
    moteur = "regles"
    modele = None
    envoie_a_un_tiers = False

    def extraire(self, document: Document, pays_organisation: str) -> Extraction:
        texte = document.texte
        clauses = [c.strip() for c in re.split(r"[;\n]|(?<=[a-z0-9%)])\.\s", texte) if c.strip()]
        tranches: dict[int | None, float] = {}
        citations = []
        for clause in clauses:
            p = _plat(clause)
            taux = re.search(_TAUX, p)
            if not taux or "an" not in p:
                continue
            valeur = _nombre(taux.group(1)) / 100
            borne = None
            if m := re.search(rf"{_N}\s*(?:premieres|1eres)\s+annees", p):
                borne = int(m.group(1))
            elif m := re.search(rf"(?:de\s+la\s+|de\s+){_N}\s*(?:e|eme|ieme)?\s*(?:annee\s*)?a\s+(?:la\s+)?{_N}\s*(?:e|eme|ieme)?\s*(?:annee|ans)", p):
                borne = int(m.group(2))
            elif re.search(rf"(?:au[- ]dela\s+de\s+(?:la\s+)?{_N}|a\s+partir\s+de\s+la\s+{_N})", p):
                borne = None
            else:
                continue
            tranches[borne] = valeur
            citations.append(clause)
        base, base_citation = "inconnue", None
        for clause in clauses:
            if re.search(r"moyenne\s+(?:mensuelle\s+)?des\s+(?:douze|12)\s+(?:derniers\s+)?mois", _plat(clause)):
                base, base_citation = "moyenne_12_mois", clause
                break
        categories = []
        if tranches:
            ordonnees = sorted(tranches.items(), key=lambda kv: (kv[0] is None, kv[0] or 0))
            categories.append(CategorieLue(
                categorie="*", tranches=[TrancheLue(jusqu_a=b, mois_par_annee=v) for b, v in ordonnees],
                citation=citations[0], autres_citations=citations[1:],
                base_salaire=base, base_salaire_citation=base_citation))
        attention = [Attention(texte="Lecture par règles : les catégories de personnel ne sont pas distinguées et "
                                     "seules les formulations courantes sont reconnues. Relisez chaque taux.")]
        return Extraction(pays=self._pays(texte), type_document=self._type(texte), intitule=self._intitule(texte),
                          date_effet=self._date(texte), date_effet_citation=self._clause_de_date(clauses),
                          categories=categories,
                          points_d_attention=attention,
                          non_trouve=[] if tranches else ["barème de l'indemnité de départ à la retraite"])

    @classmethod
    def _clause_de_date(cls, clauses: list[str]) -> str | None:
        return next((c for c in clauses if cls._date(c)), None)

    @staticmethod
    def _pays(texte: str) -> str | None:
        p = _plat(texte)
        trouves = [code for nom, code in PAYS.items() if re.search(rf"\b{nom}", p)]
        return max(set(trouves), key=trouves.count) if trouves else None

    @staticmethod
    def _type(texte: str) -> str:
        p = _plat(texte[:2000])
        if "convention collective" in p:
            return "convention_collective"
        if "accord" in p:
            return "accord_entreprise"
        if "note de service" in p or "decision" in p:
            return "decision_direction"
        return "autre"

    @staticmethod
    def _intitule(texte: str) -> str | None:
        premiere = next((l.strip() for l in texte.splitlines() if l.strip()), None)
        return premiere[:200] if premiere else None

    @staticmethod
    def _date(texte: str) -> str | None:
        p = _plat(texte)
        if m := re.search(r"(?:vigueur|compter|effet)[^.]{0,40}?(\d{1,2})(?:er)?\s+(" + "|".join(MOIS) + r")\s+(\d{4})", p):
            return f"{int(m.group(3)):04d}-{MOIS[m.group(2)]:02d}-{int(m.group(1)):02d}"
        if m := re.search(r"(?:vigueur|compter|effet)[^.]{0,40}?(\d{1,2})/(\d{1,2})/(\d{4})", p):
            return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        return None
