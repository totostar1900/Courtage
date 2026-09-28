"""Les anomalies s'enregistrent en français et s'affichent dans la langue de l'écran."""
import io
import re
from datetime import datetime
from pathlib import Path

import openpyxl
from sqlalchemy import text

from courtage import fichier as _fichier  # noqa: F401 — inscrit les traductions
from courtage import langue
from tests.outils import V1, deposer, en_tant_que, etude, fichier_azito

EN = {"X-Langue": "en"}


def _fichier_date_illisible() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Matricule", "Date de naissance", "Date d'embauche", "Salaire brut annuel"])
    ws.append(["A1", "31/13/1980", datetime(2005, 3, 1), 6_000_000])
    ws.append(["A2", datetime(1975, 6, 15), datetime(2001, 9, 1), 7_200_000])
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


def _anomalie(anomalies, code):
    return next(a for a in anomalies if a["code"] == code)


def test_l_anomalie_d_un_fichier_se_lit_en_anglais_et_reste_francaise_en_base(client, azito, bases):
    f = deposer(client, azito["org"], azito["drh"], _fichier_date_illisible())
    assert _anomalie(f["anomalies"], "date_illisible")["message"].startswith("Date illisible")

    url = f"{V1}/organisations/{azito['org']}/fichiers"
    en = next(x for x in client.get(url, headers={**en_tant_que(azito["drh"]), **EN}).json() if x["id"] == f["id"])
    fr = next(x for x in client.get(url, headers=en_tant_que(azito["drh"])).json() if x["id"] == f["id"])
    assert _anomalie(en["anomalies"], "date_illisible")["message"] == \
        "Unreadable date: “31/13/1980” (expected dd/mm/yyyy)."
    assert _anomalie(fr["anomalies"], "date_illisible")["message"] == \
        "Date illisible : « 31/13/1980 » (attendu jj/mm/aaaa)."

    with bases[0].begin() as c:
        stockees = c.execute(text("SELECT anomalies FROM fichiers_personnel WHERE id = :i"), {"i": f["id"]}).scalar_one()
    assert _anomalie(stockees, "date_illisible")["message"].startswith("Date illisible")


def test_une_etude_creee_en_anglais_garde_des_resultats_francais(client, azito, bases):
    f = deposer(client, azito["org"], azito["drh"], fichier_azito(doublon=True))
    a = {**azito, "fichier": f["id"]}
    en = client.post(f"{V1}/organisations/{a['org']}/etudes", headers={**en_tant_que(a["drh"]), **EN},
                     json={"fichier_id": f["id"], "date_evaluation": "2019-12-31", "convention_code": "CI_CCI",
                           "fonds_disponible": 0})
    assert en.status_code == 201, en.text
    fr = etude(client, a, fonds_disponible=0)
    assert fr.status_code == 201, fr.text
    en, fr = en.json(), fr.json()

    assert re.fullmatch(r"Staff number \S+ appears more than once \(rows .+\)\.",
                        _anomalie(en["anomalies"], "matricule_double")["message"])
    assert "présent plusieurs fois" in _anomalie(fr["anomalies"], "matricule_double")["message"]
    relue = client.get(f"{V1}/organisations/{a['org']}/etudes/{en['id']}", headers=en_tant_que(a["drh"])).json()
    assert relue["anomalies"] == fr["anomalies"]

    # Ce que l'empreinte scellera : identique, quelle que soit la langue de l'écran qui a créé l'étude.
    with bases[0].begin() as c:
        stockees = dict(c.execute(text("SELECT id::text, resultats->'anomalies' FROM etudes WHERE id IN (:a, :b)"),
                                  {"a": en["id"], "b": fr["id"]}).all())
    assert stockees[en["id"]] == stockees[fr["id"]]
    assert "présent plusieurs fois" in _anomalie(stockees[en["id"]], "matricule_double")["message"]


def _en_anglais(code, message):
    jeton = langue.definir("en")
    try:
        return langue.traduire(code, message)
    finally:
        langue._langue.reset(jeton)


def test_chaque_code_d_anomalie_a_sa_traduction():
    racine = Path(_fichier.__file__).parent
    sources = [*racine.glob("*.py"), racine.parent / "services" / "etudes.py", racine.parent / "services" / "experience.py"]
    codes = set()
    for source in sources:
        texte = source.read_text(encoding="utf-8")
        codes |= set(re.findall(r'Anomalie\(\s*"(?:bloquant|avertissement)",\s*"(\w+)"', texte))
        codes |= set(re.findall(r'_bloquer\(\s*lecture,\s*ligne,\s*"(\w+)"', texte))
    assert len(codes) >= 24   # la lecture des sources a bien trouvé les codes
    assert not codes - set(langue.TRADUCTIONS), codes - set(langue.TRADUCTIONS)


def test_les_messages_calcules_se_traduisent():
    assert _en_anglais("au_dela_de_la_retraite",
                       "62,4 ans, au-delà de l'âge de départ (60 ans) : son IFC est due, pas future.") == \
        "Aged 62.4, beyond the retirement age (60): the IFC is due now, not in the future."
    assert _en_anglais("champ_manquant", "Date d'embauche manquant(e).") == "Hire date missing."
    assert _en_anglais("colonnes_introuvables", "Colonne introuvable : motif. Colonnes attendues : matricule, "
                       "date d'embauche, date de départ, motif, salaire de référence.") == \
        "Column not found: reason. Expected columns: staff number, hire date, departure date, reason, reference salary."
    assert _en_anglais("non_conformite", "Catégorie « Cadres » : le régime donne moins que Convention X pour "
                       "3 à 5 ans, 9 ans d'ancienneté. Les salariés gardent droit au plancher.") == \
        "Category “Cadres”: the plan gives less than Convention X for 3 to 5 years, 9 years of service. " \
        "Employees keep their right to the floor."
    assert _en_anglais("inconnu", "Tel quel.") == "Tel quel."
