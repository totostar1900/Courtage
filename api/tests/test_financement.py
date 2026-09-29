"""Financement : cotisations, amortissement, projection du fonds sous plusieurs scénarios, offres comparées."""
import pytest

from courtage.financement import Engagement, Offre, Parametres, Scenario, projeter
from tests.outils import V1, en_tant_que, etude

SIMPLE = Engagement(annee_evaluation=2025, dette=100.0, charge=10.0, fonds_initial=0.0,
                    prestations={2027: 50.0})
SANS_FRAIS = Offre(nom="Sans frais", taux_garanti=0.0)
NUL = Scenario(nom="nul", rendement=0.0)


def une(engagement=SIMPLE, offre=SANS_FRAIS, scenario=NUL, **parametres):
    p = Parametres(**{"horizon": 3, "amortissement_annees": 1, "taux_actualisation": 0.0,
                      "croissance_salaires": 0.0, **parametres})
    return projeter(engagement, [offre], [scenario], p)["offres"][0]["scenarios"][0]


# --- La mécanique du fonds ----------------------------------------------------

def test_le_fonds_annee_par_annee():
    p = une()
    a1, a2, a3 = p["annees"]
    assert (a1["annee"], a1["cotisation"], a1["fonds_fin"]) == (2026, 110.0, 110.0)   # le déficit d'un coup + la charge
    assert (a2["cotisation"], a2["prestations"], a2["fonds_fin"]) == (10.0, 50.0, 70.0)
    assert a3["fonds_fin"] == 80.0
    assert p["annees_decouvert"] == []


def test_amortir_le_deficit_sur_plusieurs_annees():
    a = une(amortissement_annees=2)["annees"]
    assert [x["amortissement"] for x in a] == [50.0, 50.0, 0.0]


def test_frais_sur_cotisations_et_sur_encours():
    a1 = une(offre=Offre(nom="Frais", taux_garanti=0.0, frais_sur_cotisations=0.04))["annees"][0]
    assert a1["frais_cotisation"] == pytest.approx(4.4) and a1["fonds_fin"] == pytest.approx(105.6)
    a1 = une(offre=Offre(nom="Encours", taux_garanti=0.0, frais_sur_encours=0.01))["annees"][0]
    assert a1["frais_encours"] == pytest.approx(1.1) and a1["fonds_fin"] == pytest.approx(108.9)


@pytest.mark.parametrize("rendement,credite", [(0.06, 0.02 + 0.9 * 0.04), (0.01, 0.02)])
def test_taux_garanti_et_participation_aux_benefices(rendement, credite):
    offre = Offre(nom="PB", taux_garanti=0.02, participation_benefices=0.9)
    a1 = une(offre=offre, scenario=Scenario(nom="s", rendement=rendement))["annees"][0]
    assert a1["taux_credite"] == pytest.approx(credite)
    assert a1["interets"] == pytest.approx(110 * credite)


def test_un_fonds_trop_court_laisse_un_decouvert():
    """Le fonds ne paie que dans la limite de ce qu'il contient ; l'entreprise paie le reste."""
    engagement = Engagement(annee_evaluation=2025, dette=100.0, charge=0.0, fonds_initial=0.0,
                            prestations={2026: 30.0, 2027: 90.0})
    p = une(engagement=engagement, amortissement_annees=3)
    a1, a2, _ = p["annees"]
    assert a2["fonds_debut"] == pytest.approx(3.33333, rel=1e-4)
    assert a2["payees_par_le_fonds"] == pytest.approx(a2["fonds_debut"] + a2["cotisation"])
    assert a2["decouvert"] == pytest.approx(90 - a2["payees_par_le_fonds"])
    assert p["annees_decouvert"] == [2027]
    assert p["cout_total"] == pytest.approx(100 + a2["decouvert"])


def test_les_prestations_deja_echues_sont_payees_la_premiere_annee():
    engagement = Engagement(annee_evaluation=2025, dette=0.0, charge=0.0, fonds_initial=20.0,
                            prestations={2025: 20.0})
    assert une(engagement=engagement)["annees"][0]["prestations"] == 20.0


def test_le_fonds_restant_revient_a_l_entreprise():
    p = une(taux_actualisation=0.0)
    assert p["cout_net_actualise"] == pytest.approx(p["cout_total"] - p["annees"][-1]["fonds_fin"])


def test_la_couverture_des_departs_apres_l_horizon():
    engagement = Engagement(annee_evaluation=2025, dette=100.0, charge=0.0, fonds_initial=0.0,
                            prestations={2030: 200.0})
    p = une(engagement=engagement, horizon=3)
    assert p["prestations_restantes_actualisees"] == pytest.approx(200.0)      # taux 0
    assert p["couverture_des_departs_restants"] == pytest.approx(0.5)
    assert une(horizon=3)["couverture_des_departs_restants"] is None           # plus rien à payer après l'horizon


# --- Comparer -----------------------------------------------------------------

def test_l_offre_la_moins_chere_d_abord_dans_le_scenario_central():
    offres = [Offre(nom="Chère", taux_garanti=0.025, frais_sur_cotisations=0.05, frais_sur_encours=0.01),
              Offre(nom="Sobre", taux_garanti=0.025, frais_sur_cotisations=0.02),
              Offre(nom="Provision interne", taux_garanti=0.0, interne=True)]
    scenarios = [Scenario(nom="prudent", rendement=0.03), Scenario(nom="central", rendement=0.05)]
    r = projeter(SIMPLE, offres, scenarios, Parametres(horizon=10, amortissement_annees=1, taux_actualisation=0.035,
                                                       croissance_salaires=0.02, scenario_de_reference="central"))
    assert r["classement"][0] == "Sobre"
    assert r["classement"].index("Sobre") < r["classement"].index("Chère")
    [interne] = [o for o in r["offres"] if o["interne"]]
    assert interne["scenarios"][0]["annees"][0]["taux_credite"] == 0.0


def test_plan_d_amortissement():
    r = projeter(SIMPLE, [SANS_FRAIS], [NUL], Parametres(horizon=5, amortissement_annees=4, taux_actualisation=0.0,
                                                         croissance_salaires=0.0))
    assert r["plan_amortissement"] == {"deficit_initial": 100.0, "annees": 4, "annuite": 25.0}


@pytest.mark.parametrize("champs", [{"horizon": 0}, {"horizon": 41}, {"amortissement_annees": 12},
                                    {"taux_actualisation": 0.5}])
def test_parametres_refuses(champs):
    with pytest.raises(ValueError):
        Parametres(**{"horizon": 10, "amortissement_annees": 1, "taux_actualisation": 0.035,
                      "croissance_salaires": 0.02, **champs})


@pytest.mark.parametrize("champs", [{"frais_sur_cotisations": 0.5}, {"participation_benefices": 1.2},
                                    {"taux_garanti": -0.2}])
def test_offres_refusees(champs):
    with pytest.raises(ValueError):
        Offre(nom="x", **champs)


# --- Sur une étude, par l'API -------------------------------------------------

def financer(client, a, etude_id, **corps):
    return client.post(f"{V1}/organisations/{a['org']}/etudes/{etude_id}/financement",
                       json=corps, headers=en_tant_que(a["drh"]))


def test_financer_une_etude(client, azito):
    e = etude(client, azito).json()
    assert all("prestations_probables" in x for x in e["echeancier"])
    r = financer(client, azito, e["id"], horizon=10, amortissement_annees=3, offres=[
        {"nom": "Assureur A", "taux_garanti": 0.025, "participation_benefices": 0.85, "frais_sur_cotisations": 0.04},
        {"nom": "Assureur B", "taux_garanti": 0.02, "participation_benefices": 0.9, "frais_sur_encours": 0.005},
    ])
    assert r.status_code == 200, r.text
    r = r.json()
    assert [o["nom"] for o in r["offres"]] == ["Assureur A", "Assureur B", "Provision interne"]
    assert [s["scenario"] for s in r["offres"][0]["scenarios"]] == ["prudent", "central", "favorable"]
    assert len(r["offres"][0]["scenarios"][0]["annees"]) == 10
    deficit = max(e["totaux"]["dette"] - e["fonds_disponible"], 0)
    assert r["plan_amortissement"]["deficit_initial"] == deficit
    assert sorted(r["classement"]) == ["Assureur A", "Assureur B", "Provision interne"]


def test_scenarios_parametrables(client, azito):
    e = etude(client, azito).json()
    r = financer(client, azito, e["id"], horizon=5, offres=[], scenarios=[{"nom": "crise", "rendement": 0.0}]).json()
    [interne] = r["offres"]
    assert [s["scenario"] for s in interne["scenarios"]] == ["crise"]


def test_financement_refuse_avec_des_parametres_absurdes(client, azito):
    e = etude(client, azito).json()
    r = financer(client, azito, e["id"], horizon=0)
    assert r.status_code == 422


# --- Le rendement net : ce que l'offre rapporte au fonds, tous frais payés ------------------

def test_sans_frais_le_rendement_net_est_le_taux_servi():
    p = une(offre=Offre(nom="Pur", taux_garanti=0.03), scenario=Scenario(nom="s", rendement=0.03))
    assert p["taux_servi"] == pytest.approx(0.03)
    assert p["rendement_net"] == pytest.approx(0.03, abs=1e-7)


def test_les_frais_sur_encours_se_retranchent_du_taux():
    p = une(offre=Offre(nom="Encours", taux_garanti=0.03, frais_sur_encours=0.005), scenario=Scenario(nom="s", rendement=0.03))
    # (1 + 3 %) × (1 − 0,5 %) − 1 : un peu moins de 2,5 %.
    assert p["rendement_net"] == pytest.approx(1.03 * 0.995 - 1, abs=1e-7)


def test_les_frais_sur_cotisations_pesent_d_autant_plus_que_l_horizon_est_court():
    offre = Offre(nom="Entrée", taux_garanti=0.03, frais_sur_cotisations=0.03)
    court = une(offre=offre, scenario=Scenario(nom="s", rendement=0.03), horizon=3)["rendement_net"]
    long_ = une(offre=offre, scenario=Scenario(nom="s", rendement=0.03), horizon=20)["rendement_net"]
    assert court < long_ < 0.03


def test_les_offres_se_classent_par_rendement_net():
    s = [Scenario(nom="central", rendement=0.05)]
    parametres = Parametres(horizon=10, amortissement_annees=3)
    offres = [Offre(nom="Frais bas", taux_garanti=0.025, participation_benefices=0.85, frais_sur_cotisations=0.01),
              Offre(nom="Taux haut, frais lourds", taux_garanti=0.035, participation_benefices=0.5,
                    frais_sur_cotisations=0.05, frais_sur_encours=0.01)]
    r = projeter(SIMPLE, offres, s, parametres)
    rendements = {o["nom"]: o["scenarios"][0]["rendement_net"] for o in r["offres"]}
    assert r["classement_rendement"][0] == max(rendements, key=rendements.get)
    assert rendements["Frais bas"] > rendements["Taux haut, frais lourds"]


def test_sans_frais_rendement_net_et_taux_servi_sont_le_meme_nombre():
    """« Taux servi 4,63 % − frais 0,00 % = 4,62 % » : l'arrondi du calcul se voyait à l'écran."""
    p = une(offre=Offre(nom="PB", taux_garanti=0.025, participation_benefices=0.85), scenario=Scenario(nom="c", rendement=0.05))
    assert p["rendement_net"] == round(p["taux_servi"], 8)
