"""Les modèles types de régime : calculés depuis la convention, conformes par construction."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from courtage.actuariat.ifc import mois_d_ifc
from courtage.api import creer_app
from courtage.modeles import modeles_du_pays
from courtage.referentiel import BaremePaliers, BaremeTranches, referentiel_courant
from tests.outils import V1

JOUR = date(2026, 9, 26)


def _bareme(b: dict):
    return (BaremeTranches if b["forme"] == "tranches_cumulatives" else BaremePaliers).model_validate(b)


def test_quatre_modeles_par_convention_camerounaise_en_vigueur():
    ref = referentiel_courant()
    modeles = modeles_du_pays(ref, "CM", JOUR)
    en_vigueur = {c.code for c in ref.conventions_du_pays("CM", JOUR)}
    assert {m["convention"]["code"] for m in modeles} == en_vigueur
    assert len(modeles) == 4 * len(en_vigueur)
    assert {m["modele"] for m in modeles} == {"minimum", "plus_25", "cadres", "simple"}


@pytest.mark.parametrize("pays", ["CM"])
def test_aucun_modele_ne_passe_sous_la_convention(pays):
    ref = referentiel_courant()
    for m in modeles_du_pays(ref, pays, JOUR):
        convention = ref.convention(m["convention"]["code"], JOUR).bareme
        for c in m["version"]["categories"]:
            b = _bareme(c["bareme"])
            assert c["convention_code"] == m["convention"]["code"]
            for n in range(1, 46):
                assert mois_d_ifc(b, n) >= mois_d_ifc(convention, n) - 1e-9, (m["code"], c["categorie"], n)


def test_chaque_modele_fait_ce_qu_il_dit():
    ref = referentiel_courant()
    par_code = {m["code"]: m for m in modeles_du_pays(ref, "CM", JOUR)}
    code = "CM_COMMERCE"
    convention = ref.convention(code, JOUR).bareme
    minimum = _bareme(par_code[f"{code}:minimum"]["version"]["categories"][0]["bareme"])
    assert all(mois_d_ifc(minimum, n) == mois_d_ifc(convention, n) for n in range(1, 46))
    plus = _bareme(par_code[f"{code}:plus_25"]["version"]["categories"][0]["bareme"])
    assert mois_d_ifc(plus, 20) == pytest.approx(1.25 * mois_d_ifc(convention, 20), abs=0.2)
    cadres = {c["categorie"]: c for c in par_code[f"{code}:cadres"]["version"]["categories"]}
    assert set(cadres) == {"Cadre", "*"}
    assert mois_d_ifc(_bareme(cadres["Cadre"]["bareme"]), 20) > mois_d_ifc(_bareme(cadres["*"]["bareme"]), 20)
    [tranche] = par_code[f"{code}:simple"]["version"]["categories"][0]["bareme"]["tranches"]
    assert tranche["jusqu_a"] is None and round(tranche["mois_par_annee"] / 0.05, 9) % 1 == 0


def test_un_modele_est_une_version_proposee_a_relire():
    [m, *_] = modeles_du_pays(referentiel_courant(), "CM", JOUR)
    v = m["version"]
    assert v["en_vigueur_du"] is None and v["fondement"] == "accord_entreprise"
    assert v["document_reference"].startswith("Modèle type de la plateforme")
    assert m["illustration"][0]["anciennete"] == 5 and "minimum" in m["illustration"][0]


def test_la_route_est_publique_et_dit_les_pays_sans_convention(bases):
    client = TestClient(creer_app(moteur=bases[1], authentification="session"))
    cm = client.get(f"{V1}/referentiel/modeles", params={"pays": "CM"})
    assert cm.status_code == 200 and cm.json()["pays_libelle"] == "Cameroun" and cm.json()["modeles"]
    ga = client.get(f"{V1}/referentiel/modeles", params={"pays": "GA"}).json()
    assert ga["modeles"] == [] and ga["pays_libelle"] == "Gabon"
    assert client.get(f"{V1}/referentiel/modeles", params={"pays": "FR"}).status_code == 422
