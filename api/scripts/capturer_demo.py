"""Enregistre les réponses de la VRAIE API sur une entreprise FICTIVE, pour la démonstration statique.

    python scripts/capturer_demo.py <url propriétaire d'une base JETABLE> <dossier de sortie>

La base est remise à zéro (schéma public détruit), migrée, puis remplie par
l'API elle-même : « Société Démo SA », Cameroun, 40 salariés inventés (tirage
fixe), un accord plus favorable pour les cadres, une étude émise, un brouillon,
un cahier des charges. Aucune donnée réelle : le cas AZITO n'est PAS utilisé.

Sortie : `donnees.json` (réponses par « MÉTHODE chemin ») et `documents.json`
(les PDF émis, rendus en images de pages).
"""
import base64
import json
import sys
from pathlib import Path


import pymupdf
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from courtage.api import creer_app
from courtage.db.migrations import migrer
from courtage.demo import societe_demo

V1 = "/api/v1"
MOT_DE_PASSE = "demo-statique"


def _pages(pdf: bytes) -> list[str]:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return ["data:image/jpeg;base64," + base64.b64encode(p.get_pixmap(dpi=90).tobytes("jpeg", 80)).decode()
                for p in doc]


def main(url: str, sortie: Path) -> None:
    proprio = create_engine(url)
    with proprio.begin() as c:
        c.execute(text("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"))
        c.execute(text(f"""DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'courtage_app') THEN
              CREATE ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE}';
            ELSE ALTER ROLE courtage_app LOGIN PASSWORD '{MOT_DE_PASSE}'; END IF; END $$;"""))
    migrer(url)
    app = create_engine(make_url(url).set(username="courtage_app", password=MOT_DE_PASSE))
    client = TestClient(creer_app(moteur=app, authentification="entete_dev", url_publique="https://demo.courtage"))

    ids = {}
    with proprio.begin() as c:
        for cle, nom, admin in (("admin", "Plateforme (démo)", True),
                                ("conseiller", "Awa Nkoulou, actuaire conseil", False),
                                ("drh", "Direction RH, Société Démo", False)):
            ids[cle] = str(c.execute(text("INSERT INTO utilisateurs (email, nom_affiche, admin_plateforme) "
                                          "VALUES (:e, :n, :a) RETURNING id"),
                                     {"e": f"{cle}@demo.courtage", "n": nom, "a": admin}).scalar_one())
    h = lambda qui: {"X-Utilisateur": ids[qui]}  # noqa: E731

    def ok(r):
        assert r.status_code < 300, r.text
        return r.json() if r.content and r.headers.get("content-type", "").startswith("application/json") else r

    cree = societe_demo(client, h)
    org, fichier, version, projet = cree["org"], cree["fichier"], cree["version"], cree["projet"]
    dossier, etude, brouillon, fiche = cree["dossier"], cree["etude"], cree["brouillon"], cree["fiche"]

    reponses: dict[str, object] = {}

    def capter(chemin: str, qui="drh", methode="GET", corps=None, cle=None):
        r = client.request(methode, f"{V1}{chemin}", headers=h(qui), json=corps)
        assert r.status_code < 300, (chemin, r.text)
        reponses[cle or f"{methode} {chemin}"] = r.json()

    capter("/referentiel/conventions")
    capter("/referentiel/modeles?pays=CM")
    capter("/referentiel/hypotheses")
    capter("/catalogue/regimes")
    capter("/alertes")
    capter("/dev/utilisateurs")
    reponses["GET /dev/utilisateurs"] = [u for u in reponses["GET /dev/utilisateurs"] if not u["admin_plateforme"]]
    for qui in ("drh", "conseiller"):
        capter("/moi", qui=qui, cle=f"GET /moi@{ids[qui]}")
    base = f"/organisations/{org}"
    for chemin in ("/fichiers", "/regimes", "/regimes/partages", "/alertes", "/cycle", "/regimes/menage", "/nettoyage", "/etudes", "/fiches", "/equipe", "/mandats", "/contrats", "/prestations", "/dossiers", f"/dossiers/{dossier['id']}",
                   f"/etudes/{etude['id']}", f"/etudes/{brouillon['id']}", f"/fiches/{fiche['id']}", f"/fiches/{fiche['id']}/reponses"):
        capter(base + chemin)
    for v in (version["id"], projet["id"]):
        capter(f"{base}/regimes/versions/{v}/analyse")
        capter(f"{base}/regimes/versions/{v}/analyse?fichier_id={fichier['id']}")
    capter(f"{base}/simulations", methode="POST", cle=f"POST {base}/simulations", corps={
        "fichier_id": fichier["id"], "date_evaluation": "2025-12-31", "convention_code": "CM_COMMERCE",
        "fonds_disponible": 45_000_000, "variantes": [
            {"nom": "Accord IFC Société Démo, version 1", "regime_version_id": version["id"]},
            {"nom": "Accord IFC Société Démo, version 2", "regime_version_id": projet["id"]}]})
    # La référence du calcul de financement, pour vérifier la version TypeScript.
    capter(f"{base}/etudes/{etude['id']}/financement", methode="POST", cle="REFERENCE financement", corps={
        "horizon": 10, "amortissement_annees": 3, "offres": [
            {"nom": "Assureur A", "taux_garanti": 0.025, "participation_benefices": 0.85, "frais_sur_cotisations": 0.04},
            {"nom": "Assureur B", "taux_garanti": 0.02, "participation_benefices": 0.9, "frais_sur_cotisations": 0.02,
             "frais_sur_encours": 0.005}]})

    # L'orientation (comparaison) et la fiche de calcul scellée de chaque départ en retraite d'avant le mandat.
    fiches_de_calcul = []
    for p in reponses[f"GET {base}/prestations"]["prestations"]:
        if p["motif"] == "retraite" and p["service"] == "comparaison":
            capter(f"{base}/prestations/{p['id']}/orientation")
            fiches_de_calcul.append(f"{base}/prestations/{p['id']}/fiche-de-calcul")
    # L'extraction assistée, par le moteur à règles (aucun appel externe) sur un accord FICTIF de la Société Démo.
    accord = ("ACCORD D'ENTREPRISE — INDEMNITÉ DE DÉPART À LA RETRAITE\nSociété Démo SA, Douala, Cameroun\n"
              "Article 9. Le salarié qui part à la retraite perçoit une indemnité calculée sur la moyenne mensuelle "
              "des douze derniers mois de salaire :\n- 50 % d'un mois de salaire pour chacune des 5 premières années ;\n"
              "- 60 % de la 6e à la 10e année ;\n- 75 % de la 11e à la 20e année ;\n- 90 % au-delà de la 20e année.\n"
              "Le présent accord entre en vigueur le 1er juillet 2026.\n")
    capter("/extraction/mode")
    r = client.post(f"{V1}{base}/regimes/extraction", headers=h("drh"),
                    files={"fichier": ("accord-ifc-2026.txt", accord.encode("utf-8"))})
    assert r.status_code == 201, r.text
    reponses[f"POST {base}/regimes/extraction"] = r.json()

    documents = {}
    rapport = reponses[f"GET {base}/etudes/{etude['id']}"]["rapport"]["numero"]
    for numero, chemin in ((rapport, f"{base}/etudes/{etude['id']}/rapport"),
                           (fiche["numero"], f"{base}/fiches/{fiche['id']}/document"),
                           (reponses[f"GET {base}/dossiers/{dossier['id']}"]["numero"],
                            f"{base}/dossiers/{dossier['id']}/document")):
        capter(f"/verifier/{numero}")
        pdf = client.get(f"{V1}{chemin}", headers=h("drh")).content
        documents[chemin] = _pages(pdf)
    for chemin in fiches_de_calcul:
        r = client.get(f"{V1}{chemin}", headers=h("drh"))
        documents[chemin] = _pages(r.content)
        capter(f"/verifier/{r.headers['x-numero-document']}")

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "donnees.json").write_text(json.dumps({"organisation": org, "reponses": reponses}, ensure_ascii=False), "utf-8")
    (sortie / "documents.json").write_text(json.dumps(documents), "utf-8")
    print(f"{len(reponses)} réponses, {sum(len(v) for v in documents.values())} pages -> {sortie}")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
