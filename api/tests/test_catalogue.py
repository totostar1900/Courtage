"""Le catalogue anonyme des régimes : partager, retirer, consulter — sans qu'une entreprise se reconnaisse."""
import json

from sqlalchemy import text

from tests.outils import V1, en_tant_que


def entreprise(client, personnes, nom, taux=0.85, pays="CM", categorie="*", adopter=True):
    """Un dossier, sa DRH, un régime adopté (au-dessus de la convention du commerce)."""
    admin = en_tant_que(personnes["admin"])
    org = client.post(f"{V1}/organisations", json={"nom": nom, "pays": pays}, headers=admin).json()["id"]
    for qui, role in (("drh", "admin_client"), ("conseiller", "conseiller")):
        client.post(f"{V1}/organisations/{org}/adhesions", json={"utilisateur_id": str(personnes[qui]), "role": role},
                    headers=admin)
    drh = en_tant_que(personnes["drh"])
    r = client.post(f"{V1}/organisations/{org}/regimes", json={"nom": f"Accord {nom}"}, headers=drh).json()
    v = client.post(f"{V1}/organisations/{org}/regimes/{r['id']}/versions", headers=drh, json={
        "en_vigueur_du": "2024-01-01", "fondement": "accord_entreprise",
        "document_reference": f"Accord secret de {nom}, art. 7", "note": f"Négocié avec le syndicat de {nom}",
        "categories": [{"categorie": categorie, "convention_code": "CM_COMMERCE" if pays == "CM" else "CI_CCI", "bareme": {
            "forme": "tranches_cumulatives", "tranches": [{"jusqu_a": None, "mois_par_annee": taux}]}}]}).json()
    if adopter:
        a = client.post(f"{V1}/organisations/{org}/regimes/versions/{v['id']}/adoption", headers=drh,
                        json={"accepte_non_conformite": False})
        assert a.status_code == 200, a.text
    return {"org": org, "version": v["id"], "nom": nom}


def partager(client, personnes, e, secteur="commerce", taille="50_a_250", consentement=True, qui="drh"):
    return client.post(f"{V1}/organisations/{e['org']}/regimes/versions/{e['version']}/partage",
                       headers=en_tant_que(personnes[qui]),
                       json={"secteur": secteur, "taille": taille, "consentement": consentement})


def test_le_catalogue_ne_montre_rien_avant_cinq_puis_des_groupes_anonymes(client, personnes):
    # Qui n'appartient à aucune entreprise confirmée ne consulte pas le catalogue.
    r = client.get(f"{V1}/catalogue/regimes", headers=en_tant_que(personnes["etranger"]))
    assert r.status_code == 403 and r.json()["code"] == "inscription_non_confirmee"
    catalogue = lambda: client.get(f"{V1}/catalogue/regimes", headers=en_tant_que(personnes["admin"])).json()  # noqa: E731
    assert catalogue()["groupes"] == []
    entreprises = [entreprise(client, personnes, f"Entreprise {i}", taux=0.8 + i / 20,
                              categorie="Pilotes de ligne" if i == 0 else "*") for i in range(5)]
    for e in entreprises[:4]:
        assert partager(client, personnes, e).status_code == 201
    assert catalogue()["groupes"] == [] and catalogue()["entreprises"] == 4
    partager(client, personnes, entreprises[4])
    c = catalogue()
    [groupe] = c["groupes"]
    assert (groupe["pays"], groupe["secteur"], groupe["taille"]) == ("CM", "commerce", "50_a_250")
    assert groupe["libelle"] == "Commerce et distribution · Cameroun · 50 à 250 salariés"
    assert groupe["entreprises"] == 5 and len(groupe["regimes"]) == 5
    # Trié par générosité, jamais dans l'ordre du partage.
    ecarts = [r["ecart_convention_20_ans"] for r in groupe["regimes"]]
    assert ecarts == sorted(ecarts, reverse=True)
    # Rien de reconnaissable : ni nom, ni document, ni note, ni date, ni organisation.
    brut = json.dumps(c, ensure_ascii=False)
    for e in entreprises:
        assert e["nom"] not in brut and e["org"] not in brut and e["version"] not in brut
    assert "Accord secret" not in brut and "syndicat" not in brut and "2024" not in brut
    assert "Pilotes" not in brut and "Catégorie A" in brut
    assert groupe["regimes"][0]["convention_code"] == "CM_COMMERCE"       # le secteur est montré : la convention aussi

    # Une entreprise d'un autre secteur, seule : la CEMAC redevient un seul groupe, sans secteur ni convention.
    banque = entreprise(client, personnes, "Banque seule")
    partager(client, personnes, banque, secteur="banque_assurance")
    [groupe] = catalogue()["groupes"]
    assert (groupe["pays"], groupe["secteur"], groupe["taille"]) == ("CM", None, None) and groupe["entreprises"] == 6
    assert all(r["convention_code"] is None for r in groupe["regimes"])
    # Elle se retire : le groupe du commerce revient.
    [partage] = client.get(f"{V1}/organisations/{banque['org']}/regimes/partages", headers=en_tant_que(personnes["drh"])).json()
    client.post(f"{V1}/organisations/{banque['org']}/regimes/partages/{partage['partage_id']}/retrait",
                headers=en_tant_que(personnes["drh"]))
    assert catalogue()["groupes"][0]["secteur"] == "commerce"
    moi = client.get(f"{V1}/organisations/{entreprises[0]['org']}/regimes/partages", headers=en_tant_que(personnes["drh"])).json()
    assert moi[0]["actif"] and moi[0]["visible"]


def test_seule_la_drh_partage_une_version_adoptee_avec_son_accord(client, personnes):
    e = entreprise(client, personnes, "Prudente")
    assert partager(client, personnes, e, qui="conseiller").status_code == 403
    assert partager(client, personnes, e, consentement=False).json()["code"] == "consentement_requis"
    assert partager(client, personnes, e, secteur="inconnu").status_code == 422
    projet = entreprise(client, personnes, "En projet", adopter=False)
    assert partager(client, personnes, projet).json()["code"] == "version_non_adoptee"
    hors = entreprise(client, personnes, "Abidjan", pays="CI")
    assert partager(client, personnes, hors).json()["code"] == "hors_cemac"


def test_un_seul_partage_actif_par_entreprise_et_le_lien_reste_chez_elle(client, personnes, bases):
    e = entreprise(client, personnes, "Deux fois")
    premier = partager(client, personnes, e).json()["partage_id"]
    second = partager(client, personnes, e, taille="plus_de_250").json()["partage_id"]
    liste = client.get(f"{V1}/organisations/{e['org']}/regimes/partages", headers=en_tant_que(personnes["drh"])).json()
    assert {(p["partage_id"], p["actif"]) for p in liste} == {(premier, False), (second, True)}
    # Une autre entreprise ne voit pas ce lien, et ne peut pas retirer ce partage.
    autre = entreprise(client, personnes, "Voisine")
    assert client.get(f"{V1}/organisations/{autre['org']}/regimes/partages", headers=en_tant_que(personnes["drh"])).json() == []
    r = client.post(f"{V1}/organisations/{autre['org']}/regimes/partages/{second}/retrait", headers=en_tant_que(personnes["drh"]))
    assert r.status_code == 404
    # La table publique ne porte aucune organisation, et le rôle applicatif ne peut ni la modifier ni l'effacer.
    with bases[0].connect() as c:
        colonnes = c.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'catalogue_regimes'")).scalars().all()
        droits = c.execute(text("SELECT privilege_type FROM information_schema.role_table_grants "
                                "WHERE grantee = 'courtage_app' AND table_name = 'catalogue_regimes'")).scalars().all()
    assert "organisation_id" not in colonnes and sorted(droits) == ["INSERT", "SELECT"]
