"""Le parcours d'une version de régime : projet, à venir, en vigueur, remplacée, abandonnée, supprimée."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

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


def test_une_version_appliquee_ne_s_abandonne_ni_ne_se_supprime(client, azito, bases):
    v = regime(client, azito, [categorie("*", CADRES)])
    adopter(client, azito, v["id"])
    url = f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}"
    h = en_tant_que(azito["drh"])
    assert client.post(f"{url}/abandon", json={"motif": "x"}, headers=h).json()["code"] == "version_non_projet"
    r = client.delete(url, params={"motif": "x"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "version_appliquee"
    assert lister(client, azito)[1]["suppression"]["possible"] is False
    # Et la base elle-même refuse.
    _, app = bases
    with app.begin() as c:
        c.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": azito["org"]})
        with pytest.raises(DBAPIError, match="version_adoptee_immuable"):
            with c.begin_nested():
                c.execute(text("DELETE FROM regimes_categories WHERE version_id = :v"), {"v": v["id"]})


def test_ce_qui_ne_s_est_jamais_applique_se_supprime_si_rien_ne_le_cite(client, azito):
    v1 = regime(client, azito, [categorie("*", CADRES)])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CCI)], en_vigueur_du="2016-01-01")
    etude(client, azito, regime_version_id=v2["id"], convention_code=None)
    h = en_tant_que(azito["drh"])
    base = f"{V1}/organisations/{azito['org']}/regimes/versions"
    r = client.delete(f"{base}/{v2['id']}", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "version_citee" and "brouillon" in r.json()["message"]
    vs = lister(client, azito)
    assert vs[2]["suppression"]["bloquee_par_brouillons"] is True and len(vs[2]["citations"]["brouillons"]) == 1
    assert client.delete(f"{base}/{v1['id']}", headers=h).json() == {"supprimee": True, "regime_supprime": False}
    # Une version abandonnée, jamais étudiée, se supprime aussi.
    v3 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2017-01-01")
    client.post(f"{base}/{v3['id']}/abandon", json={"motif": "Non retenu"}, headers=h)
    assert client.delete(f"{base}/{v3['id']}", headers=h).status_code == 200
    assert set(lister(client, azito)) == {2}
    # Le dernier projet parti, le régime part avec.
    autre = regime(client, azito, [categorie("*", CCI)], nom="Essai")
    assert client.delete(f"{base}/{autre['id']}", headers=h).json() == {"supprimee": True, "regime_supprime": True}
    noms = [r["nom"] for r in client.get(f"{V1}/organisations/{azito['org']}/regimes", headers=h).json()]
    assert "Essai" not in noms


def test_une_adoption_a_venir_s_annule_par_la_drh_avec_un_motif(client, azito):
    v = regime(client, azito, [categorie("*", CADRES)], en_vigueur_du="2099-01-01")
    adopter(client, azito, v["id"])
    url = f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}"
    assert client.delete(url, headers=en_tant_que(azito["conseiller"])).status_code == 403
    r = client.delete(url, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 422 and r.json()["code"] == "motif_requis"
    assert client.delete(url, params={"motif": "Avenant retiré avant son entrée en vigueur"},
                         headers=en_tant_que(azito["drh"])).status_code == 200


def test_un_projet_se_corrige_sur_place(client, azito):
    v = regime(client, azito, [categorie("*", CCI)])
    url = f"{V1}/organisations/{azito['org']}/regimes/versions/{v['id']}"
    corps = {"en_vigueur_du": "2016-06-01", "fondement": "accord_entreprise", "document_reference": "Avenant corrigé",
             "categories": [categorie("*", CADRES), categorie("Cadre", CADRES)]}
    r = client.put(url, json=corps, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200, r.text
    e = r.json()
    assert (e["numero"], e["en_vigueur_du"], e["document_reference"]) == (1, "2016-06-01", "Avenant corrigé")
    assert {c["categorie"] for c in e["categories"]} == {"*", "Cadre"}
    assert set(lister(client, azito)) == {1}                                      # pas de version de plus
    adopter(client, azito, v["id"])
    assert client.put(url, json=corps, headers=en_tant_que(azito["drh"])).json()["code"] == "version_non_projet"


def test_le_menage_propose_ce_qui_peut_partir_et_le_fait_en_une_fois(client, azito, bases):
    h = en_tant_que(azito["drh"])
    base = f"{V1}/organisations/{azito['org']}/regimes"
    en_vigueur = regime(client, azito, [categorie("*", CCI)])
    adopter(client, azito, en_vigueur["id"])
    vieux = version(client, azito, en_vigueur["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2016-01-01")
    etude(client, azito, regime_version_id=vieux["id"], convention_code=None)        # un brouillon le retient
    recent = version(client, azito, en_vigueur["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2017-01-01")
    a_venir = version(client, azito, en_vigueur["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2099-01-01")
    adopter(client, azito, a_venir["id"])
    with bases[0].begin() as c:
        c.execute(text("UPDATE regimes_versions SET cree_le = now() - interval '120 days' WHERE id = :v"), {"v": vieux["id"]})
    m = client.get(f"{base}/menage", headers=h).json()
    par_numero = {c["numero"]: c for c in m["candidats"]}
    assert set(par_numero) == {2, 3, 4}                                    # jamais la version en vigueur
    assert par_numero[2]["coche"] and "120 jours" in par_numero[2]["raison"] and "brouillon" in par_numero[2]["raison"]
    assert not par_numero[3]["coche"]                                      # récent : proposé, pas coché
    assert not par_numero[4]["coche"] and par_numero[4]["motif_requis"]    # une adoption à venir : à décider
    conseil = client.get(f"{base}/menage", headers=en_tant_que(azito["conseiller"])).json()
    assert {c["numero"] for c in conseil["candidats"]} == {2, 3}           # l'adoption à venir est à la DRH
    alertes = client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=h).json()
    assert any(a["code"] == "projet_a_trancher" for a in alertes)
    r = client.post(f"{base}/menage", json={"versions": [par_numero[2]["version_id"], par_numero[3]["version_id"]]},
                    headers=h)
    assert r.status_code == 200 and r.json() == {"versions": 2, "brouillons": 1}
    assert set(lister(client, azito)) == {1, 4}
    r = client.post(f"{base}/menage", json={"versions": [en_vigueur["id"]]}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "hors_menage"
