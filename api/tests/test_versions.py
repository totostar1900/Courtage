"""Une version de régime : brouillon ou adoptée. Modifier, dupliquer, supprimer, communiquer (notes), ménage."""
import pymupdf
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.outils import V1, en_tant_que, etude
from tests.test_regime import CADRES, CCI, adopter, categorie, regime, version


def lister(client, a, qui="drh"):
    rs = client.get(f"{V1}/organisations/{a['org']}/regimes", headers=en_tant_que(a[qui])).json()
    return {v["numero"]: v for r in rs for v in r["versions"]}


def url(a, v):
    return f"{V1}/organisations/{a['org']}/regimes/versions/{v['id']}"


def test_les_dates_sont_une_information_pas_un_statut(client, azito):
    v1 = regime(client, azito, [categorie("*", CCI)], en_vigueur_du="2015-03-12")
    assert lister(client, azito)[1]["application"] is None                      # un brouillon
    adopter(client, azito, v1["id"])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2099-01-01")
    adopter(client, azito, v2["id"])
    vs = lister(client, azito)
    assert {v["statut"] for v in vs.values()} == {"adoptee"}
    assert vs[1]["application"] == {"a_venir": False, "depuis": "2015-03-12", "remplacee_le": "2099-01-01",
                                    "remplacee_par": 2, "en_cours": True}
    assert vs[2]["application"]["a_venir"] is True


def test_un_brouillon_se_corrige_sur_place_et_une_version_adoptee_se_duplique(client, azito):
    v = regime(client, azito, [categorie("*", CCI)])
    corps = {"en_vigueur_du": "2016-06-01", "fondement": "accord_entreprise", "document_reference": "Avenant corrigé",
             "categories": [categorie("*", CADRES), categorie("Cadre", CADRES)]}
    r = client.put(url(azito, v), json=corps, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200, r.text
    assert (r.json()["numero"], r.json()["document_reference"]) == (1, "Avenant corrigé")
    adopter(client, azito, v["id"])
    assert client.put(url(azito, v), json=corps, headers=en_tant_que(azito["drh"])).json()["code"] == "version_adoptee"
    r = client.post(f"{url(azito, v)}/duplication", headers=en_tant_que(azito["drh"]))
    assert r.status_code == 201
    copie = r.json()
    assert (copie["numero"], copie["statut"]) == (2, "analyse")
    assert {c["categorie"] for c in copie["categories"]} == {"*", "Cadre"}


def test_supprimer_un_brouillon_emporte_ses_etudes_en_brouillon(client, azito):
    v1 = regime(client, azito, [categorie("*", CADRES)])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CCI)], en_vigueur_du="2016-01-01")
    e = etude(client, azito, regime_version_id=v2["id"], convention_code=None).json()
    assert lister(client, azito)[2]["suppression"] == {"possible": True, "reservee_entreprise": False,
                                                        "brouillons": 1, "raison": None}
    h = en_tant_que(azito["conseiller"])
    assert client.delete(url(azito, v2), headers=h).json() == {"supprimee": True, "regime_supprime": False}
    assert client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}", headers=h).status_code == 404
    assert client.delete(url(azito, v1), headers=h).json() == {"supprimee": True, "regime_supprime": True}


def test_une_version_adoptee_se_supprime_si_rien_ne_la_cite(client, azito, bases):
    v = regime(client, azito, [categorie("*", CADRES)])
    adopter(client, azito, v["id"])
    assert client.delete(url(azito, v), headers=en_tant_que(azito["conseiller"])).status_code == 403
    r = client.delete(url(azito, v), headers=en_tant_que(azito["drh"]))
    assert r.status_code == 422 and r.json()["code"] == "motif_requis"
    # Une version adoptée qui reste ne se modifie pas, même en base, ni ses catégories.
    _, app = bases
    with app.begin() as c:
        c.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": azito["org"]})
        with pytest.raises(DBAPIError, match="version_adoptee_immuable"):
            with c.begin_nested():
                c.execute(text("DELETE FROM regimes_categories WHERE version_id = :v"), {"v": v["id"]})
    r = client.delete(url(azito, v), params={"motif": "Adoptée par erreur"}, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200, r.text


def test_une_note_emise_retient_la_version(client, azito):
    v = regime(client, azito, [categorie("*", CCI), categorie("Cadre", CADRES)])
    h = en_tant_que(azito["drh"])
    assert client.post(f"{url(azito, v)}/notes/salaries", headers=h).json()["code"] == "version_non_adoptee"
    adopter(client, azito, v["id"])
    r = client.post(f"{url(azito, v)}/notes/salaries", headers=h)
    assert r.status_code == 200, r.text
    numero = r.json()["numero"]
    assert numero.startswith("NR-")
    assert client.post(f"{url(azito, v)}/notes/salaries", headers=h).json()["numero"] == numero     # la même
    pdf = client.get(f"{url(azito, v)}/notes/salaries", headers=en_tant_que(azito["conseiller"]))
    assert pdf.headers["content-type"] == "application/pdf"
    with pymupdf.open(stream=pdf.content, filetype="pdf") as doc:
        texte = " ".join(p.get_text() for p in doc)
    assert "Ce que vous recevrez à votre départ en retraite" in texte and "minimum de la" in texte
    assert "dette" not in texte.lower()
    assureurs = client.post(f"{url(azito, v)}/notes/assureurs", headers=h).json()["numero"]
    with pymupdf.open(stream=client.get(f"{url(azito, v)}/notes/assureurs", headers=h).content, filetype="pdf") as doc:
        texte = " ".join(p.get_text() for p in doc)
    assert "La population" in texte and "Cadre" in texte
    vs = lister(client, azito)
    assert vs[1]["notes"] == {"salaries": numero, "assureurs": assureurs}
    assert vs[1]["suppression"]["possible"] is False and "2 notes émises" in vs[1]["suppression"]["raison"]
    assert client.get(f"{V1}/verifier/{numero}").json()["authentique"] is True


def test_le_menage(client, azito, bases):
    h = en_tant_que(azito["drh"])
    base = f"{V1}/organisations/{azito['org']}/regimes"
    adoptee = regime(client, azito, [categorie("*", CCI)])
    adopter(client, azito, adoptee["id"])
    vieux = version(client, azito, adoptee["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2016-01-01")
    etude(client, azito, regime_version_id=vieux["id"], convention_code=None)
    recent = version(client, azito, adoptee["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2017-01-01")
    with bases[0].begin() as c:
        c.execute(text("UPDATE regimes_versions SET cree_le = now() - interval '120 days' WHERE id = :v"), {"v": vieux["id"]})
    m = {c["numero"]: c for c in client.get(f"{base}/menage", headers=h).json()["candidats"]}
    assert set(m) == {1, 2, 3}
    assert m[2]["coche"] and "120 jours" in m[2]["raison"] and "brouillon partira" in m[2]["raison"]
    assert not m[3]["coche"] and not m[1]["coche"] and m[1]["motif_requis"]
    conseil = client.get(f"{base}/menage", headers=en_tant_que(azito["conseiller"])).json()["candidats"]
    assert {c["numero"] for c in conseil} == {2, 3}
    assert any(a["code"] == "projet_a_trancher" for a in client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=h).json())
    r = client.post(f"{base}/menage", json={"versions": [m[2]["version_id"], recent["id"]]}, headers=h)
    assert r.json() == {"versions": 2, "brouillons": 1}
    assert set(lister(client, azito)) == {1}


# --- Fichiers, conditions, contrats : les données de travail --------------------------------------------------

def test_un_fichier_se_supprime_ou_s_allege_selon_ce_qui_le_cite(client, azito):
    from tests.outils import deposer, fichier_azito
    org, h = azito["org"], en_tant_que(azito["drh"])
    autre = deposer(client, org, azito["drh"], fichier_azito(), date_donnees="2019-06-30")
    etude(client, azito, fichier_id=autre["id"])                                     # un brouillon
    f = next(x for x in client.get(f"{V1}/organisations/{org}/fichiers", headers=h).json() if x["id"] == autre["id"])
    assert (f["etudes_emises"], len(f["brouillons"])) == (0, 1)
    assert client.delete(f"{V1}/organisations/{org}/fichiers/{autre['id']}", headers=h).json() == {"supprime": True, "brouillons": 1}
    # Le fichier d'une étude émise ne se supprime pas ; il s'allège, une fois.
    e = etude(client, azito).json()
    client.post(f"{V1}/organisations/{org}/etudes/{e['id']}/emission", headers=en_tant_que(azito["conseiller"]))
    r = client.delete(f"{V1}/organisations/{org}/fichiers/{azito['fichier']}", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "fichier_cite"
    assert client.post(f"{V1}/organisations/{org}/fichiers/{azito['fichier']}/allegement", headers=h).json() == {"allege": True, "brouillons": 0}
    f = next(x for x in client.get(f"{V1}/organisations/{org}/fichiers", headers=h).json() if x["id"] == azito["fichier"])
    assert f["effectif"] == 0 and f["vide_le"] is not None
    assert client.post(f"{V1}/organisations/{org}/fichiers/{azito['fichier']}/allegement", headers=h).json()["code"] == "deja_allege"
    assert client.get(f"{V1}/organisations/{org}/etudes/{e['id']}/rapport", headers=h).status_code == 200


def test_un_contrat_saisi_par_erreur_se_supprime(client, azito):
    org, h = azito["org"], en_tant_que(azito["conseiller"])
    k = client.post(f"{V1}/organisations/{org}/contrats", headers=h, json={"en_vigueur_du": "2031-01-01", "service": "courtage", "mandat_reference": "Mandat test"}).json()
    assert client.delete(f"{V1}/organisations/{org}/contrats/{k['id']}", headers=h).json() == {"supprime": True}
