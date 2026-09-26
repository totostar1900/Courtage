"""Rapport scellé : généré à l'émission, conservé, vérifiable publiquement par son numéro."""
import re

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from courtage.api import creer_app
from tests.outils import V1, en_tant_que, etude

CLE = b"cle-de-test-suffisamment-longue-pour-un-hmac"


def emettre(client, a, **champs):
    e = etude(client, a, **champs).json()
    r = client.post(f"{V1}/organisations/{a['org']}/etudes/{e['id']}/emission", headers=en_tant_que(a["conseiller"]))
    assert r.status_code == 200, r.text
    return r.json()


def rapport(client, a, etude_id):
    r = client.get(f"{V1}/organisations/{a['org']}/etudes/{etude_id}/rapport", headers=en_tant_que(a["drh"]))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    return r.content


def pages(pdf: bytes) -> list[str]:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return [p.get_text() for p in doc]


def test_le_rapport_est_emis_avec_l_etude(client, azito):
    e = emettre(client, azito)
    numero = e["rapport"]["numero"]
    assert re.fullmatch(r"RL-[A-Z0-9]{4}-[A-Z0-9]{4}", numero)
    textes = pages(rapport(client, azito, e["id"]))
    tout = "\n".join(textes)
    assert "AZITO" in tout
    assert "60 130 415" in tout.replace(" ", " ").replace("\xa0", " ")   # la dette, au franc
    assert "Convention collective interprofessionnelle de Côte d'Ivoire" in tout
    assert "Conseiller" in tout                                                # l'émetteur, par son nom affiché
    assert len(textes) >= 2
    for t in textes:                                                           # le pied de page, sur CHAQUE page
        assert numero in t


def test_le_rapport_ne_contient_aucun_nom_de_salarie(client, azito):
    e = emettre(client, azito)
    assert "Nom Prénom" not in "\n".join(pages(rapport(client, azito, e["id"])))


def test_sans_cle_le_sceau_est_dit_non_probant(client, azito):
    e = emettre(client, azito)
    assert "non probant" in "\n".join(pages(rapport(client, azito, e["id"]))).lower()
    v = client.get(f"{V1}/verifier/{e['rapport']['numero']}").json()
    assert v["authentique"] is True and v["probant"] is False


def test_verification_publique_sans_compte(bases, azito):
    avec_cle = TestClient(creer_app(moteur=bases[1], authentification="entete_dev", cle_sceau=CLE))
    e = emettre(avec_cle, azito)
    v = avec_cle.get(f"{V1}/verifier/{e['rapport']['numero']}")   # aucun en-tête d'identité
    assert v.status_code == 200
    v = v.json()
    assert v["authentique"] is True and v["probant"] is True
    assert v["resume"]["organisation"] == "AZITO"
    assert v["resume"]["dette"] == e["totaux"]["dette"]
    assert v["resume"]["date_evaluation"] == "2019-12-31"


def test_verifier_qu_un_pdf_est_l_original(client, azito):
    e = emettre(client, azito)
    pdf = rapport(client, azito, e["id"])
    url = f"{V1}/verifier/{e['rapport']['numero']}"
    assert client.post(url, files={"document": ("r.pdf", pdf)}).json()["conforme"] is True
    milieu = len(pdf) // 2
    retouche = pdf[:milieu] + bytes([pdf[milieu] ^ 1]) + pdf[milieu + 1:]   # un seul bit changé
    assert client.post(url, files={"document": ("r.pdf", retouche)}).json()["conforme"] is False


def test_un_sceau_altere_n_est_plus_authentique(client, azito, bases):
    e = emettre(client, azito)
    with bases[0].begin() as c:   # seul le propriétaire le peut : le rôle applicatif n'a pas UPDATE
        c.execute(text("UPDATE sceaux SET resume = jsonb_set(resume, '{dette}', '1') WHERE numero = :n"),
                  {"n": e["rapport"]["numero"]})
    assert client.get(f"{V1}/verifier/{e['rapport']['numero']}").json()["authentique"] is False


def test_numero_inconnu(client):
    assert client.get(f"{V1}/verifier/RL-AAAA-AAAA").status_code == 404


def test_pas_de_rapport_pour_un_brouillon(client, azito):
    e = etude(client, azito).json()
    r = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/rapport", headers=en_tant_que(azito["drh"]))
    assert r.status_code == 404
    assert r.json()["code"] == "rapport_indisponible"


def test_si_le_rapport_echoue_l_etude_n_est_pas_emise(client, azito, monkeypatch):
    from courtage.services import rapport as module_rapport

    def en_panne(*_, **__):
        raise RuntimeError("moteur PDF indisponible")
    monkeypatch.setattr(module_rapport, "rendre_pdf", en_panne)
    e = etude(client, azito).json()
    with pytest.raises(RuntimeError):
        client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission",
                    headers=en_tant_que(azito["conseiller"]))
    relue = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}", headers=en_tant_que(azito["drh"])).json()
    assert relue["statut"] == "brouillon"


def test_en_production_la_cle_de_sceau_est_obligatoire(bases, monkeypatch):
    monkeypatch.setenv("COURTAGE_ENV", "production")
    with pytest.raises(RuntimeError, match="sceau"):
        creer_app(moteur=bases[1], authentification="aucune")


def test_le_rapport_dit_ce_que_coute_le_regime(client, azito):
    from tests.test_regime import CADRES, adopter, categorie, regime
    v = regime(client, azito, [categorie("*", CADRES)])
    adopter(client, azito, v["id"])
    e = emettre(client, azito, convention_code=None, regime_version_id=v["id"])
    tout = "\n".join(pages(rapport(client, azito, e["id"])))
    assert "Accord AZITO 2015" in tout
    assert "au-delà de la convention" in tout


def test_le_rapport_met_la_non_conformite_en_tete(client, azito):
    from tests.test_regime import AVARE, adopter, categorie, regime
    v = regime(client, azito, [categorie("*", AVARE)])
    adopter(client, azito, v["id"], accepte=True)
    e = emettre(client, azito, convention_code=None, regime_version_id=v["id"])
    premiere = pages(rapport(client, azito, e["id"]))[0]
    assert premiere.index("Régime non conforme") < premiere.index("Synthèse")
