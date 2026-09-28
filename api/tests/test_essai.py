"""L'essai sans compte : un calcul à l'écran, rien de gardé, rien d'imprimable côté serveur."""
import json

from sqlalchemy import text

from tests.outils import V1, fichier_azito

PARAMS = {"pays": "CM", "date_evaluation": "2025-12-31", "fonds_disponible": 10_000_000, "convention_code": "CM_COMMERCE"}


def essayer(client, contenu=None, **p):
    return client.post(f"{V1}/essai/etude", data={"parametres": json.dumps({**PARAMS, **p})},
                       files={"fichier": ("personnel.xlsx", contenu or fichier_azito())})


def lignes_en_base(proprio) -> dict:
    with proprio.connect() as c:
        tables = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).scalars().all()
        return {t: c.execute(text(f'SELECT count(*) FROM "{t}"')).scalar() for t in tables}


def test_l_essai_calcule_sans_compte_et_ne_garde_rien(client, bases):
    avant = lignes_en_base(bases[0])
    r = essayer(client)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["effectif"] == 23 and e["totaux"]["dette"] > 0 and e["non_scelle"] is True
    assert e["echeancier"] and e["sensibilite"]["dette"] > e["totaux"]["dette"]
    assert lignes_en_base(bases[0]) == avant                      # aucune ligne écrite, dans aucune table


def test_un_regime_saisi(client):
    bareme = {"forme": "tranches_cumulatives", "tranches": [{"jusqu_a": None, "mois_par_annee": 1.0}]}
    r = essayer(client, categories=[{"categorie": "*", "convention_code": "CM_COMMERCE", "bareme": bareme}])
    base = essayer(client).json()["totaux"]["dette"]
    assert r.status_code == 200, r.text
    assert r.json()["totaux"]["dette"] > base                      # un mois par année, plus que la convention


def test_les_limites_de_l_essai(client):
    assert essayer(client, pays="CI", convention_code="CI_CCI").json()["code"] == "hors_cemac"
    assert essayer(client, convention_code="CI_CCI").json()["code"] == "convention_autre_pays"
    lignes = "matricule;date de naissance;date d'embauche;salaire annuel\n" + "".join(
        f"M{i};1980-01-01;2010-01-01;6000000\n" for i in range(301))
    r = client.post(f"{V1}/essai/etude", data={"parametres": json.dumps(PARAMS)},
                    files={"fichier": ("personnel.csv", lignes.encode())})
    assert r.json()["code"] == "essai_trop_grand" and r.json()["details"]["effectif"] == 301
