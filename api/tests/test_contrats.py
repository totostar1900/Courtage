"""P1 : le contrat suivi dit le service rendu — courtage (mandat) ou comparaison — à une date."""
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from courtage.db import contexte
from courtage.services import contrats
from tests.outils import V1, en_tant_que

COURTAGE = {"en_vigueur_du": "2026-01-01", "service": "courtage", "assureur": "Assureur A",
            "numero_police": "IFC-2026-0042", "date_effet_police": "2026-01-01",
            "mandat_reference": "Mandat de courtage du 15/12/2025"}


def url(a):
    return f"{V1}/organisations/{a['org']}/contrats"


def test_sans_contrat_le_client_est_en_comparaison(client, azito):
    r = client.get(url(azito), headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200
    assert r.json()["service"] == "comparaison" and r.json()["en_vigueur"] is None and r.json()["historique"] == []


def test_le_conseiller_enregistre_un_courtage(client, azito, bases):
    r = client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 201, r.text
    lu = client.get(url(azito), headers=en_tant_que(azito["drh"])).json()
    assert lu["service"] == "courtage"
    assert lu["en_vigueur"]["assureur"] == "Assureur A" and lu["en_vigueur"]["mandat_reference"].startswith("Mandat")
    with bases[0].connect() as c:
        assert "contrat.enregistre" in set(c.execute(text("SELECT action FROM journal WHERE organisation_id = :o"),
                                                     {"o": azito["org"]}).scalars())


def test_pas_de_courtage_sans_mandat(client, azito):
    r = client.post(url(azito), json={**COURTAGE, "mandat_reference": None}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 422 and r.json()["code"] == "mandat_requis"
    r = client.post(url(azito), json={**COURTAGE, "assureur": None}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 201, r.text                                  # l'assureur vient une fois le contrat placé


def test_une_comparaison_peut_n_avoir_aucun_assureur(client, azito):
    r = client.post(url(azito), json={"en_vigueur_du": "2026-01-01", "service": "comparaison"},
                    headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 201, r.text


def test_l_entreprise_ne_se_declare_pas_mandante_seule(client, azito):
    r = client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 403


def test_le_service_est_celui_en_vigueur_a_la_date(client, azito, bases):
    client.post(url(azito), json={"en_vigueur_du": "2024-01-01", "service": "comparaison", "assureur": "Assureur B"},
                headers=en_tant_que(azito["conseiller"]))
    client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["conseiller"]))
    with Session(bases[1]) as s, s.begin():
        contexte(s.connection(), azito["org"])
        assert contrats.service_a_la_date(s, date(2023, 12, 31)).service == "comparaison"
        avant = contrats.service_a_la_date(s, date(2025, 6, 30))
        assert (avant.service, avant.contrat.assureur) == ("comparaison", "Assureur B")
        assert contrats.service_a_la_date(s, date(2026, 1, 1)).service == "courtage"


def test_deux_contrats_le_meme_jour(client, azito):
    client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["conseiller"]))
    r = client.post(url(azito), json={**COURTAGE, "service": "comparaison"}, headers=en_tant_que(azito["conseiller"]))
    assert r.status_code == 409 and r.json()["code"] == "contrat_deja_enregistre"


def test_un_contrat_ne_se_modifie_pas(client, azito, bases):
    client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["conseiller"]))
    with pytest.raises(ProgrammingError, match="permission"):
        with bases[1].begin() as c:
            contexte(c, azito["org"])
            c.execute(text("UPDATE contrats SET service = 'comparaison'"))


def test_un_autre_client_ne_voit_pas_le_contrat(client, azito, bases):
    client.post(url(azito), json=COURTAGE, headers=en_tant_que(azito["conseiller"]))
    import uuid
    with bases[1].begin() as c:
        contexte(c, uuid.uuid4())
        assert c.execute(text("SELECT count(*) FROM contrats")).scalar() == 0
