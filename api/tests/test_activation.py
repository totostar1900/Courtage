"""Ce que permet une inscription en attente : tout le travail ; rien de ce qui sort ; rien des assureurs."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from courtage.services import activation
from tests.outils import V1, en_tant_que, etude
from tests.test_fiche import fiche


def mettre_en_attente(bases, org):
    with bases[0].begin() as c:
        c.execute(text("UPDATE organisations SET activation = 'en_attente', rccm = :r, rccm_normalise = :r, "
                       "activation_demandee_le = now() WHERE id = :o"), {"o": org, "r": "RC" + str(org).replace("-", "")[:12].upper()})


def u(a, suite=""):
    return f"{V1}/organisations/{a['org']}{suite}"


def test_le_travail_reste_ouvert(client, azito, bases):
    mettre_en_attente(bases, azito["org"])
    h = en_tant_que(azito["drh"])
    e = etude(client, azito)
    assert e.status_code == 201, e.text                                        # une étude se calcule
    lu = client.get(u(azito, "/activation"), headers=h).json()
    assert lu["etat"] == "en_attente" and lu["capacites"]["rapport_scelle"] is False and "echeance" in lu
    assert client.post(u(azito, "/mandats"), json={"besoins": ["placement"]}, headers=h).status_code == 201


@pytest.mark.parametrize("appel", [
    lambda c, a, e: c.get(u(a, f"/etudes/{e}/export"), headers=en_tant_que(a["drh"])),
    lambda c, a, e: c.post(u(a, f"/etudes/{e}/emission"), headers=en_tant_que(a["conseiller"])),
    lambda c, a, e: c.post(u(a, "/membres"), json={"telephone": "+237650000009", "nom_affiche": "X", "role": "lecteur_client"},
                           headers=en_tant_que(a["drh"])),
    lambda c, a, e: c.get(f"{V1}/catalogue/regimes", headers=en_tant_que(a["drh"])),
])
def test_ce_qui_sort_attend_la_confirmation(client, azito, bases, appel):
    e = etude(client, azito).json()["id"]
    mettre_en_attente(bases, azito["org"])
    r = appel(client, azito, e)
    assert r.status_code == 403 and r.json()["code"] == "inscription_non_confirmee", r.text


def test_le_cahier_attend_le_mandat(client, azito):
    e = etude(client, azito).json()
    client.post(u(azito, f"/etudes/{e['id']}/emission"), headers=en_tant_que(azito["conseiller"]))
    r = fiche(client, azito, e["id"], mandat=False)
    assert r.status_code == 409 and r.json()["code"] == "mandat_requis", r.text


def test_deux_jours_ouvres():
    vendredi = datetime(2026, 10, 2, 16, tzinfo=timezone.utc)
    assert activation.echeance(vendredi).isoformat() == "2026-10-06"          # lundi, mardi
    assert activation.normaliser_rccm(" rc/dla-2024 b 1 ") == "RCDLA2024B1"
