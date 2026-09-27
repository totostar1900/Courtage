"""L'équipe : des droits et une fonction libre ; qui gère qui ; les garde-fous."""
from tests.outils import V1, deposer, en_tant_que, fichier_azito


def equipe(client, a, qui="drh"):
    return client.get(f"{V1}/organisations/{a['org']}/equipe", headers=en_tant_que(a[qui])).json()


def inscrire(client, a, qui, telephone, role, fonction=None, nom="Quelqu'un"):
    return client.post(f"{V1}/organisations/{a['org']}/membres", headers=en_tant_que(a[qui]),
                       json={"telephone": telephone, "nom_affiche": nom, "role": role, "fonction": fonction})


def test_chacun_donne_les_droits_qu_il_gere(client, azito):
    assert [d["role"] for d in equipe(client, azito, "conseiller")["droits_attribuables"]] == [
        "admin_client", "contributeur_client", "lecteur_client", "conseiller"]
    e = equipe(client, azito, "drh")
    assert [d["role"] for d in e["droits_attribuables"]] == ["admin_client", "contributeur_client", "lecteur_client"]
    assert "DAF" in e["fonctions"]
    conseiller = next(m for m in e["membres"] if m["role"] == "conseiller")
    assert conseiller["modifiable"] is False and conseiller["retirable"] is False     # la DRH ne gère pas le conseiller
    assert inscrire(client, azito, "drh", "+237 6 99 00 00 21", "conseiller").status_code == 403
    r = inscrire(client, azito, "drh", "+237 6 99 00 00 22", "contributeur_client", fonction="DAF", nom="M. DAF")
    assert r.status_code == 201, r.text
    daf = next(m for m in equipe(client, azito)["membres"] if m["nom"] == "M. DAF")
    assert (daf["fonction"], daf["droits"], daf["modifiable"], daf["retirable"]) == ("DAF", "Contributeur", True, True)


def test_le_contributeur_prepare_sans_decider(client, azito):
    r = inscrire(client, azito, "conseiller", "+237 6 99 00 00 23", "contributeur_client", nom="Contributeur")
    contributeur = r.json()["utilisateur_id"]
    h = en_tant_que(contributeur)
    deposer(client, azito["org"], contributeur, fichier_azito())                      # il dépose
    r = client.post(f"{V1}/organisations/{azito['org']}/regimes", json={"nom": "Essai"}, headers=h)
    assert r.status_code == 201                                                       # il prépare
    assert inscrire(client, {**azito, "c": contributeur}, "c", "+237 6 99 00 00 24", "lecteur_client").status_code == 403
    assert equipe(client, {**azito, "c": contributeur}, "c")["droits_attribuables"] == []


def test_modifier_et_retirer_avec_les_garde_fous(client, azito):
    org = azito["org"]
    drh_id = str(azito["drh"])
    h = en_tant_que(azito["drh"])
    # La fonction change ; le dernier administrateur ne se rétrograde pas et ne se retire pas.
    r = client.patch(f"{V1}/organisations/{org}/membres/{drh_id}", json={"fonction": "DRH"}, headers=h)
    assert r.status_code == 200 and next(m for m in r.json()["membres"] if m["id"] == drh_id)["fonction"] == "DRH"
    r = client.patch(f"{V1}/organisations/{org}/membres/{drh_id}", json={"role": "lecteur_client"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "dernier_du_role"
    assert client.delete(f"{V1}/organisations/{org}/membres/{drh_id}", headers=h).json()["code"] == "dernier_du_role"
    # Avec un second administrateur, le premier peut partir ; ce qu'il a fait reste au journal.
    autre = inscrire(client, azito, "drh", "+237 6 99 00 00 25", "admin_client", fonction="DG").json()["utilisateur_id"]
    r = client.delete(f"{V1}/organisations/{org}/membres/{drh_id}", headers=en_tant_que(autre))
    assert r.status_code == 200
    assert drh_id not in {m["id"] for m in r.json()["membres"]}
    # Le conseiller, dernier de son rôle, reste.
    conseiller = str(azito["conseiller"])
    r = client.delete(f"{V1}/organisations/{org}/membres/{conseiller}", headers=en_tant_que(azito["conseiller"]))
    assert r.json()["code"] == "dernier_du_role"


def test_le_nom_d_une_personne_qui_suit_d_autres_dossiers_ne_se_change_pas_ici(client, azito, personnes):
    admin = en_tant_que(personnes["admin"])
    autre = client.post(f"{V1}/organisations", json={"nom": "Autre SA", "pays": "CM"}, headers=admin).json()["id"]
    client.post(f"{V1}/organisations/{autre}/adhesions", headers=admin,
                json={"utilisateur_id": str(azito["drh"]), "role": "lecteur_client"})
    r = client.patch(f"{V1}/organisations/{azito['org']}/membres/{azito['drh']}", json={"nom_affiche": "Autre nom"},
                     headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 409 and r.json()["code"] == "nom_partage"
