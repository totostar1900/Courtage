"""Référentiel : format des barèmes, vigueur dans le temps, règle d'émission."""
from datetime import date

import pytest
from pydantic import ValidationError

from courtage.referentiel import (
    Convention,
    Referentiel,
    motifs_de_refus,
    referentiel_courant,
)


@pytest.fixture(scope="module")
def ref() -> Referentiel:
    return referentiel_courant()


# --- Chargement ---------------------------------------------------------------

def test_le_referentiel_courant_se_charge_avec_sa_version(ref):
    assert ref.version
    assert {"CI_CCI", "MG_APB", "CM_COMMERCE", "CM_BANQUES"} <= {c.code for c in ref.conventions}
    assert "TV_CIMA_F" in ref.tables


def test_chaque_convention_cite_une_source(ref):
    for c in ref.conventions:
        assert c.sources, c.code
        assert all(s.titre for s in c.sources)


# --- Vigueur dans le temps ----------------------------------------------------

def test_le_commerce_camerounais_change_de_bareme_au_16_janvier_2024(ref):
    avant = ref.convention("CM_COMMERCE", date(2023, 12, 31))
    apres = ref.convention("CM_COMMERCE", date(2024, 12, 31))
    assert avant.en_vigueur_au == date(2024, 1, 15)
    assert apres.en_vigueur_du == date(2024, 1, 16)
    assert [t.mois_par_annee for t in avant.bareme.tranches] == [0.40, 0.45, 0.60, 0.65, 0.75]
    assert [t.mois_par_annee for t in apres.bareme.tranches] == [0.45, 0.50, 0.65, 0.75, 0.80]


def test_aucune_convention_en_vigueur_a_la_date(ref):
    with pytest.raises(LookupError):
        ref.convention("CM_BANQUES", date(2000, 1, 1))


def test_code_inconnu(ref):
    with pytest.raises(LookupError):
        ref.convention("XX_RIEN", date(2024, 1, 1))


def test_conventions_du_pays(ref):
    codes = {c.code for c in ref.conventions_du_pays("CM", date(2025, 12, 31))}
    assert codes == {"CM_COMMERCE", "CM_BANQUES"}


# --- Format -------------------------------------------------------------------

def _convention(**bareme) -> dict:
    return dict(
        pays="CM", code="CM_TEST", libelle="Test", statut="valide",
        sources=[{"titre": "Texte"}], verification="test",
        en_vigueur_du="2020-01-01", bareme=bareme,
    )


def test_refuse_des_tranches_desordonnees():
    with pytest.raises(ValidationError):
        Convention.model_validate(_convention(
            forme="tranches_cumulatives",
            tranches=[{"jusqu_a": 10, "mois_par_annee": 0.3}, {"jusqu_a": 5, "mois_par_annee": 0.4},
                      {"jusqu_a": None, "mois_par_annee": 0.5}],
        ))


def test_refuse_une_derniere_tranche_bornee():
    with pytest.raises(ValidationError):
        Convention.model_validate(_convention(
            forme="tranches_cumulatives", tranches=[{"jusqu_a": 5, "mois_par_annee": 0.3}],
        ))


def test_refuse_un_taux_absurde():
    with pytest.raises(ValidationError):
        Convention.model_validate(_convention(
            forme="tranches_cumulatives", tranches=[{"jusqu_a": None, "mois_par_annee": 30}],
        ))


def test_refuse_une_forme_inconnue():
    with pytest.raises(ValidationError):
        Convention.model_validate(_convention(forme="au_doigt_mouille"))


def test_refuse_une_vigueur_inversee():
    brut = _convention(forme="tranches_cumulatives", tranches=[{"jusqu_a": None, "mois_par_annee": 0.3}])
    brut["en_vigueur_au"] = "2019-01-01"
    with pytest.raises(ValidationError):
        Convention.model_validate(brut)


def test_refuse_deux_versions_qui_se_chevauchent(tmp_path):
    for i, (du, au) in enumerate([("2020-01-01", "2022-12-31"), ("2022-06-01", None)]):
        brut = _convention(forme="tranches_cumulatives", tranches=[{"jusqu_a": None, "mois_par_annee": 0.3}])
        brut.update(en_vigueur_du=du, en_vigueur_au=au)
        import json
        (tmp_path / f"convention_test_{i}.json").write_text(json.dumps(brut), "utf-8")
    with pytest.raises(ValueError, match="chevauch"):
        Referentiel.depuis_dossier(tmp_path, version="test")


# --- Règle d'émission ---------------------------------------------------------

def test_emission_permise_convention_du_pays_valide_et_en_vigueur(ref):
    c = ref.convention("CM_COMMERCE", date(2025, 12, 31))
    assert motifs_de_refus(c, pays_organisation="CM", date_evaluation=date(2025, 12, 31)) == []


def test_refus_convention_d_un_autre_pays(ref):
    """La leçon d'AZITO : le barème d'un pays dans l'étude d'un autre."""
    c = ref.convention("MG_APB", date(2019, 12, 31))
    assert "pays_different" in motifs_de_refus(c, pays_organisation="CI", date_evaluation=date(2019, 12, 31))


def test_refus_convention_a_valider():
    c = Convention.model_validate({**_convention(
        forme="tranches_cumulatives", tranches=[{"jusqu_a": None, "mois_par_annee": 0.3}]),
        "statut": "a_valider"})
    assert "convention_a_valider" in motifs_de_refus(c, pays_organisation="CM", date_evaluation=date(2025, 12, 31))


def test_refus_convention_hors_vigueur_a_la_date_d_evaluation(ref):
    ancienne = ref.convention("CM_COMMERCE", date(2023, 12, 31))
    assert "hors_vigueur" in motifs_de_refus(ancienne, pays_organisation="CM", date_evaluation=date(2024, 12, 31))


# --- Barème d'entreprise : jamais moins que la convention ---------------------

from courtage.actuariat.ifc import comparer_baremes  # noqa: E402
from courtage.referentiel import BaremeTranches  # noqa: E402


def _tranches(*taux):
    bornes = [5, 10, None][:len(taux)] if len(taux) == 3 else [None]
    return BaremeTranches(forme="tranches_cumulatives",
                          tranches=[{"jusqu_a": b, "mois_par_annee": t} for b, t in zip(bornes, taux)])


def test_un_bareme_plus_genereux_passe(ref):
    ci = ref.convention("CI_CCI", date(2019, 12, 31)).bareme
    assert comparer_baremes(_tranches(0.30, 0.40, 0.50), ci) == []


def test_un_bareme_moins_genereux_est_refuse_avec_les_anciennetes_en_cause(ref):
    ci = ref.convention("CI_CCI", date(2019, 12, 31)).bareme
    en_dessous = comparer_baremes(_tranches(0.35), ci)  # 35 % partout : rattrapé par les 40 % de la convention
    assert en_dessous[0] == 16  # 15 ans : 5,25 mois des deux côtés ; 16 ans : 5,60 contre 5,65
    assert en_dessous == list(range(16, 51))
