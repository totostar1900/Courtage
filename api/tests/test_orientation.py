"""P4 : en comparaison, la plateforme oriente vers l'assureur — sans rien recueillir — et reçoit ce qu'il a payé."""
import pymupdf
from sqlalchemy import text

from tests.outils import V1, en_tant_que
from tests.test_dossiers import COURTAGE, IDENTITE
from tests.test_prestations import DEPART

COMPARAISON = {"en_vigueur_du": "2019-01-01", "service": "comparaison", "assureur": "Assureur B",
               "numero_police": "IFC-B-12", "date_effet_police": "2019-01-01"}


def u(a, suite=""):
    return f"{V1}/organisations/{a['org']}{suite}"


def depart(client, a, contrat=COMPARAISON, **champs):
    if contrat:
        assert client.post(u(a, "/contrats"), json=contrat, headers=en_tant_que(a["conseiller"])).status_code == 201
    r = client.post(u(a, "/prestations"), json={**DEPART, "verse": 3_625_000, **champs}, headers=en_tant_que(a["drh"]))
    assert r.status_code == 201, r.text
    return r.json()


def orientation(client, a, p, qui="drh"):
    return client.get(u(a, f"/prestations/{p['id']}/orientation"), headers=en_tant_que(a[qui]))


def test_en_comparaison_l_orientation_dit_a_qui_quoi_et_combien(client, azito):
    p = depart(client, azito)
    o = orientation(client, azito, p).json()
    assert o["service"] == "comparaison" and o["qui_s_en_occupe"] == "entreprise"
    assert (o["assureur"], o["numero_police"]) == ("Assureur B", "IFC-B-12")
    assert o["du"] == 3_625_000 and o["montant_a_demander"] == 3_625_000
    natures = [x["nature"] for x in o["pieces"]]
    assert {"courrier_demande", "certificat_travail", "attestation_depart", "piece_identite", "coordonnees_paiement",
            "fiche_de_calcul"} <= set(natures)
    assert not {"nom", "beneficiaire", "identite"} & set(o)


def test_la_demande_suggeree_est_le_plus_petit_du_du_et_du_verse(client, azito):
    p = depart(client, azito, verse=4_000_000)
    assert orientation(client, azito, p).json()["montant_a_demander"] == 3_625_000
    p = depart(client, azito, contrat=None, matricule="A-2", verse=3_000_000)
    assert orientation(client, azito, p).json()["montant_a_demander"] == 3_000_000


def test_sans_assureur_connu_on_le_dit(client, azito):
    p = depart(client, azito, contrat=None)
    o = orientation(client, azito, p).json()
    assert o["assureur"] is None and "votre conseiller" in o["message"]


def test_en_courtage_l_orientation_renvoie_au_dossier(client, azito):
    p = depart(client, azito, contrat=COURTAGE)
    o = orientation(client, azito, p).json()
    assert o["service"] == "courtage" and o["qui_s_en_occupe"] == "plateforme"


def test_hors_retraite_rien_a_demander(client, azito):
    p = depart(client, azito, motif="demission")
    r = orientation(client, azito, p)
    assert r.status_code == 409 and r.json()["code"] == "pas_d_ifc"


# --- La fiche de calcul scellée ----------------------------------------------------------

def test_la_fiche_de_calcul_est_scellee_sans_identite(client, azito, bases):
    p = depart(client, azito)
    r = client.get(u(azito, f"/prestations/{p['id']}/fiche-de-calcul"), headers=en_tant_que(azito["drh"]))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    with pymupdf.open(stream=r.content, filetype="pdf") as doc:
        texte = "".join(page.get_text() for page in doc)
    assert "3 625 000" in texte and "7,25" in texte and "Assureur B" in texte
    numero = r.headers["x-numero-document"]
    assert numero.startswith("FC-") and numero in texte.replace("\n", "")
    publique = client.get(f"{V1}/verifier/{numero}").json()
    assert publique["authentique"] and publique["nature"] == "fiche_de_calcul"
    assert "A-017" not in str(publique)
    # La même ligne rend la même fiche : un seul sceau.
    encore = client.get(u(azito, f"/prestations/{p['id']}/fiche-de-calcul"), headers=en_tant_que(azito["drh"]))
    assert encore.content == r.content
    with bases[0].connect() as c:
        assert c.execute(text("SELECT count(*) FROM documents WHERE prestation_id = :p"), {"p": p["id"]}).scalar() == 1


# --- Déclarer ce que l'assureur a payé ----------------------------------------------------

def test_l_entreprise_declare_le_paiement_de_son_assureur(client, azito):
    p = depart(client, azito)
    r = client.post(u(azito, f"/prestations/{p['id']}/paiement"), headers=en_tant_que(azito["drh"]),
                    json={"part_fonds_demandee": 3_625_000, "part_fonds_payee": 3_500_000, "payee_le": "2020-03-01"})
    assert r.status_code == 201, r.text
    nouvelle = r.json()
    assert (nouvelle["part_fonds_payee"], nouvelle["payee_le"], nouvelle["soldee"]) == (3_500_000, "2020-03-01", True)
    assert nouvelle["remplace_id"] == p["id"] and "déclaré par l'entreprise" in nouvelle["motif_correction"]
    assert "fonds_paye_au_dela_demande" not in {c["code"] for c in nouvelle["constats"]}


def test_un_paiement_ne_precede_pas_le_depart(client, azito):
    p = depart(client, azito)
    r = client.post(u(azito, f"/prestations/{p['id']}/paiement"), headers=en_tant_que(azito["drh"]),
                    json={"part_fonds_payee": 1, "payee_le": "2019-12-01"})
    assert r.status_code == 422 and r.json()["code"] == "paiement_avant_depart"


def test_un_dossier_de_courtage_porte_son_paiement_lui_meme(client, azito):
    p = depart(client, azito, contrat=COURTAGE)
    client.post(u(azito, "/dossiers"), headers=en_tant_que(azito["drh"]),
                json={"prestation_id": p["id"], "montant_demande": 3_625_000, "beneficiaire": IDENTITE})
    r = client.post(u(azito, f"/prestations/{p['id']}/paiement"), headers=en_tant_que(azito["drh"]),
                    json={"part_fonds_payee": 1, "payee_le": "2020-03-01"})
    assert r.status_code == 409 and r.json()["code"] == "dossier_ouvert"


def test_le_lecteur_ne_declare_pas(client, azito, bases):
    p = depart(client, azito)
    with bases[0].begin() as c:
        lecteur = c.execute(text("INSERT INTO utilisateurs (email, nom_affiche) VALUES ('lo@x.ci', 'L') RETURNING id")).scalar_one()
        c.execute(text("INSERT INTO adhesions (utilisateur_id, organisation_id, role) VALUES (:u, :o, 'lecteur_client')"),
                  {"u": lecteur, "o": azito["org"]})
    assert client.get(u(azito, f"/prestations/{p['id']}/orientation"), headers=en_tant_que(lecteur)).status_code == 200
    r = client.post(u(azito, f"/prestations/{p['id']}/paiement"), headers=en_tant_que(lecteur),
                    json={"part_fonds_payee": 1, "payee_le": "2020-03-01"})
    assert r.status_code == 403
