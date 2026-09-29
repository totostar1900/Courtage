"""Le mandat de courtage : demandé par le client, proposé par le conseiller, signé par l'administrateur."""
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.outils import V1, en_tant_que


def url(a, suite=""):
    return f"{V1}/organisations/{a['org']}/mandats{suite}"


def proposition(**autres):
    return {"perimetre": ["analyse", "consultation", "placement"], "date_effet": (date.today() + timedelta(days=10)).isoformat(),
            "duree_mois": 12, "preavis_mois": 3, "exclusif": True, **autres}


def demander(client, a):
    r = client.post(url(a), json={"besoins": ["placement"], "message": "Nous voulons assurer nos IFC."},
                    headers=en_tant_que(a["drh"]))
    assert r.status_code == 201, r.text
    return r.json()


def test_de_la_demande_a_la_signature(client, azito):
    m = demander(client, azito)
    assert m["statut"] == "demande" and m["besoins"][0]["code"] == "placement"
    assert client.post(url(azito), json={"besoins": ["placement"]}, headers=en_tant_que(azito["drh"])).json()["code"] == "demande_en_cours"
    # Seul le conseiller propose.
    assert client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(), headers=en_tant_que(azito["drh"])).status_code == 403
    r = client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(conditions="Revue annuelle du régime incluse."),
                   headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 200, r.text
    p = r.json()["proposition"]
    titres = [x["titre"] for x in p["texte"]["articles"]]
    assert {"Objet", "Mission du Courtier", "Devoir de conseil et d'information", "Rémunération",
            "Durée et résiliation", "Conditions particulières"} <= set(titres)
    [remuneration] = [x for x in p["texte"]["articles"] if x["titre"] == "Rémunération"]
    assert "gratuit pour le Client" in remuneration["paragraphes"][0]
    assert "exclusivement par la commission versée par l'assureur" in remuneration["paragraphes"][1]
    # Signer exige d'accepter, un nom, et le texte lu : pas un autre.
    corps = {"nom": "Awa Kouassi", "fonction": "DRH", "empreinte": p["empreinte"], "accepte": True,
             "qualite": "representant_legal"}
    h = en_tant_que(azito["drh"])
    assert client.post(url(azito, f"/{m['id']}/signature"), json={**corps, "accepte": False}, headers=h).json()["code"] == "acceptation_requise"
    assert client.post(url(azito, f"/{m['id']}/signature"), json={**corps, "empreinte": "0" * 64}, headers=h).json()["code"] == "texte_modifie"
    assert client.post(url(azito, f"/{m['id']}/signature"), json=corps, headers=en_tant_que(azito["conseiller"])).status_code == 403
    r = client.post(url(azito, f"/{m['id']}/signature"), json=corps, headers=h)
    assert r.status_code == 200, r.text
    s = r.json()["signature"]
    assert s["numero"].startswith("MC-") and s["nom"] == "Awa Kouassi"
    assert s["qualite"] == "representant_legal" and s["delegation"] is None
    # Le contrat « courtage » prend effet à la date du mandat, le mandat pour référence.
    k = client.get(f"{V1}/organisations/{azito['org']}/contrats", headers=h).json()
    [courtage] = [c for c in k["historique"] if c["service"] == "courtage"]
    assert courtage["mandat_reference"] == s["numero"] and courtage["en_vigueur_du"] == proposition()["date_effet"]
    assert courtage["raison_de_garder"]
    # Le PDF scellé se vérifie.
    pdf = client.get(url(azito, f"/{m['id']}/pdf"), headers=h)
    assert pdf.headers["content-type"] == "application/pdf"
    assert client.get(f"{V1}/verifier/{s['numero']}").json()["authentique"] is True
    # Signé, il ne se reprend plus.
    assert client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(), headers=en_tant_que(azito["conseiller"])).json()["code"] == "mandat_clos"


def test_refuser_puis_redemander(client, azito):
    m = demander(client, azito)
    assert client.post(url(azito, f"/{m['id']}/refus"), json={}, headers=en_tant_que(azito["drh"])).json()["code"] == "mandat_clos"
    client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(), headers=en_tant_que(azito["conseiller"]))
    r = client.post(url(azito, f"/{m['id']}/refus"), json={"motif": "Pas cette année."}, headers=en_tant_que(azito["drh"]))
    assert r.json()["statut"] == "refuse" and r.json()["motif"] == "Pas cette année."
    assert demander(client, azito)["statut"] == "demande"


def test_une_proposition_datee_du_passe_est_refusee(client, azito):
    m = demander(client, azito)
    r = client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(date_effet="2020-01-01"),
                   headers=en_tant_que(azito["conseiller"]))
    assert r.json()["code"] == "date_passee"


def test_un_mandat_signe_ne_se_modifie_pas(client, azito, bases):
    m = demander(client, azito)
    p = client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(), headers=en_tant_que(azito["conseiller"])).json()["proposition"]
    client.post(url(azito, f"/{m['id']}/signature"), json={"nom": "Awa Kouassi", "empreinte": p["empreinte"], "accepte": True, "qualite": "representant_legal"},
                headers=en_tant_que(azito["drh"]))
    with pytest.raises(DBAPIError, match="mandat_immuable"):
        with bases[1].begin() as c:
            c.execute(text("SELECT set_config('app.organisation_id', :o, true)"), {"o": azito["org"]})
            c.execute(text("UPDATE mandats_courtage SET duree_mois = 60 WHERE id = :m"), {"m": m["id"]})


def signer(client, a, m, **corps):
    return client.post(url(a, f"/{m['id']}/signature"), headers=en_tant_que(a["drh"]),
                       json={"nom": "Awa Kouassi", "fonction": "DRH", "empreinte": m["proposition"]["empreinte"],
                             "accepte": True, **corps})


def test_le_signataire_dit_sa_qualite_et_le_delegataire_depose_sa_delegation(client, azito):
    m = demander(client, azito)
    m = client.put(url(azito, f"/{m['id']}/proposition"), json=proposition(), headers=en_tant_que(azito["conseiller"])).json()
    assert signer(client, azito, m).json()["code"] == "qualite_requise"
    assert signer(client, azito, m, qualite="delegataire").json()["code"] == "delegation_requise"
    # Un RCCM n'est pas une délégation.
    rccm = client.post(f"{V1}/organisations/{azito['org']}/justificatifs", headers=en_tant_que(azito["drh"]),
                       files={"fichier": ("rccm.pdf", b"%PDF-1.4 rccm", "application/pdf")}).json()
    assert signer(client, azito, m, qualite="delegataire", delegation_id=rccm["id"]).json()["code"] == "delegation_requise"
    # Seul l'administrateur, qui signe, dépose une délégation.
    r = client.post(f"{V1}/organisations/{azito['org']}/justificatifs", headers=en_tant_que(azito["drh"]),
                    data={"nature": "delegation"},
                    files={"fichier": ("pouvoir.pdf", b"%PDF-1.4 pouvoir", "application/pdf")})
    assert r.status_code == 201 and r.json()["nature"] == "delegation"
    r = signer(client, azito, m, qualite="delegataire", delegation_id=r.json()["id"])
    assert r.status_code == 200, r.text
    s = r.json()["signature"]
    assert s["qualite"] == "delegataire" and s["delegation"]["nom_fichier"] == "pouvoir.pdf"
    # Le conseiller ouvre la délégation ; un étranger au dossier, non.
    doc = client.get(f"{V1}/organisations/{azito['org']}/justificatifs/{s['delegation']['id']}",
                     headers=en_tant_que(azito["conseiller"]))
    assert doc.status_code == 200 and doc.content == b"%PDF-1.4 pouvoir"
    assert client.get(f"{V1}/organisations/{azito['org']}/justificatifs/{s['delegation']['id']}",
                      headers=en_tant_que(azito["etranger"])).status_code == 403


def test_la_base_refuse_un_delegataire_sans_delegation(bases, client, azito):
    m = demander(client, azito)
    with pytest.raises(DBAPIError, match="delegation_du_delegataire"):
        with bases[0].begin() as c:
            c.execute(text("UPDATE mandats_courtage SET signataire_qualite = 'delegataire' WHERE id = :i"), {"i": m["id"]})
