"""P2 : une prestation est un départ sans identité ; le dû est recalculé, le versé déclaré, l'historique repris."""
import io
from datetime import datetime

import openpyxl
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from courtage.db import contexte
from tests.outils import V1, en_tant_que, etude, sous_contrat
from tests.test_regime import CADRES, adopter, categorie, regime

@pytest.fixture(autouse=True)
def _sous_contrat(request):
    """Les départs s'ouvrent sous un contrat en vigueur (activation « departs ») : AZITO y est, depuis 2021."""
    if "azito" in request.fixturenames:
        sous_contrat(request.getfixturevalue("client"), request.getfixturevalue("azito"))


# CI_CCI : 30 % d'un mois par an jusqu'à 5 ans, 35 % jusqu'à 10, 40 % au-delà.
# 20 ans : 5 × 0,30 + 5 × 0,35 + 10 × 0,40 = 7,25 mois.
DEPART = {"matricule": "A-017", "motif": "retraite", "date_embauche": "2000-01-01", "date_depart": "2020-01-01",
          "salaire_mensuel_reference": 500_000, "convention_code": "CI_CCI"}


def url(a, suite=""):
    return f"{V1}/organisations/{a['org']}/prestations{suite}"


def enregistrer(client, a, qui="drh", **champs):
    return client.post(url(a), json={**DEPART, **champs}, headers=en_tant_que(a[qui]))


def actives(client, a):
    return client.get(url(a), headers=en_tant_que(a["drh"])).json()["prestations"]


# --- Le dû, recalculé ------------------------------------------------------------------

def test_le_du_est_recalcule_selon_la_convention(client, azito, bases):
    r = enregistrer(client, azito, verse=3_625_000)
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["du"] == 3_625_000                     # 7,25 mois × 500 000
    assert p["calcul"]["mois"] == 7.25 and p["calcul"]["anciennete"] == 20.0
    assert p["calcul"]["source"] == {"type": "convention", "convention_code": "CI_CCI",
                                     "libelle": "Convention collective interprofessionnelle de Côte d'Ivoire"}
    assert p["constats"] == [] and p["service"] == "comparaison"
    with bases[0].connect() as c:
        assert "prestation.enregistree" in set(c.execute(text("SELECT action FROM journal WHERE organisation_id = :o"),
                                                         {"o": azito["org"]}).scalars())


def test_sans_convention_la_derniere_etude_la_donne(client, azito):
    corps = {k: v for k, v in DEPART.items() if k != "convention_code"}
    r = client.post(url(azito), json=corps, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 422 and r.json()["code"] == "convention_requise"
    assert etude(client, azito).status_code == 201
    r = client.post(url(azito), json=corps, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 201 and r.json()["calcul"]["source"]["convention_code"] == "CI_CCI"


def test_le_regime_en_vigueur_au_depart_l_emporte(client, azito):
    v = regime(client, azito, [categorie("Cadre", CADRES), categorie("*", CADRES)], en_vigueur_du="2015-03-12")
    assert adopter(client, azito, v["id"]).status_code == 200
    apres = enregistrer(client, azito, categorie="Cadre").json()
    # CADRES : 5 × 0,60 + 5 × 0,70 + 10 × 0,80 = 14,5 mois.
    assert apres["du"] == 7_250_000 and apres["calcul"]["source"]["type"] == "regime"
    assert apres["calcul"]["source"]["regime_version_id"] == v["id"]
    avant = enregistrer(client, azito, matricule="A-018", date_depart="2014-12-31", date_embauche="1994-12-31").json()
    assert avant["calcul"]["source"]["type"] == "convention" and avant["du"] == 3_625_000


def test_un_depart_hors_retraite_ne_doit_pas_d_ifc(client, azito):
    p = enregistrer(client, azito, motif="demission").json()
    assert p["du"] == 0 and p["calcul"]["mois"] == 0 and "retraite" in p["calcul"]["raison"]


# --- Versé, fonds, constats ------------------------------------------------------------

def test_verse_sous_le_du_est_signale_au_dela_est_permis(client, azito):
    sous = enregistrer(client, azito, verse=3_000_000).json()
    assert [(c["niveau"], c["code"]) for c in sous["constats"]] == [("avertit", "verse_sous_le_du")]
    dessus = enregistrer(client, azito, matricule="A-018", verse=4_000_000).json()
    assert [(c["niveau"], c["code"]) for c in dessus["constats"]] == [("informe", "verse_au_dela_du_du")]


def test_le_fonds_ne_paie_pas_plus_que_demande(client, azito):
    p = enregistrer(client, azito, verse=3_625_000, part_fonds_demandee=3_000_000, part_fonds_payee=3_200_000,
                    payee_le="2020-02-15").json()
    assert "fonds_paye_au_dela_demande" in {c["code"] for c in p["constats"]}


def test_un_paiement_a_une_date(client, azito):
    r = enregistrer(client, azito, part_fonds_payee=1_000_000)
    assert r.status_code == 422 and r.json()["code"] == "date_paiement_requise"


def test_un_matricule_encore_present_dans_un_fichier_posterieur(client, azito):
    # Le fichier d'AZITO est arrêté au 31/12/2019 et contient le matricule « 3 ».
    p = enregistrer(client, azito, matricule="3", date_embauche="1998-01-01", date_depart="2018-06-30").json()
    assert "encore_present" in {c["code"] for c in p["constats"]}


def test_le_service_est_celui_du_jour_du_depart(client, azito):
    client.post(f"{V1}/organisations/{azito['org']}/contrats", headers=en_tant_que(azito["conseiller"]), json={
        "en_vigueur_du": "2019-06-01", "service": "courtage", "assureur": "A", "mandat_reference": "Mandat"})
    assert enregistrer(client, azito).json()["service"] == "courtage"
    assert enregistrer(client, azito, matricule="A-018", date_depart="2019-01-31",
                       date_embauche="1999-01-31").json()["service"] == "comparaison"


# --- Aucune identité, des droits -------------------------------------------------------

def test_aucune_identite_n_est_acceptee(client, azito):
    for champ in ("nom", "prenom", "telephone", "piece_identite"):
        r = enregistrer(client, azito, **{champ: "x"})
        assert r.status_code == 422, champ


def test_qui_enregistre(client, azito, personnes, bases):
    assert enregistrer(client, azito, qui="conseiller").status_code == 201
    with bases[0].begin() as c:
        lecteur = c.execute(text("INSERT INTO utilisateurs (email, nom_affiche) VALUES ('l@x.cm', 'L') RETURNING id")).scalar_one()
        c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'lecteur_client')"),
                  {"u": lecteur, "o": azito["org"]})
    r = client.post(url(azito), json=DEPART, headers=en_tant_que(lecteur))
    assert r.status_code == 403
    assert client.get(url(azito), headers=en_tant_que(lecteur)).status_code == 200


# --- Une écriture ----------------------------------------------------------------------

def test_une_correction_remplace_sans_effacer(client, azito):
    p = enregistrer(client, azito).json()
    r = client.post(url(azito, f"/{p['id']}/correction"), headers=en_tant_que(azito["drh"]),
                    json={**DEPART, "salaire_mensuel_reference": 600_000, "motif_correction": "Salaire mal saisi"})
    assert r.status_code == 201, r.text
    nouvelle = r.json()
    assert nouvelle["remplace_id"] == p["id"] and nouvelle["du"] == 4_350_000
    assert [x["id"] for x in actives(client, azito)] == [nouvelle["id"]]
    encore = client.post(url(azito, f"/{p['id']}/correction"), headers=en_tant_que(azito["drh"]),
                         json={**DEPART, "motif_correction": "Encore"})
    assert encore.status_code == 409 and encore.json()["code"] == "deja_corrigee"


def test_une_annulation_retire_la_ligne(client, azito):
    p = enregistrer(client, azito).json()
    r = client.post(url(azito, f"/{p['id']}/annulation"), headers=en_tant_que(azito["drh"]),
                    json={"motif_correction": "Doublon"})
    assert r.status_code == 201, r.text
    assert actives(client, azito) == []
    sans_motif = client.post(url(azito, f"/{enregistrer(client, azito).json()['id']}/annulation"),
                             headers=en_tant_que(azito["drh"]), json={"motif_correction": " "})
    assert sans_motif.status_code == 422


def test_une_prestation_ne_se_modifie_pas(client, azito, bases):
    enregistrer(client, azito)
    with pytest.raises(ProgrammingError, match="permission"):
        with bases[1].begin() as c:
            contexte(c, azito["org"])
            c.execute(text("UPDATE prestations SET du = 0"))
    # L'effacement n'est permis que pour une inscription jamais confirmée ; un dossier confirmé le refuse.
    with pytest.raises(DBAPIError, match="effacement_refuse"):
        with bases[1].begin() as c:
            contexte(c, azito["org"])
            c.execute(text("DELETE FROM prestations"))


def test_les_totaux(client, azito):
    enregistrer(client, azito, verse=3_625_000, part_fonds_payee=3_000_000, payee_le="2020-03-01")
    enregistrer(client, azito, matricule="A-018", motif="demission")
    t = client.get(url(azito), headers=en_tant_que(azito["drh"])).json()["totaux"]
    assert t == {"nombre": 2, "retraites": 1, "autres_departs": 1, "du": 3_625_000, "verse": 3_625_000,
                 "part_fonds_payee": 3_000_000}


# --- L'historique, par tableur -----------------------------------------------------------

def tableur(lignes, entete=("Matricule", "Nom", "Date d'embauche", "Date de départ", "Motif",
                            "Salaire mensuel de référence", "Montant versé", "Payé par le fonds", "Date de paiement")):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Départs 2015-2019"])
    ws.append(list(entete))
    for l in lignes:
        ws.append(list(l))
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


LIGNES = [
    ("B-001", "Nom Un", datetime(2000, 1, 1), datetime(2020, 1, 1), "Retraite", 500_000, 3_625_000, 3_625_000, datetime(2020, 2, 1)),
    ("B-002", "Nom Deux", datetime(2010, 5, 1), datetime(2016, 5, 1), "Démission", 300_000, None, None, None),
    ("B-003", "Nom Trois", datetime(1990, 1, 1), datetime(2018, 1, 1), "retirement", 400_000, 3_000_000, None, None),
]


def importer(client, a, contenu, enregistrer_=False, qui="conseiller"):
    return client.post(url(a, "/import"), headers=en_tant_que(a[qui]),
                       files={"fichier": ("departs.xlsx", contenu)},
                       data={"convention_code": "CI_CCI", "enregistrer": "true" if enregistrer_ else "false"})


def test_l_apercu_d_un_import_n_enregistre_rien(client, azito):
    r = importer(client, azito, tableur(LIGNES))
    assert r.status_code == 200, r.text
    a = r.json()
    assert [l["matricule"] for l in a["lignes"]] == ["B-001", "B-002", "B-003"]
    assert [l["motif"] for l in a["lignes"]] == ["retraite", "demission", "retraite"]
    assert a["lignes"][0]["du"] == 3_625_000 and a["lignes"][1]["du"] == 0
    assert a["colonnes_ignorees"] == ["Nom"] and a["enregistrees"] == 0
    assert "Nom Un" not in r.text
    assert actives(client, azito) == []


def test_l_import_enregistre_soldees_sous_un_meme_lot(client, azito):
    r = importer(client, azito, tableur(LIGNES), enregistrer_=True)
    assert r.status_code == 201, r.text
    assert r.json()["enregistrees"] == 3
    ps = actives(client, azito)
    assert len(ps) == 3 and all(p["soldee"] and p["origine"] == "import" for p in ps)
    assert len({p["import_id"] for p in ps}) == 1


def test_une_ligne_bloquante_arrete_tout_l_import(client, azito):
    mauvaises = LIGNES + [("B-004", "X", "pas une date", datetime(2019, 1, 1), "Retraite", 1, None, None, None),
                          ("B-005", "Y", datetime(2010, 1, 1), datetime(2019, 1, 1), "Mutation", 1, None, None, None)]
    a = importer(client, azito, tableur(mauvaises)).json()
    assert {x["code"] for x in a["anomalies"] if x["niveau"] == "bloquant"} >= {"date_illisible", "motif_inconnu"}
    r = importer(client, azito, tableur(mauvaises), enregistrer_=True)
    assert r.status_code == 422 and r.json()["code"] == "import_bloque"
    assert actives(client, azito) == []


def test_un_tableur_sans_colonne_de_depart(client, azito):
    a = importer(client, azito, tableur([("B-1", datetime(2000, 1, 1), 1)], entete=("Matricule", "Date d'embauche", "Salaire"))).json()
    assert "colonnes_introuvables" in {x["code"] for x in a["anomalies"]}


def test_l_apercu_calcule_sans_enregistrer(client, azito):
    r = client.post(url(azito, "/apercu"), json={**DEPART, "verse": 3_000_000}, headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200, r.text
    assert r.json()["du"] == 3_625_000 and r.json()["constats"][0]["code"] == "verse_sous_le_du"
    assert actives(client, azito) == []
