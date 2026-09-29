"""La clôture du placement : la police de l'offre retenue à la mise en vigueur, les appels de prime confrontés au
registre des comptes, le contre-appel, le virement déclaré, l'encaissement confirmé, les relevés. Rien n'est payé
par la plateforme."""
from datetime import date, timedelta

import pytest

from tests.outils import V1, en_tant_que, sous_mandat
from tests.test_comptes_assureurs import compte
from tests.test_reponses import cahier, repondre, u  # noqa: F401 — `cahier` est une fixture

PDF = ("doc.pdf", b"%PDF-1.4 doc", "application/pdf")
AUJOURD_HUI = date.today()
IBAN = "CM21 10003 00100 0512345678 91"


def url(a, suite=""):
    return f"{V1}/organisations/{a['org']}{suite}"


def police(client, a, assureur, **autres):
    r = client.post(url(a, "/polices"), headers=en_tant_que(a["conseiller"]), json={
        "assureur": assureur, "date_effet": (AUJOURD_HUI - timedelta(days=1)).isoformat(), "periodicite": "annuelle",
        **autres})
    assert r.status_code == 201, r.text
    return r.json()


def deposer(client, a, qui, p, nature, **champs):
    return client.post(url(a, f"/polices/{p['id']}/pieces"), headers=en_tant_que(a[qui]), data={"nature": nature, **champs},
                       files={"fichier": PDF})


def appel(client, a, p, **autres):
    r = client.post(url(a, f"/polices/{p['id']}/appels"), headers=en_tant_que(a["conseiller"]), json={
        "reference": f"AP-{autres.get('premiere', False)}-{AUJOURD_HUI}", "montant": 5_000_000,
        "echeance": (AUJOURD_HUI + timedelta(days=30)).isoformat(), "banque": "SGC", "titulaire": "Assureur SA",
        "iban": IBAN, **autres})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def mandate(client, azito):
    sous_mandat(client, azito)
    return azito


def enregistrer_compte(client, personnes, assureur, iban=IBAN):
    r = client.post(f"{V1}/assureurs/comptes", json=compte(assureur=assureur, iban=iban),
                    headers=en_tant_que(personnes["admin"]))
    assert r.status_code == 201, r.text


def test_de_la_police_recue_a_la_mise_en_vigueur(client, mandate, personnes):
    a, nom = mandate, f"Assureur Vigueur {AUJOURD_HUI:%Y%m%d}"
    enregistrer_compte(client, personnes, nom)
    p = police(client, a, nom)
    assert p["statut"]["code"] == "retenue"
    # Signer exige la police reçue ; l'entreprise ne dépose pas la police, le conseiller si.
    assert client.post(url(a, f"/polices/{p['id']}/signature"), headers=en_tant_que(a["drh"]),
                       json={"signee_le": AUJOURD_HUI.isoformat()}).json()["code"] == "police_non_recue"
    assert deposer(client, a, "drh", p, "police").status_code == 403
    assert deposer(client, a, "conseiller", p, "police").status_code == 201
    client.put(url(a, f"/polices/{p['id']}/numero"), headers=en_tant_que(a["conseiller"]), json={"numero_police": "IFC-2026-001"})
    r = client.post(url(a, f"/polices/{p['id']}/signature"), headers=en_tant_que(a["drh"]), json={"signee_le": AUJOURD_HUI.isoformat()})
    assert r.status_code == 200 and r.json()["statut"]["code"] == "signee" and r.json()["numero_police"] == "IFC-2026-001"
    # La première prime : appelée, virée, encaissée sur quittance.
    ap = appel(client, a, p, premiere=True)
    assert ap["controle"] == "conforme" and ap["etat"] == "a_payer" and not ap["ne_pas_payer"]
    v = client.post(url(a, f"/appels/{ap['id']}/virement"), headers=en_tant_que(a["drh"]),
                    json={"vire_le": AUJOURD_HUI.isoformat(), "montant": 4_900_000, "reference": "VIR-778"})
    assert v.status_code == 200 and v.json()["etat"] == "declare" and v.json()["virement"]["ecart"] == -100_000
    assert client.post(url(a, f"/appels/{ap['id']}/encaissement"), headers=en_tant_que(a["conseiller"]),
                       json={"encaisse_le": AUJOURD_HUI.isoformat()}).json()["code"] == "quittance_requise"
    assert deposer(client, a, "conseiller", p, "quittance", appel_id=ap["id"]).status_code == 201
    r = client.post(url(a, f"/appels/{ap['id']}/encaissement"), headers=en_tant_que(a["conseiller"]),
                    json={"encaisse_le": AUJOURD_HUI.isoformat()})
    assert r.json()["etat"] == "encaisse"
    [lue] = [x for x in client.get(url(a, "/placement"), headers=en_tant_que(a["drh"])).json()["polices"] if x["id"] == p["id"]]
    assert lue["statut"]["code"] == "en_vigueur" and all(e["fait"] for e in lue["statut"]["etapes"])


def test_un_compte_different_du_registre_se_leve_par_un_contre_appel(client, mandate, personnes):
    a, nom = mandate, f"Assureur Fraude {AUJOURD_HUI:%Y%m%d}"
    enregistrer_compte(client, personnes, nom)
    p = police(client, a, nom)
    ap = appel(client, a, p, iban="CM21 99999 00000 0000000000 01")
    assert ap["controle"] == "modifie" and ap["ne_pas_payer"] is True
    # Les alertes : grave pour le conseiller.
    alertes = client.get(f"{V1}/organisations/{a['org']}/alertes", headers=en_tant_que(a["conseiller"])).json()
    assert any(x["code"] == "coordonnees_a_confirmer" and x["niveau"] == "grave" for x in alertes)
    # L'entreprise ne lève pas l'écart ; un encaissement ne se confirme pas avant le contre-appel.
    assert client.post(url(a, f"/appels/{ap['id']}/contre-appel"), headers=en_tant_que(a["drh"]),
                       json={"aupres": "x", "telephone": "1", "le": AUJOURD_HUI.isoformat()}).status_code == 403
    deposer(client, a, "conseiller", p, "quittance", appel_id=ap["id"])
    assert client.post(url(a, f"/appels/{ap['id']}/encaissement"), headers=en_tant_que(a["conseiller"]),
                       json={"encaisse_le": AUJOURD_HUI.isoformat()}).json()["code"] == "contre_appel_requis"
    r = client.post(url(a, f"/appels/{ap['id']}/contre-appel"), headers=en_tant_que(a["conseiller"]),
                    json={"aupres": "M. Kamga, comptabilité", "telephone": "+237 233 42 00 00", "le": AUJOURD_HUI.isoformat()})
    assert r.status_code == 200 and r.json()["ne_pas_payer"] is False and r.json()["contre_appel"]["aupres"].startswith("M. Kamga")
    assert client.post(url(a, f"/appels/{ap['id']}/contre-appel"), headers=en_tant_que(a["conseiller"]),
                       json={"aupres": "x y", "telephone": "123456", "le": AUJOURD_HUI.isoformat()}).json()["code"] == "contre_appel_fait"


def test_un_assureur_absent_du_registre_et_une_prime_en_retard(client, mandate):
    a = mandate
    p = police(client, a, f"Assureur Inconnu {AUJOURD_HUI:%Y%m%d%H%M}")
    ap = appel(client, a, p, echeance=(AUJOURD_HUI - timedelta(days=3)).isoformat())
    assert ap["controle"] == "non_enregistre" and ap["etat"] == "en_retard"
    alertes = client.get(f"{V1}/organisations/{a['org']}/alertes", headers=en_tant_que(a["drh"])).json()
    assert any(x["code"] == "prime_en_retard" and x["lien"] == "placement" for x in alertes)


def test_l_avis_ne_porte_ni_coordonnees_ni_montant(client, bases, mandate):
    from tests.test_avis import recus
    a = mandate
    p = police(client, a, "Assureur Avis")
    appel(client, a, p)
    [corps] = [x for x in recus(client, bases, a["drh"]) if "appel de prime" in x]
    assert "CM21" not in corps and "5 000 000" not in corps and "5000000" not in corps and "/placement" in corps


def test_depuis_l_offre_choisie_et_une_seule_fois(client, cahier):  # noqa: F811
    r = repondre(client, cahier)
    client.post(u(cahier, "/choix"), json={"reponse_id": r.json()["id"]}, headers=en_tant_que(cahier["drh"]))
    t = client.get(url(cahier, "/placement"), headers=en_tant_que(cahier["conseiller"])).json()
    [offre] = t["offres_a_placer"]
    p = police(client, cahier, None, choix_id=offre["id"])
    assert p["assureur"] == "Assureur A"
    assert client.get(url(cahier, "/placement"), headers=en_tant_que(cahier["conseiller"])).json()["offres_a_placer"] == []
    r = client.post(url(cahier, "/polices"), headers=en_tant_que(cahier["conseiller"]), json={
        "choix_id": offre["id"], "date_effet": AUJOURD_HUI.isoformat(), "periodicite": "annuelle"})
    assert r.json()["code"] == "police_existante"


def test_le_releve_se_rapproche_des_primes_et_de_l_etude(client, mandate):
    a = mandate
    p = police(client, a, "Assureur Relevé")
    assert deposer(client, a, "conseiller", p, "releve").json()["code"] == "releve_incomplet"
    r = deposer(client, a, "conseiller", p, "releve", releve_le=AUJOURD_HUI.isoformat(), montant_fonds="12000000")
    assert r.status_code == 201, r.text
    [lue] = [x for x in client.get(url(a, "/placement"), headers=en_tant_que(a["drh"])).json()["polices"] if x["id"] == p["id"]]
    [releve] = lue["releves"]["releves"]
    assert releve["montant_fonds"] == 12_000_000 and releve["primes_encaissees"] == 0


def test_sans_mandat_rien_ne_se_cree(client, azito):
    r = client.post(url(azito, "/polices"), headers=en_tant_que(azito["conseiller"]), json={
        "assureur": "X Assurances", "date_effet": AUJOURD_HUI.isoformat(), "periodicite": "annuelle"})
    assert r.json()["code"] == "mandat_requis"
