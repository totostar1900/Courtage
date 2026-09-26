"""Barème d'entreprise : un accord, un contrat ou un usage plus généreux que la convention.

Une entreprise peut verser plus que sa convention, jamais moins. Si elle le fait
habituellement, sa dette réelle est plus lourde que la dette conventionnelle
(obligation implicite, IAS 19) : l'étude doit l'évaluer avec SON barème.
"""
import pytest
from sqlalchemy import text

from tests.outils import V1, en_tant_que, etude

GENEREUX = {"forme": "tranches_cumulatives", "tranches": [
    {"jusqu_a": 5, "mois_par_annee": 0.40}, {"jusqu_a": 10, "mois_par_annee": 0.50},
    {"jusqu_a": None, "mois_par_annee": 0.60}]}


def proposer(client, a, qui="drh", **champs):
    corps = {"libelle": "Accord d'entreprise du 12/03/2015", "fondement": "accord_entreprise",
             "document_reference": "Accord AZITO 2015, art. 12", "convention_code": "CI_CCI",
             "en_vigueur_du": "2015-03-12", "bareme": GENEREUX, **champs}
    return client.post(f"{V1}/organisations/{a['org']}/baremes", json=corps, headers=en_tant_que(a[qui]))


def valider(client, a, bareme_id, qui="conseiller"):
    return client.post(f"{V1}/organisations/{a['org']}/baremes/{bareme_id}/validation", headers=en_tant_que(a[qui]))


def test_une_etude_evaluee_avec_le_bareme_de_l_entreprise(client, azito):
    b = proposer(client, azito)
    assert b.status_code == 201, b.text
    assert b.json()["statut"] == "propose"
    assert valider(client, azito, b.json()["id"]).json()["statut"] == "valide"

    conventionnelle = etude(client, azito).json()
    e = etude(client, azito, bareme_entreprise_id=b.json()["id"])
    assert e.status_code == 201, e.text
    e = e.json()
    assert e["bareme_entreprise"]["libelle"] == "Accord d'entreprise du 12/03/2015"
    assert e["totaux"]["dette"] > conventionnelle["totaux"]["dette"]
    # Ce que l'accord coûte au-delà de la convention se lit dans l'étude.
    assert e["totaux_convention"]["dette"] == conventionnelle["totaux"]["dette"]
    assert e["emission"] == {"possible": True, "motifs": []}


def test_un_bareme_moins_genereux_que_la_convention_est_refuse(client, azito):
    r = proposer(client, azito, bareme={"forme": "tranches_cumulatives",
                                        "tranches": [{"jusqu_a": None, "mois_par_annee": 0.35}]})
    assert r.status_code == 422
    assert r.json()["code"] == "bareme_inferieur_convention"
    assert r.json()["details"]["anciennetes"][0] == 16


def test_un_bareme_non_valide_ne_sort_pas(client, azito):
    b = proposer(client, azito).json()
    e = etude(client, azito, bareme_entreprise_id=b["id"]).json()
    assert "bareme_entreprise_a_valider" in e["emission"]["motifs"]


def test_un_bareme_hors_vigueur_a_la_date_d_evaluation(client, azito):
    b = proposer(client, azito, en_vigueur_du="2021-01-01").json()
    valider(client, azito, b["id"])
    e = etude(client, azito, bareme_entreprise_id=b["id"]).json()
    assert "bareme_entreprise_hors_vigueur" in e["emission"]["motifs"]


def test_le_bareme_ameliore_la_convention_de_l_etude(client, azito):
    b = proposer(client, azito).json()
    r = etude(client, azito, convention_code="MG_APB", bareme_entreprise_id=b["id"])
    assert r.status_code == 422
    assert r.json()["code"] == "bareme_autre_convention"


def test_seul_le_conseiller_valide(client, azito):
    b = proposer(client, azito).json()
    assert valider(client, azito, b["id"], qui="drh").status_code == 403


def test_un_bareme_valide_ne_se_modifie_plus(client, azito, bases):
    b = proposer(client, azito).json()
    valider(client, azito, b["id"])
    with pytest.raises(Exception, match="bareme_valide_immuable"):
        with bases[0].begin() as c:
            c.execute(text("UPDATE baremes_entreprise SET libelle = 'autre' WHERE id = :b"), {"b": b["id"]})


def test_le_bareme_d_une_autre_organisation_est_introuvable(client, azito, personnes):
    b = proposer(client, azito).json()
    autre = client.post(f"{V1}/organisations", json={"nom": "Autre", "pays": "CI"},
                        headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{autre}/adhesions", json={"utilisateur_id": str(personnes["conseiller"]),
                                                               "role": "conseiller"}, headers=en_tant_que(personnes["admin"]))
    r = client.post(f"{V1}/organisations/{autre}/baremes/{b['id']}/validation",
                    headers=en_tant_que(personnes["conseiller"]))
    assert r.status_code == 404


def test_liste_des_baremes(client, azito):
    proposer(client, azito)
    r = client.get(f"{V1}/organisations/{azito['org']}/baremes", headers=en_tant_que(azito["drh"]))
    assert [b["fondement"] for b in r.json()] == ["accord_entreprise"]


def test_un_bareme_depasse_par_une_revision_de_la_convention(client, personnes):
    """Le minimum légal monte : un accord de 2015 aux taux du commerce 2012 tombe sous la révision de 2024."""
    from tests.outils import deposer, fichier_azito
    org = client.post(f"{V1}/organisations", json={"nom": "Négoce Douala", "pays": "CM"},
                      headers=en_tant_que(personnes["admin"])).json()["id"]
    client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes["conseiller"]),
                                                             "role": "conseiller"}, headers=en_tant_que(personnes["admin"]))
    a = {"org": org, **personnes}
    commerce_2012 = {"forme": "tranches_cumulatives", "tranches": [
        {"jusqu_a": 5, "mois_par_annee": 0.40}, {"jusqu_a": 10, "mois_par_annee": 0.45},
        {"jusqu_a": 15, "mois_par_annee": 0.60}, {"jusqu_a": 20, "mois_par_annee": 0.65},
        {"jusqu_a": None, "mois_par_annee": 0.75}]}
    b = proposer(client, a, qui="conseiller", convention_code="CM_COMMERCE", en_vigueur_du="2015-01-01",
                 bareme=commerce_2012)
    assert b.status_code == 201, b.text
    valider(client, a, b.json()["id"])
    f = deposer(client, org, personnes["conseiller"], fichier_azito(), date_donnees="2024-12-31")
    e = client.post(f"{V1}/organisations/{org}/etudes", headers=en_tant_que(personnes["conseiller"]), json={
        "fichier_id": f["id"], "date_evaluation": "2024-12-31", "convention_code": "CM_COMMERCE",
        "fonds_disponible": 0, "bareme_entreprise_id": b.json()["id"]}).json()
    assert "bareme_inferieur_convention" in e["emission"]["motifs"]
