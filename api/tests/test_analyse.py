"""Analyse d'un régime : légalité, nature, pièges et coûts, en constats sourcés."""
from dataclasses import replace

import pytest

from courtage.actuariat.ifc import Regles
from courtage.analyse import Contexte, analyser
from courtage.referentiel import BaremeTranches, notes_juridiques
from tests.outils import V1, en_tant_que
from tests.test_ifc import CI, hypotheses, salaries
from tests.test_regime import AVARE, CADRES, CCI, adopter, categorie, regime, version


def tranches(*taux, bornes=(5, 10)):
    b = list(bornes)[: len(taux) - 1] + [None]
    return BaremeTranches(forme="tranches_cumulatives",
                          tranches=[{"jusqu_a": x, "mois_par_annee": t} for x, t in zip(b, taux)])


PLANCHER = Regles(bareme=CI.bareme)


def contexte(regles_texte, *, fondement="accord_entreprise", pays="CI", categories=None, precedent=None,
             avec_salaries=True):
    regles = {k: replace(v, plancher=PLANCHER) for k, v in regles_texte.items()}
    return Contexte(
        pays=pays, fondement=fondement,
        categories=categories or [{"categorie": k, "base_salaire": "dernier", "avec_primes": False,
                                   "evenements": ["retraite"]} for k in regles_texte],
        salaries=salaries() if avec_salaries else None, hypotheses=hypotheses(), convention=CI,
        regles=regles, regles_texte=regles_texte, regles_plancher={k: PLANCHER for k in regles_texte},
        regles_precedentes=precedent,
    )


def par_code(constats):
    return {c.code: c for c in constats}


# --- La base de notes ---------------------------------------------------------

def test_chaque_note_est_sourcee_et_a_valider():
    notes = notes_juridiques()
    assert {"provisionnement", "usage", "deductibilite_CI", "deductibilite_CM", "egalite_de_traitement",
            "abus_de_biens_sociaux"} <= set(notes)
    for n in notes.values():
        assert n.statut == "a_valider"        # aucun juriste n'a relu : décision du 2026-09-26
        assert n.texte and n.titre


# --- Nature -------------------------------------------------------------------

def test_tout_regime_est_a_provisionner():
    c = par_code(analyser(contexte({"*": Regles(bareme=CI.bareme)})))
    assert c["provisionnement"].niveau == "informe"
    assert c["provisionnement"].statut_contenu == "a_valider"
    assert c["provisionnement"].sources


def test_une_decision_de_la_direction_devient_un_usage():
    c = par_code(analyser(contexte({"*": Regles(bareme=CI.bareme)}, fondement="decision_direction")))
    assert c["usage"].niveau == "informe"
    assert "usage" not in par_code(analyser(contexte({"*": Regles(bareme=CI.bareme)})))


@pytest.mark.parametrize("pays", ["CI", "CM"])
def test_la_deductibilite_depend_du_pays(pays):
    c = par_code(analyser(contexte({"*": Regles(bareme=CI.bareme)}, pays=pays)))
    assert c[f"deductibilite_{pays}"].niveau == "informe"


def test_plusieurs_categories_appellent_des_criteres_objectifs():
    c = par_code(analyser(contexte({"Cadre": Regles(bareme=tranches(0.6, 0.7, 0.8)), "*": Regles(bareme=CI.bareme)})))
    assert c["egalite_de_traitement"].niveau == "informe"


def test_une_base_avec_primes_est_signalee():
    categories = [{"categorie": "*", "base_salaire": "dernier", "avec_primes": True, "evenements": ["retraite"]}]
    c = par_code(analyser(contexte({"*": Regles(bareme=CI.bareme)}, categories=categories)))
    assert c["base_avec_primes"].niveau == "avertit"


# --- Coûts --------------------------------------------------------------------

def test_le_cout_de_la_non_conformite():
    """Ce que l'entreprise sous-estime si elle se fie à son propre texte."""
    avare = Regles(bareme=tranches(0.10))
    c = par_code(analyser(contexte({"*": avare})))["cout_non_conformite"]
    assert c.niveau == "avertit"
    retenue = c.chiffres["dette_retenue"]
    assert retenue == pytest.approx(60_130_415, rel=1e-5)      # la dette conventionnelle : le plancher joue partout
    assert c.chiffres["dette_selon_le_texte"] < retenue
    assert c.chiffres["ecart"] == retenue - c.chiffres["dette_selon_le_texte"]


def test_la_dette_de_passe_creee_par_l_adoption():
    genereux = Regles(bareme=tranches(0.6, 0.7, 0.8))
    c = par_code(analyser(contexte({"*": genereux})))["dette_de_passe"]
    assert c.niveau == "informe"
    assert c.chiffres["reference"] == "convention"
    assert c.chiffres["supplement"] > 0


def test_la_dette_de_passe_face_a_la_version_precedente():
    precedent = {"*": Regles(bareme=tranches(0.5, 0.6, 0.7), plancher=PLANCHER)}
    c = par_code(analyser(contexte({"*": Regles(bareme=tranches(0.6, 0.7, 0.8))}, precedent=precedent)))["dette_de_passe"]
    assert c.chiffres["reference"] == "version_precedente"


def test_une_amelioration_reservee_aux_hauts_salaires():
    """Un régime qui ne relève que la catégorie où sont les plus hauts salaires."""
    sal = salaries()
    hauts = {s.matricule for s in sorted(sal, key=lambda s: -s.salaire_annuel)[:3]}
    sal = [replace(s, categorie="Direction" if s.matricule in hauts else "Personnel") for s in sal]
    regles = {"Direction": Regles(bareme=tranches(1.5, 1.5, 1.5)), "Personnel": Regles(bareme=CI.bareme)}
    ctx = replace(contexte(regles), salaries=sal)
    c = par_code(analyser(ctx))["concentration"]
    assert c.niveau == "avertit"
    assert c.chiffres["part_des_mieux_payes"] > 0.9


def test_une_amelioration_uniforme_n_est_pas_une_concentration():
    c = par_code(analyser(contexte({"*": Regles(bareme=tranches(0.45, 0.525, 0.60))})))
    assert c["concentration"].niveau == "informe"


def test_sans_fichier_pas_de_chiffres():
    codes = set(par_code(analyser(contexte({"*": Regles(bareme=tranches(0.10))}, avec_salaries=False))))
    assert not codes & {"cout_non_conformite", "dette_de_passe", "concentration"}


def test_les_constats_viennent_dans_l_ordre_bloque_avertit_informe():
    niveaux = [c.niveau for c in analyser(contexte({"*": Regles(bareme=tranches(0.10))}))]
    ordre = {"bloque": 0, "avertit": 1, "informe": 2}
    assert niveaux == sorted(niveaux, key=ordre.get)


# --- Par l'API ----------------------------------------------------------------

def analyse_api(client, a, version_id, **params):
    r = client.get(f"{V1}/organisations/{a['org']}/regimes/versions/{version_id}/analyse",
                   params=params, headers=en_tant_que(a["drh"]))
    assert r.status_code == 200, r.text
    return {c["code"]: c for c in r.json()["constats"]}


def test_analyse_d_un_regime_par_l_api(client, azito):
    v = regime(client, azito, [categorie("*", AVARE)])
    c = analyse_api(client, azito, v["id"])
    assert c["sous_le_plancher"]["niveau"] == "avertit"      # signalé, jamais bloquant : il s'adopte en le confirmant
    assert "provisionnement" in c and "cout_non_conformite" not in c       # sans fichier, pas de chiffres
    c = analyse_api(client, azito, v["id"], fichier_id=azito["fichier"], date_evaluation="2019-12-31")
    assert c["cout_non_conformite"]["chiffres"]["ecart"] > 0
    assert c["provisionnement"]["statut_contenu"] == "a_valider"


def test_la_dette_de_passe_se_mesure_a_la_version_en_vigueur_la_veille(client, azito):
    v1 = regime(client, azito, [categorie("*", CCI)])
    adopter(client, azito, v1["id"])
    v2 = version(client, azito, v1["regime_id"], [categorie("*", CADRES)], en_vigueur_du="2019-06-01")
    c = analyse_api(client, azito, v2["id"], fichier_id=azito["fichier"], date_evaluation="2019-12-31")
    assert c["dette_de_passe"]["chiffres"]["reference"] == "version_precedente"
