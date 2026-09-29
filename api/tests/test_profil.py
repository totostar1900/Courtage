"""L'espace personnel : l'identité, les dossiers, les appareils connectés."""
from courtage import auth
from sqlalchemy.orm import Session

from tests.outils import V1, en_tant_que


def test_le_profil_dit_qui_je_suis_et_ou(client, azito):
    p = client.get(f"{V1}/moi/profil", headers=en_tant_que(azito["drh"])).json()
    assert p["id"] == str(azito["drh"])
    [d] = [x for x in p["dossiers"] if x["id"] == azito["org"]]
    assert d["role"] == "admin_client"


def test_changer_son_nom(client, azito):
    r = client.patch(f"{V1}/moi/profil", json={"nom_affiche": "Awa K."}, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200 and r.json()["nom_affiche"] == "Awa K."
    assert client.patch(f"{V1}/moi/profil", json={"nom_affiche": "A"}, headers=en_tant_que(azito["drh"])).status_code == 422


def test_deconnecter_un_autre_appareil(client, azito, bases):
    from courtage.db import Utilisateur
    with Session(bases[1]) as s, s.begin():
        u = s.get(Utilisateur, azito["drh"])
        courant = auth.ouvrir_session(s, u, "Mozilla/5.0 (Windows NT 10.0) Chrome/130")
        auth.ouvrir_session(s, u, "Mozilla/5.0 (Linux; Android 14) Chrome/130")
    h = {"Authorization": f"Bearer {courant}"}
    p = client.get(f"{V1}/moi/profil", headers=h).json()
    assert [x["courante"] for x in p["sessions"]].count(True) == 1 and len(p["sessions"]) == 2
    autre = next(x for x in p["sessions"] if not x["courante"])
    p = client.delete(f"{V1}/moi/sessions/{autre['id']}", headers=h).json()
    assert [x["id"] for x in p["sessions"]] != [] and autre["id"] not in [x["id"] for x in p["sessions"]]
    # La session d'un autre utilisateur ne se ferme pas d'ici.
    assert client.delete(f"{V1}/moi/sessions/{p['sessions'][0]['id']}", headers=en_tant_que(azito["conseiller"])).status_code == 404
