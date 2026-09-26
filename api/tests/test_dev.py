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
    prod = TestClient(creer_app(moteur=bases[1], authentification="session"))
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


def test_la_societe_demo_se_seme_au_demarrage_et_une_seule_fois(bases, monkeypatch):
    """COURTAGE_DEMO=1 : le site en ligne montre le même dossier fictif que la démonstration, suivi par
    l'administrateur ; un redémarrage ne le recrée pas ; la production le refuse."""
    import uuid
    from courtage.amorcer import amorcer
    from courtage.demo import NOM_DEMO, depuis_environnement
    from tests.conftest import MOT_DE_PASSE_APP
    monkeypatch.delenv("COURTAGE_ENV", raising=False)
    url = bases[0].url.render_as_string(hide_password=False)
    tel = f"+2376{uuid.uuid4().int % 10**8:08d}"
    admin, _ = amorcer(url, tel, "Admin en ligne")
    env = {"COURTAGE_DEMO": "1", "COURTAGE_URL_PROPRIETAIRE": url, "COURTAGE_MOT_DE_PASSE_APP": MOT_DE_PASSE_APP}
    assert depuis_environnement({}) is None
    assert "production" in depuis_environnement({**env, "COURTAGE_ENV": "production"})
    assert "semée" in depuis_environnement(env)
    assert "déjà" in depuis_environnement(env)

    client = TestClient(creer_app(moteur=bases[1], authentification="entete_dev"))
    dossiers = client.get(f"{V1}/moi", headers=en_tant_que(admin)).json()["organisations"]
    [demo] = [o for o in dossiers if o["nom"] == NOM_DEMO]
    assert demo["role"] == "conseiller" and demo["pays"] == "CM"
    base = f"{V1}/organisations/{demo['id']}"
    etudes = client.get(f"{base}/etudes", headers=en_tant_que(admin)).json()
    assert sorted(e["statut"] for e in etudes) == ["brouillon", "emise"]
    assert client.get(f"{base}/fichiers", headers=en_tant_que(admin)).json()[0]["effectif"] == 40
    [fiche] = client.get(f"{base}/fiches", headers=en_tant_que(admin)).json()
    assert len(client.get(f"{base}/fiches/{fiche['id']}/reponses", headers=en_tant_que(admin)).json()["reponses"]) == 3
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM organisations WHERE nom = :n"), {"n": NOM_DEMO}).scalar() == 1
