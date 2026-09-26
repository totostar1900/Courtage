"""Outils de développement : la liste des personnes (mode entete_dev seulement) et le jeu de démonstration."""
from fastapi.testclient import TestClient
from sqlalchemy import text

from courtage.api import creer_app
from courtage.demo import semer
from tests.outils import V1, en_tant_que


def test_la_liste_des_personnes_n_existe_qu_en_developpement(bases, personnes):
    dev = TestClient(creer_app(moteur=bases[1], authentification="entete_dev"))
    r = dev.get(f"{V1}/dev/utilisateurs")
    assert r.status_code == 200
    assert {"id", "nom_affiche", "email", "admin_plateforme"} <= set(r.json()[0])
    prod = TestClient(creer_app(moteur=bases[1], authentification="aucune"))
    assert prod.get(f"{V1}/dev/utilisateurs").status_code == 404


def test_le_jeu_de_demonstration(bases):
    ids = semer(bases[0])
    client = TestClient(creer_app(moteur=bases[1], authentification="entete_dev"))
    moi = client.get(f"{V1}/moi", headers=en_tant_que(ids["drh"])).json()
    [org] = [o for o in moi["organisations"] if o["id"] == str(ids["organisation"])]
    assert (org["nom"], org["role"]) == ("AZITO (démonstration)", "admin_client")
    fichiers = client.get(f"{V1}/organisations/{org['id']}/fichiers", headers=en_tant_que(ids["drh"])).json()
    assert fichiers[0]["effectif"] == 23
    r = client.get(f"{V1}/organisations/{org['id']}/remuneration", headers=en_tant_que(ids["drh"])).json()
    assert r["en_vigueur"] is not None
    with bases[0].connect() as c:
        assert c.execute(text("SELECT nom_affiche FROM utilisateurs WHERE id = :u"), {"u": ids["conseiller"]}).scalar_one()
