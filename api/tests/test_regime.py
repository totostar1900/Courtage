"""Le régime IFC de l'entreprise : versions, catégories, adoption, et l'étude qui s'y appuie."""
import pytest
from sqlalchemy import text

from tests.outils import V1, deposer, en_tant_que, etude, fichier_azito

CCI = {"forme": "tranches_cumulatives", "tranches": [
    {"jusqu_a": 5, "mois_par_annee": 0.30}, {"jusqu_a": 10, "mois_par_annee": 0.35},
    {"jusqu_a": None, "mois_par_annee": 0.40}]}
CADRES = {"forme": "tranches_cumulatives", "tranches": [
    {"jusqu_a": 5, "mois_par_annee": 0.60}, {"jusqu_a": 10, "mois_par_annee": 0.70},
    {"jusqu_a": None, "mois_par_annee": 0.80}]}
AVARE = {"forme": "tranches_cumulatives", "tranches": [{"jusqu_a": None, "mois_par_annee": 0.10}]}


def categorie(nom, bareme, **autres):
    return {"categorie": nom, "convention_code": "CI_CCI", "bareme": bareme, **autres}


def regime(client, a, categories, qui="drh", en_vigueur_du="2015-03-12", nom="Accord AZITO 2015"):
    r = client.post(f"{V1}/organisations/{a['org']}/regimes", json={"nom": nom}, headers=en_tant_que(a[qui]))
    assert r.status_code == 201, r.text
    return version(client, a, r.json()["id"], categories, qui=qui, en_vigueur_du=en_vigueur_du)


def version(client, a, regime_id, categories, qui="drh", en_vigueur_du="2015-03-12"):
    r = client.post(f"{V1}/organisations/{a['org']}/regimes/{regime_id}/versions", headers=en_tant_que(a[qui]), json={
        "en_vigueur_du": en_vigueur_du, "fondement": "accord_entreprise",
        "document_reference": "Accord d'entreprise du 12/03/2015, art. 12", "categories": categories})
    assert r.status_code == 201, r.text
    return r.json()


def adopter(client, a, version_id, qui="drh", accepte=False):
    return client.post(f"{V1}/organisations/{a['org']}/regimes/versions/{version_id}/adoption",
                       headers=en_tant_que(a[qui]), json={"accepte_non_conformite": accepte})


def fichier_par_categorie(client, a):
    """Les cinq premiers salariés d'AZITO en cadres."""
    return deposer(client, a["org"], a["drh"], fichier_azito(categories={i: "Cadre" for i in range(5)}))["id"]


# --- Versions, constats, adoption ---------------------------------------------

def test_un_regime_conforme(client, azito):
    v = regime(client, azito, [categorie("Cadre", CADRES), categorie("*", CCI)])
    assert v["statut"] == "analyse" and v["numero"] == 1
    assert [c["categorie"] for c in v["categories"]] == ["*", "Cadre"]
    assert v["constats"] == []
    r = adopter(client, azito, v["id"])
    assert r.status_code == 200, r.text
    assert r.json()["statut"] == "adoptee" and r.json()["non_conformite_acceptee"] is False


def test_un_regime_sous_le_plancher_est_enregistre_tel_quel(client, azito):
    v = regime(client, azito, [categorie("*", AVARE)])
    [c] = v["constats"]
    assert (c["niveau"], c["code"]) == ("bloque", "sous_le_plancher")
    assert c["details"]["anciennetes"][:2] == [1, 2]
    assert "1 à 50 ans" in c["message"]


def test_l_adoption_d_un_regime_non_conforme_demande_d_en_prendre_acte(client, azito):
    v = regime(client, azito, [categorie("*", AVARE)])
    r = adopter(client, azito, v["id"])
    assert r.status_code == 409 and r.json()["code"] == "non_conformite_a_accepter"
    r = adopter(client, azito, v["id"], accepte=True)
    assert r.status_code == 200
    assert r.json()["non_conformite_acceptee"] is True


def test_l_entreprise_adopte_pas_le_conseiller(client, azito):
    v = regime(client, azito, [categorie("*", CCI)], qui="conseiller")
    assert adopter(client, azito, v["id"], qui="conseiller").status_code == 403
    assert adopter(client, azito, v["id"], qui="drh").status_code == 200


def test_une_version_adoptee_ne_bouge_plus(client, azito, bases):
    v = regime(client, azito, [categorie("*", CCI)])
    adopter(client, azito, v["id"])
    for instruction in ("UPDATE regimes_versions SET note = 'x' WHERE id = :v",
                        "UPDATE regimes_categories SET anciennete_minimale = 3 WHERE version_id = :v"):
        with pytest.raises(Exception, match="version_adoptee_immuable"):
            with bases[0].begin() as c:
                c.execute(text(instruction), {"v": v["id"]})


def test_les_versions_se_numerotent(client, azito):
    v1 = regime(client, azito, [categorie("*", CCI)])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2019-06-01")
    assert v2["numero"] == 2
    liste = client.get(f"{V1}/organisations/{azito['org']}/regimes", headers=en_tant_que(azito["drh"])).json()
    [r] = liste
    assert [v["numero"] for v in r["versions"]] == [1, 2]


@pytest.mark.parametrize("categories,code", [
    ([], "regime_sans_categorie"),
    ([categorie("*", CCI), categorie("*", CADRES)], "categorie_en_double"),
    ([{**categorie("*", CCI), "convention_code": "CM_COMMERCE"}], "convention_autre_pays"),
    ([categorie("*", CCI, evenements=["deces"])], "evenements_invalides"),
    ([categorie("*", {"forme": "au_doigt_mouille"})], "bareme_mal_forme"),
])
def test_saisies_refusees(client, azito, categories, code):
    r = client.post(f"{V1}/organisations/{azito['org']}/regimes", json={"nom": "R"}, headers=en_tant_que(azito["drh"]))
    r = client.post(f"{V1}/organisations/{azito['org']}/regimes/{r.json()['id']}/versions", headers=en_tant_que(azito["drh"]),
                    json={"en_vigueur_du": "2015-01-01", "fondement": "usage", "document_reference": "Usage constant",
                          "categories": categories})
    assert r.status_code == 422 and r.json()["code"] == code


# --- L'étude s'appuie sur une version du régime -------------------------------

def test_etude_par_categorie(client, azito):
    v = regime(client, azito, [categorie("Cadre", CADRES), categorie("*", CCI)])
    adopter(client, azito, v["id"])
    f = fichier_par_categorie(client, azito)
    conventionnelle = etude(client, {**azito, "fichier": f}).json()
    e = etude(client, {**azito, "fichier": f}, convention_code=None, regime_version_id=v["id"])
    assert e.status_code == 201, e.text
    e = e.json()
    assert e["regime"]["nom"] == "Accord AZITO 2015"
    assert e["par_categorie"]["Cadre"]["effectif"] == 5 and e["par_categorie"]["Employé"]["effectif"] == 18
    assert e["totaux"]["dette"] > conventionnelle["totaux"]["dette"]
    assert e["totaux_convention"]["dette"] == conventionnelle["totaux"]["dette"]
    assert e["emission"] == {"possible": True, "motifs": []}


def test_une_categorie_du_fichier_sans_regle_est_refusee(client, azito):
    v = regime(client, azito, [categorie("Cadre", CADRES)])
    adopter(client, azito, v["id"])
    r = etude(client, {**azito, "fichier": fichier_par_categorie(client, azito)},
              convention_code=None, regime_version_id=v["id"])
    assert r.status_code == 422
    assert r.json()["code"] == "categories_inconnues"
    assert r.json()["details"]["categories"] == ["Employé"]


def test_un_regime_non_conforme_est_evalue_au_plancher_et_le_dit(client, azito):
    v = regime(client, azito, [categorie("*", AVARE)])
    adopter(client, azito, v["id"], accepte=True)
    conventionnelle = etude(client, azito).json()
    e = etude(client, azito, convention_code=None, regime_version_id=v["id"]).json()
    assert e["totaux"]["dette"] == conventionnelle["totaux"]["dette"]
    assert "non_conformite" in {a["code"] for a in e["anomalies"] if a["niveau"] == "avertissement"}
    assert e["emission"]["possible"] is True           # l'entreprise est souveraine, le rapport dira la vérité


def test_base_moyenne_12_mois_et_evenements_non_evalues_signales(client, azito):
    v = regime(client, azito, [categorie("*", CCI, base_salaire="moyenne_12_mois",
                                         evenements=["retraite", "deces"])])
    adopter(client, azito, v["id"])
    e = etude(client, azito, convention_code=None, regime_version_id=v["id"]).json()
    codes = {a["code"] for a in e["anomalies"]}
    assert {"base_salaire_approchee", "evenements_non_evalues"} <= codes


def test_une_version_non_adoptee_ne_sort_pas(client, azito):
    v = regime(client, azito, [categorie("*", CCI)])
    e = etude(client, azito, convention_code=None, regime_version_id=v["id"]).json()
    assert "regime_non_adopte" in e["emission"]["motifs"]


def test_une_version_remplacee_a_la_date_d_evaluation(client, azito):
    v1 = regime(client, azito, [categorie("*", CCI)])
    adopter(client, azito, v1["id"])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2019-06-01")
    adopter(client, azito, v2["id"])
    e = etude(client, azito, convention_code=None, regime_version_id=v1["id"]).json()
    assert "regime_hors_vigueur" in e["emission"]["motifs"]
    e = etude(client, azito, convention_code=None, regime_version_id=v2["id"]).json()
    assert "regime_hors_vigueur" not in e["emission"]["motifs"]


def test_une_etude_sans_regime_ni_convention(client, azito):
    r = etude(client, azito, convention_code=None)
    assert r.status_code == 422 and r.json()["code"] == "convention_ou_regime_requis"


def test_isolation_des_regimes(client, azito, personnes):
    v = regime(client, azito, [categorie("*", CCI)])
    autre = client.post(f"{V1}/organisations", json={"nom": "Autre", "pays": "CI"},
                        headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{autre}/adhesions", json={"utilisateur_id": str(personnes["drh"]),
                                                               "role": "admin_client"}, headers=en_tant_que(personnes["admin"]))
    r = client.post(f"{V1}/organisations/{autre}/regimes/versions/{v['id']}/adoption",
                    headers=en_tant_que(personnes["drh"]), json={"accepte_non_conformite": False})
    assert r.status_code == 404
