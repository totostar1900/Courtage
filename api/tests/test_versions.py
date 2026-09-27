"""Le parcours d'une version de régime : projet, à venir, en vigueur, remplacée, abandonnée, supprimée."""
from sqlalchemy import text

from tests.outils import V1, en_tant_que, etude
from tests.test_regime import CADRES, CCI, adopter, categorie, regime, version


def lister(client, a, qui="drh"):
    [r] = client.get(f"{V1}/organisations/{a['org']}/regimes", headers=en_tant_que(a[qui])).json()
    return {v["numero"]: v for v in r["versions"]}


def test_l_etat_se_lit_sur_les_dates(client, azito):
    v1 = regime(client, azito, [categorie("*", CCI)], en_vigueur_du="2015-03-12")
    assert lister(client, azito)[1]["etat"] == "projet"
    adopter(client, azito, v1["id"])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2020-01-01")
    v3 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2099-01-01")
    assert lister(client, azito)[1]["etat"] == "en_vigueur"
    adopter(client, azito, v2["id"])
    adopter(client, azito, v3["id"])
    vs = lister(client, azito)
    assert vs[1]["etat"] == "remplacee" and vs[1]["remplacee_par"] == 2 and vs[1]["jusqu_au"] == "2020-01-01"
    assert vs[2]["etat"] == "en_vigueur"
    assert vs[3]["etat"] == "a_venir"


def test_un_projet_s_abandonne_avec_un_motif_et_ne_bouge_plus(client, azito, bases):
    v = regime(client, azito, [categorie("*", CADRES)])
    url = f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}"
    assert client.post(f"{url}/abandon", json={"motif": "x"}, headers=en_tant_que(azito["lecteur"] if "lecteur" in azito
                       else azito["etranger"])).status_code == 403
    r = client.post(f"{url}/abandon", json={"motif": "Avenant non signé"}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200, r.text
    assert (r.json()["etat"], r.json()["motif_abandon"]) == ("abandonnee", "Avenant non signé")
    assert adopter(client, azito, v["id"]).status_code == 409
    assert client.post(f"{url}/abandon", json={"motif": "encore"}, headers=en_tant_que(azito["drh"])).json()["code"] == "version_non_projet"
    r = etude(client, azito, regime_version_id=v["id"], convention_code=None)
    assert r.status_code == 422 and r.json()["code"] == "version_abandonnee"
    # La base elle-même refuse de la modifier.
    with bases[0].connect() as c:
        statut = c.execute(text("SELECT statut FROM regimes_versions WHERE id = :v"), {"v": v["id"]}).scalar()
    assert statut == "abandonnee"


def test_une_version_adoptee_ne_s_abandonne_ni_ne_se_supprime(client, azito):
    v = regime(client, azito, [categorie("*", CADRES)])
    adopter(client, azito, v["id"])
    url = f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}"
    h = en_tant_que(azito["drh"])
    assert client.post(f"{url}/abandon", json={"motif": "x"}, headers=h).json()["code"] == "version_non_projet"
    assert client.delete(url, headers=h).json()["code"] == "version_non_projet"


def test_un_projet_jamais_etudie_se_supprime_et_son_regime_vide_avec(client, azito):
    v1 = regime(client, azito, [categorie("*", CADRES)])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CCI)], en_vigueur_du="2016-01-01")
    etude(client, azito, regime_version_id=v2["id"], convention_code=None)
    h = en_tant_que(azito["drh"])
    base = f"{V1}/organisations/{azito['org']}/regimes/versions"
    r = client.delete(f"{base}/{v2['id']}", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "version_utilisee"
    assert lister(client, azito)[2]["etudes"] == 1
    assert client.delete(f"{base}/{v1['id']}", headers=h).json() == {"supprimee": True, "regime_supprime": False}
    assert set(lister(client, azito)) == {2}
    # Le dernier projet parti, le régime part avec.
    autre = regime(client, azito, [categorie("*", CCI)], nom="Essai")
    assert client.delete(f"{base}/{autre['id']}", headers=h).json() == {"supprimee": True, "regime_supprime": True}
    noms = [r["nom"] for r in client.get(f"{V1}/organisations/{azito['org']}/regimes", headers=h).json()]
    assert "Essai" not in noms
