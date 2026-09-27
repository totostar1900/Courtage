"""Nettoyer un dossier : l'archive d'abord, puis ce qui a été choisi ; les sceaux restent vérifiables."""
import io
import zipfile

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.outils import V1, en_tant_que, etude


def emettre(client, a):
    e = etude(client, a).json()
    r = client.post(f"{V1}/organisations/{a['org']}/etudes/{e['id']}/emission", headers=en_tant_que(a["conseiller"]))
    assert r.status_code == 200, r.text
    return r.json()


def test_l_archive_contient_les_documents_et_les_etudes(client, azito):
    e = emettre(client, azito)
    r = client.get(f"{V1}/organisations/{azito['org']}/archive", headers=en_tant_que(azito["drh"]))
    assert r.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        noms = z.namelist()
        assert any(n.startswith("documents/") and e["rapport"]["numero"] in n for n in noms)
        assert "etudes/etude-ifc-2019-12-31.xlsx" in noms
        assert e["rapport"]["numero"] in z.read("SOMMAIRE.txt").decode()


def test_nettoyer_garde_les_sceaux(client, azito, bases):
    org, h = azito["org"], en_tant_que(azito["drh"])
    e = emettre(client, azito)
    etude(client, azito)                                                               # un brouillon
    inv = client.get(f"{V1}/organisations/{org}/nettoyage", headers=h).json()
    assert inv["brouillons"]["etudes"] == 1 and inv["etudes_emises"] == {"total": 1, "supprimables": 1, "citees_par_un_cahier": 0}
    assert client.get(f"{V1}/organisations/{org}/nettoyage", headers=en_tant_que(azito["etranger"])).status_code == 403
    corps = {"fichiers": "supprimer", "brouillons": True, "etudes_emises": True, "confirmation": "non"}
    assert client.post(f"{V1}/organisations/{org}/nettoyage", json=corps, headers=h).json()["code"] == "confirmation_requise"
    r = client.post(f"{V1}/organisations/{org}/nettoyage", json={**corps, "confirmation": "nettoyer"}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json() == {"etudes_brouillon": 1, "versions_brouillon": 0, "etudes_emises": 1, "fichiers_alleges": 0,
                        "fichiers_supprimes": 1}
    assert client.get(f"{V1}/organisations/{org}/etudes", headers=h).json() == []
    assert client.get(f"{V1}/organisations/{org}/fichiers", headers=h).json() == []
    assert client.get(f"{V1}/verifier/{e['rapport']['numero']}").json()["authentique"] is True


def test_une_etude_emise_ne_se_supprime_pas_hors_du_nettoyage(azito, client, bases):
    e = emettre(client, azito)
    _, app = bases
    with app.begin() as c:
        c.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": azito["org"]})
        with pytest.raises(DBAPIError, match="etude_emise_immuable"):
            with c.begin_nested():
                c.execute(text("DELETE FROM documents WHERE etude_id = :e"), {"e": e["id"]})
                c.execute(text("DELETE FROM etudes WHERE id = :e"), {"e": e["id"]})


def test_alleger_le_personnel_garde_les_etudes_emises(client, azito):
    org, h = azito["org"], en_tant_que(azito["conseiller"])
    emettre(client, azito)
    r = client.post(f"{V1}/organisations/{org}/nettoyage", headers=h,
                    json={"fichiers": "supprimer", "confirmation": "NETTOYER"})
    assert r.json()["fichiers_alleges"] == 1 and r.json()["fichiers_supprimes"] == 0     # cité : allégé, pas supprimé
    [f] = client.get(f"{V1}/organisations/{org}/fichiers", headers=h).json()
    assert f["vide_le"] is not None and len(client.get(f"{V1}/organisations/{org}/etudes", headers=h).json()) == 1
