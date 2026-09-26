"""Fonctions d'appui partagées par les tests de l'API."""
import io
import json
from datetime import datetime
from pathlib import Path

import openpyxl

AZITO = json.loads((Path(__file__).parent / "fixtures" / "azito_2019.json").read_text())
V1 = "/api/v1"


def fichier_azito(doublon: bool = False, categories: dict[int, str] | None = None) -> bytes:
    """Le personnel d'AZITO tel qu'une DRH l'enverrait. `categories` : rang → catégorie
    (colonne « Catégorie » ; les rangs absents sont des « Employé »)."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["AZITO — état du personnel au 31/12/2019"])
    ws.append([])
    entete = ["Matricule", "Nom et prénoms", "Date de naissance", "Date d'embauche", "Salaire brut annuel"]
    ws.append(entete + (["Catégorie"] if categories is not None else []))
    for i, s in enumerate(AZITO["salaries"]):
        ligne = [s["matricule"], "Nom Prénom", datetime.fromisoformat(s["naissance"]),
                 datetime.fromisoformat(s["embauche"]), s["salaire_annuel"]]
        ws.append(ligne + ([categories.get(i, "Employé")] if categories is not None else []))
    if doublon:
        s = AZITO["salaries"][0]
        ws.append([s["matricule"], "Autre", datetime.fromisoformat(s["naissance"]),
                   datetime.fromisoformat(s["embauche"]), s["salaire_annuel"]])
    tampon = io.BytesIO()
    wb.save(tampon)
    return tampon.getvalue()


def en_tant_que(utilisateur_id):
    return {"X-Utilisateur": str(utilisateur_id)}


def deposer(client, org, qui, contenu, date_donnees="2019-12-31"):
    r = client.post(f"{V1}/organisations/{org}/fichiers", headers=en_tant_que(qui),
                    files={"fichier": ("azito.xlsx", contenu)}, data={"date_donnees": date_donnees})
    assert r.status_code == 201, r.text
    return r.json()


def etude(client, a, qui="drh", **champs):
    corps = {"fichier_id": a["fichier"], "date_evaluation": "2019-12-31", "convention_code": "CI_CCI",
             "fonds_disponible": AZITO["fonds_disponible"], **champs}
    return client.post(f"{V1}/organisations/{a['org']}/etudes", json=corps, headers=en_tant_que(a[qui]))


def codes(anomalies, niveau=None):
    return {x["code"] for x in anomalies if niveau is None or x["niveau"] == niveau}
