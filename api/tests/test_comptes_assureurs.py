"""Le registre des comptes bancaires des assureurs : le courtier seul, chaque ligne avec son contre-appel, un
changement remplace sans effacer."""
from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from courtage.services import comptes_assureurs
from tests.outils import V1, en_tant_que

URL = f"{V1}/assureurs/comptes"


def compte(**autres):
    return {"assureur": "Allianz Cameroun Assurances", "banque": "Société Générale Cameroun",
            "titulaire": "Allianz Cameroun Assurances SA", "iban": "CM21 10003 00100 0512345678 91",
            "bic": "sgcmcmcx", "verifie_aupres": "Mme Ngo, direction financière", "verifie_telephone": "+237 233 42 00 00",
            "verifie_le": date.today().isoformat(), **autres}


def test_le_courtier_seul_enregistre_et_chaque_ligne_porte_son_contre_appel(client, personnes):
    admin = en_tant_que(personnes["admin"])
    assert client.post(URL, json=compte(), headers=en_tant_que(personnes["conseiller"])).status_code == 403
    assert client.get(URL, headers=en_tant_que(personnes["drh"])).status_code == 403
    assert client.post(URL, json=compte(verifie_aupres=" ", verifie_telephone="12"), headers=admin).json()["code"] == \
        "contre_appel_requis"
    futur = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(URL, json=compte(verifie_le=futur), headers=admin).json()["code"] == "date_future"
    assert client.post(URL, json=compte(iban="CM21 ???? ????"), headers=admin).json()["code"] == "iban_invalide"
    r = client.post(URL, json=compte(assureur=f"Assureur {date.today()} A"), headers=admin)
    assert r.status_code == 201, r.text
    assert r.json()["iban"] == "CM2110003001000512345678 91".replace(" ", "") and r.json()["bic"] == "SGCMCMCX"


def test_un_changement_remplace_sans_effacer(client, personnes):
    admin = en_tant_que(personnes["admin"])
    nom = f"Saham Assurance {date.today():%Y%m%d%H}"
    premier = client.post(URL, json=compte(assureur=nom), headers=admin).json()
    second = client.post(URL, json=compte(assureur=nom.upper(), iban="CM2199999000000000000001",
                                          verifie_aupres="M. Eto'o, trésorerie"), headers=admin).json()
    assert second["remplace_id"] == premier["id"]                    # même assureur, écrit autrement
    [ligne] = [a for a in client.get(URL, headers=admin).json()["assureurs"]
               if comptes_assureurs.cle(a["assureur"]) == comptes_assureurs.cle(nom)]
    assert ligne["en_vigueur"]["id"] == second["id"]
    assert [h["id"] for h in ligne["historique"]] == [premier["id"]]


def test_le_registre_ne_se_modifie_pas_en_base(bases, client, personnes):
    c = client.post(URL, json=compte(assureur="Assureur immuable"), headers=en_tant_que(personnes["admin"])).json()
    with pytest.raises(DBAPIError, match="permission denied"):
        with bases[1].begin() as conn:
            conn.execute(text("UPDATE comptes_assureurs SET iban = 'XX' WHERE id = :i"), {"i": c["id"]})


def test_la_cle_d_un_assureur_ignore_accents_et_ponctuation():
    assert comptes_assureurs.cle("Société d'Assurances — SAAR") == comptes_assureurs.cle("SOCIETE D ASSURANCES SAAR")
