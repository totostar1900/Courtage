"""Extraction assistée : proposer un régime à partir d'un texte existant — CEMAC seulement, chaque valeur citée et vérifiée."""
import json
from types import SimpleNamespace

import pytest

from courtage.extraction import (CategorieLue, Document, Extraction, ExtractionImpossible, TrancheLue,
                                 citation_retrouvee, lire_document, proposer)
from courtage.extraction.claude import SCHEMA, ExtracteurClaude
from courtage.extraction.regles import ExtracteurRegles

FONDEMENTS = {"accord_entreprise": "", "contrat_travail": "", "usage": "", "decision_direction": ""}

ACCORD = """ACCORD D'ENTREPRISE RELATIF A L'INDEMNITE DE DEPART A LA RETRAITE
Société Démo SA — Douala, Cameroun
Article 9 — Indemnité de départ à la retraite
Le salarié qui part à la retraite perçoit une indemnité calculée sur la moyenne mensuelle des douze derniers mois de salaire :
- 45 % d'un mois de salaire pour chacune des 5 premières années ;
- 50 % de la 6e à la 10e année ;
- 65 % de la 11e à la 15e année ;
- 80 % au-delà de la 15e année.
Le présent accord entre en vigueur le 1er février 2024.
"""


def doc(texte=ACCORD, nom="accord.txt"):
    return lire_document(texte.encode("utf-8"), nom)


# --- Le moteur à règles -------------------------------------------------------------------

def test_les_regles_lisent_un_bareme_courant():
    x = ExtracteurRegles().extraire(doc(), "CM")
    assert (x.pays, x.type_document, x.date_effet) == ("CM", "accord_entreprise", "2024-02-01")
    [c] = x.categories
    assert [(t.jusqu_a, t.mois_par_annee) for t in c.tranches] == [(5, 0.45), (10, 0.5), (15, 0.65), (None, 0.8)]
    assert c.base_salaire == "moyenne_12_mois"
    assert "5 premières années" in c.citation


def test_chaque_valeur_lue_par_les_regles_se_retrouve_dans_le_texte():
    p = proposer(ExtracteurRegles().extraire(doc(), "CM"), doc(), "CM", "CM_COMMERCE", FONDEMENTS)
    assert p.verifications and all(v["retrouvee"] for v in p.verifications)
    assert {v["champ"] for v in p.verifications} >= {"* · barème", "* · barème (suite)", "* · base de salaire", "date d'effet"}


def test_un_texte_sans_bareme():
    x = ExtracteurRegles().extraire(doc("Note de service : horaires d'été."), "CM")
    assert x.categories == [] and x.non_trouve


# --- Les citations -----------------------------------------------------------------------

def test_une_citation_se_retrouve_malgre_accents_casse_et_espaces():
    assert citation_retrouvee("45 %  D'UN MOIS de salaire pour chacune des 5 premieres annees", ACCORD)
    assert citation_retrouvee("60 % d'un mois de salaire pour chacune des 5 premières années", ACCORD) is False
    assert citation_retrouvee("n'importe quoi", "") is None


# --- La proposition --------------------------------------------------------------------------

def extraction(**champs):
    base = dict(pays="CM", type_document="accord_entreprise", intitule="Accord IFC du 1er février 2024",
                date_effet="2024-02-01", date_effet_citation="entre en vigueur le 1er février 2024",
                categories=[CategorieLue(categorie="*", tranches=[TrancheLue(jusqu_a=5, mois_par_annee=0.45),
                                                                  TrancheLue(jusqu_a=None, mois_par_annee=0.5)],
                                         citation="45 % d'un mois de salaire pour chacune des 5 premières années",
                                         base_salaire="moyenne_12_mois",
                                         base_salaire_citation="la moyenne mensuelle des douze derniers mois de salaire")])
    return Extraction(**{**base, **champs})


def test_la_proposition_preremplit_une_version():
    p = proposer(extraction(), doc(), "CM", "CM_COMMERCE", FONDEMENTS)
    assert p.version == {"en_vigueur_du": "2024-02-01", "fondement": "accord_entreprise",
                         "document_reference": "Accord IFC du 1er février 2024",
                         "categories": [{"categorie": "*", "convention_code": "CM_COMMERCE",
                                         "bareme": {"forme": "tranches_cumulatives", "tranches": [
                                             {"jusqu_a": 5, "mois_par_annee": 0.45}, {"jusqu_a": None, "mois_par_annee": 0.5}]},
                                         "anciennete_minimale": 0, "plafond_mois": None, "arrondi": "annees",
                                         "base_salaire": "moyenne_12_mois", "avec_primes": False, "evenements": ["retraite"]}]}
    assert all(v["retrouvee"] for v in p.verifications)
    assert not [c for c in p.constats if c["niveau"] != "informe"]


def test_une_citation_inventee_est_signalee():
    x = extraction(categories=[CategorieLue(categorie="Cadres", tranches=[TrancheLue(mois_par_annee=1.0)],
                                            citation="100 % d'un mois pour les cadres")])
    p = proposer(x, doc(), "CM", "CM_COMMERCE", FONDEMENTS)
    assert {c["code"] for c in p.constats} >= {"citation_introuvable", "sans_categorie_generale"}
    assert [v["retrouvee"] for v in p.verifications if v["champ"].startswith("Cadres")] == [False]


def test_hors_cemac_rien_n_est_repris():
    p = proposer(extraction(pays="CI"), doc(), "CM", "CM_COMMERCE", FONDEMENTS)
    assert p.version == {} and [c["code"] for c in p.constats] == ["hors_cemac"]


def test_une_derniere_tranche_fermee_est_prolongee_et_signalee():
    x = extraction(categories=[CategorieLue(categorie="*", tranches=[TrancheLue(jusqu_a=10, mois_par_annee=0.3)],
                                            citation="45 % d'un mois de salaire pour chacune des 5 premières années")])
    p = proposer(x, doc(), "CM", None, FONDEMENTS)
    assert p.version["categories"][0]["bareme"]["tranches"][-1] == {"jusqu_a": None, "mois_par_annee": 0.3}
    assert "derniere_tranche_ouverte" in {c["code"] for c in p.constats}


def test_un_pdf_scanne_ne_peut_pas_etre_verifie():
    illisible = Document(b"%PDF", "scan.pdf", "application/pdf", "")
    p = proposer(extraction(), illisible, "CM", None, FONDEMENTS)
    assert "texte_illisible" in {c["code"] for c in p.constats}
    assert {v["retrouvee"] for v in p.verifications} == {None}


# --- Le moteur Claude, sans réseau ------------------------------------------------------------

class FauxClient:
    def __init__(self, texte=None, stop="end_turn"):
        self.appels = []
        self.texte, self.stop = texte, stop
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.appels.append(kw)
        contenu = [SimpleNamespace(type="text", text=self.texte)] if self.texte is not None else []
        return SimpleNamespace(stop_reason=self.stop, content=contenu)


def test_la_requete_envoyee_a_claude():
    reponse = extraction().model_dump(mode="json")
    client = FauxClient(json.dumps(reponse))
    x = ExtracteurClaude(client=client).extraire(doc(), "CM")
    assert x == extraction()
    [appel] = client.appels
    assert appel["model"] == "claude-opus-5" and appel["fallbacks"] == "default"
    assert appel["betas"] == ["server-side-fallback-2026-07-01"]
    assert appel["thinking"] == {"type": "adaptive"}
    assert appel["output_config"]["format"] == {"type": "json_schema", "schema": SCHEMA}
    document = appel["messages"][0]["content"][0]
    assert document["type"] == "document" and document["source"]["type"] == "text"
    assert "Cameroun" in appel["messages"][0]["content"][1]["text"]


def test_un_pdf_part_tel_quel():
    client = FauxClient(json.dumps(extraction().model_dump(mode="json")))
    ExtracteurClaude(client=client).extraire(Document(b"%PDF-1.4 x", "a.pdf", "application/pdf", ""), "CM")
    source = client.appels[0]["messages"][0]["content"][0]["source"]
    assert source["type"] == "base64" and source["media_type"] == "application/pdf"


@pytest.mark.parametrize("client", [FauxClient(None, stop="refusal"), FauxClient("{", stop="end_turn"),
                                    FauxClient(json.dumps({"categories": "pas une liste"})), FauxClient("x", stop="max_tokens")])
def test_une_lecture_ratee_se_dit(client):
    with pytest.raises(ExtractionImpossible):
        ExtracteurClaude(client=client).extraire(doc(), "CM")


def test_le_schema_est_strict_partout():
    def parcourir(s):
        if isinstance(s, dict):
            if s.get("type") == "object":
                assert s["additionalProperties"] is False and set(s["required"]) == set(s["properties"])
            for v in s.values():
                parcourir(v)
        elif isinstance(s, list):
            for v in s:
                parcourir(v)
    parcourir(SCHEMA)


# --- Par l'API -------------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from courtage.api import creer_app  # noqa: E402
from tests.outils import V1, en_tant_que  # noqa: E402


class ExtracteurTiers:
    """Un moteur qui, comme Claude, envoie le texte à un tiers — sans réseau."""
    moteur, modele, envoie_a_un_tiers = "faux", "modele-de-test", True

    def __init__(self, x=None):
        self.x, self.appels = x, 0

    def extraire(self, document, pays):
        self.appels += 1
        return self.x or extraction()


@pytest.fixture
def cm(bases, personnes):
    """Un client camerounais (CEMAC), et une API dont le moteur envoie à un tiers."""
    moteur = ExtracteurTiers()
    web = TestClient(creer_app(moteur=bases[1], authentification="entete_dev", extracteur=moteur))
    org = web.post(f"{V1}/organisations", json={"nom": "Démo CM", "pays": "CM"}, headers=en_tant_que(personnes["admin"])).json()["id"]
    for qui, role in (("conseiller", "conseiller"), ("drh", "admin_client")):
        web.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes[qui]), "role": role},
                 headers=en_tant_que(personnes["admin"]))
    return {"web": web, "org": org, "moteur": moteur, **personnes}


def envoyer(cm, qui="drh", consentement=True, contenu=ACCORD.encode(), nom="accord.txt", org=None):
    return cm["web"].post(f"{V1}/organisations/{org or cm['org']}/regimes/extraction", headers=en_tant_que(cm[qui]),
                          files={"fichier": (nom, contenu)}, data={"consentement": str(consentement).lower()})


def test_sans_accord_rien_ne_part(cm):
    r = envoyer(cm, consentement=False)
    assert r.status_code == 422 and r.json()["code"] == "consentement_requis"
    assert cm["moteur"].appels == 0


def test_l_extraction_propose_et_garde_seulement_l_empreinte(cm, bases):
    r = envoyer(cm)
    assert r.status_code == 201, r.text
    x = r.json()
    assert x["version"]["categories"][0]["bareme"]["tranches"][0] == {"jusqu_a": 5, "mois_par_annee": 0.45}
    assert x["envoie_a_un_tiers"] is True and x["modele"] == "modele-de-test"
    with bases[0].connect() as c:
        ligne = c.execute(text("SELECT empreinte, taille, envoye_a_un_tiers FROM extractions WHERE organisation_id = :o"),
                          {"o": cm["org"]}).one()
        colonnes = [r[0] for r in c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'extractions'"))]
    assert len(ligne.empreinte.strip()) == 64 and ligne.taille == len(ACCORD.encode()) and ligne.envoye_a_un_tiers
    assert "contenu" not in colonnes                     # le document lui-même n'est jamais gardé


def test_hors_cemac_on_ne_lit_pas(cm, personnes):
    ci = cm["web"].post(f"{V1}/organisations", json={"nom": "Démo CI", "pays": "CI"}, headers=en_tant_que(personnes["admin"])).json()["id"]
    cm["web"].post(f"{V1}/organisations/{ci}/adhesions", json={"utilisateur_id": str(personnes["drh"]), "role": "admin_client"},
                   headers=en_tant_que(personnes["admin"]))
    r = envoyer(cm, org=ci)
    assert r.status_code == 409 and r.json()["code"] == "hors_cemac" and cm["moteur"].appels == 0


def test_formats(cm):
    assert envoyer(cm, contenu=b"PK\x03\x04", nom="accord.docx").json()["code"] == "format_non_pris_en_charge"


def test_le_lecteur_n_extrait_pas(cm, bases):
    with bases[0].begin() as c:
        lecteur = c.execute(text("INSERT INTO utilisateurs (email, nom_affiche) VALUES ('lx@x.cm', 'L') RETURNING id")).scalar_one()
        c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'lecteur_client')"),
                  {"u": lecteur, "o": cm["org"]})
    assert envoyer({**cm, "lecteur": lecteur}, qui="lecteur").status_code == 403


def test_le_mode_dit_ce_qui_part(cm):
    m = cm["web"].get(f"{V1}/extraction/mode", headers=en_tant_que(cm["drh"])).json()
    assert m["envoie_a_un_tiers"] is True and set(m["pays_couverts"]) == {"CM", "GA", "CG", "TD", "CF", "GQ"}


def test_par_defaut_le_moteur_a_regles_ne_demande_pas_d_accord(client, personnes):
    org = client.post(f"{V1}/organisations", json={"nom": "G", "pays": "GA"}, headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes["drh"]), "role": "admin_client"},
                headers=en_tant_que(personnes["admin"]))
    r = client.post(f"{V1}/organisations/{org}/regimes/extraction", headers=en_tant_que(personnes["drh"]),
                    files={"fichier": ("accord.txt", ACCORD.replace("Cameroun", "Gabon").encode())})
    assert r.status_code == 201, r.text
    assert r.json()["moteur"] == "regles" and len(r.json()["version"]["categories"][0]["bareme"]["tranches"]) == 4


# --- Pour le référentiel ------------------------------------------------------------------

def test_la_plateforme_propose_une_convention_a_valider(cm):
    r = cm["web"].post(f"{V1}/referentiel/extraction", headers=en_tant_que(cm["admin"]),
                       files={"fichier": ("ccn-commerce.txt", ACCORD.encode())},
                       data={"pays": "CM", "consentement": "true"})
    assert r.status_code == 200, r.text
    c = r.json()["convention"]
    assert c["statut"] == "a_valider" and c["pays"] == "CM" and c["code"].startswith("CM_")
    assert c["bareme"]["forme"] == "tranches_cumulatives" and "À valider" in c["verification"]
    from courtage.referentiel import Convention
    Convention.model_validate(c)                         # un fichier prêt pour referentiel/donnees/, une fois relu


def test_le_referentiel_n_est_pas_pour_un_client(cm):
    r = cm["web"].post(f"{V1}/referentiel/extraction", headers=en_tant_que(cm["conseiller"]),
                       files={"fichier": ("x.txt", b"x")}, data={"pays": "CM", "consentement": "true"})
    assert r.status_code == 403


def test_le_referentiel_seulement_cemac(cm):
    r = cm["web"].post(f"{V1}/referentiel/extraction", headers=en_tant_que(cm["admin"]),
                       files={"fichier": ("x.txt", b"x")}, data={"pays": "CI", "consentement": "true"})
    assert r.json()["code"] == "hors_cemac"


def test_un_vrai_pdf_se_lit_localement():
    from weasyprint import HTML
    pdf = HTML(string="<p>" + ACCORD.replace("\n", "</p><p>") + "</p>").write_pdf()
    d = lire_document(pdf, "accord.pdf")
    assert d.type_contenu == "application/pdf" and "premières années" in d.texte
    x = ExtracteurRegles().extraire(d, "CM")
    assert [t.mois_par_annee for t in x.categories[0].tranches] == [0.45, 0.5, 0.65, 0.8]
    assert citation_retrouvee(x.categories[0].citation, d.texte)
