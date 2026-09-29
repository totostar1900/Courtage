"""Le cycle annuel : calculé depuis la dernière étude émise, les étapes lues dans les données, les points d'attention,
les rappels au plus une fois par étape, état et année."""
from datetime import date

from sqlalchemy.orm import Session

from courtage.db import contexte
from courtage.services import annuel
from tests.outils import V1, deposer, en_tant_que, fichier_azito
from tests.test_rapport import emettre


def cal(client, a):
    r = client.get(f"{V1}/organisations/{a['org']}/calendrier", headers=en_tant_que(a["drh"]))
    assert r.status_code == 200, r.text
    return r.json()


def etape(c, code):
    return next(e for e in c["etapes"] if e["code"] == code)


def test_sans_etude_emise_pas_de_cycle(client, azito):
    assert cal(client, azito) == {"derniere": None, "prochaine": None, "etapes": []}


def test_le_cycle_part_de_la_derniere_etude_et_avance_avec_elle(client, azito):
    emettre(client, azito)                                     # au 31/12/2019
    c = cal(client, azito)
    assert (c["derniere"], c["prochaine"]) == ("2019-12-31", "2020-12-31")
    assert etape(c, "personnel")["echeance"] == "2021-01-30" and etape(c, "personnel")["etat"] == "en_retard"
    alertes = client.get(f"{V1}/organisations/{azito['org']}/alertes", headers=en_tant_que(azito["drh"])).json()
    # Le retard est dit une fois, par l'alerte qui existait déjà ; le calendrier ne la double pas.
    codes = [x["code"] for x in alertes]
    assert "etude_a_renouveler" in codes and "annuel_personnel" not in codes and "annuel_evaluation" not in codes
    # Le personnel au 31/12/2020 : l'étape est faite.
    f = deposer(client, azito["org"], azito["drh"], fichier_azito(), date_donnees="2020-12-31")
    assert etape(cal(client, azito), "personnel")["fait_le"] == "2020-12-31"
    # L'évaluation au 31/12/2020 émise : le cycle passe à 2021.
    emettre(client, {**azito, "fichier": f["id"]}, date_evaluation="2020-12-31")
    assert cal(client, azito)["prochaine"] == "2021-12-31"


def test_les_etats_selon_le_jour(bases, client, azito):
    emettre(client, azito)
    with Session(bases[1]) as session, session.begin():
        contexte(session.connection(), azito["org"])
        etat = lambda jour: {e["code"]: e["etat"] for e in annuel.calendrier(session, jour)["etapes"]}  # noqa: E731
        assert etat(date(2020, 11, 1))["personnel"] == "a_venir"        # échéance au 30/01/2021
        assert etat(date(2021, 1, 5))["personnel"] == "bientot"
        assert etat(date(2021, 2, 1))["personnel"] == "en_retard"
        # Une étape bientôt due s'annonce (information) ; son retard, les alertes existantes le disent.
        assert {a[1]: a[0] for a in annuel.alertes(session, date(2021, 1, 5))}["annuel_personnel"] == "info"
        assert "annuel_personnel" not in {a[1] for a in annuel.alertes(session, date(2021, 2, 10))}


def test_les_rappels_une_fois_par_etape_etat_et_annee(bases, client, azito):
    from courtage.messagerie import CourrielJournal
    emettre(client, azito)                                     # prochaine évaluation au 31/12/2020
    courriel = CourrielJournal()

    def passer(jour):
        return annuel.rappeler_partout(bases[1], courriel, "https://exemple.cm", jour)

    passer(date(2021, 1, 5))                                   # personnel et évaluation : bientôt dus
    recus = [m for m in courriel.envoyes if "AZITO" in m.texte]
    assert any("« Mettre à jour le personnel » est attendue le 30/01/2021" in m.texte for m in recus)
    assert all("https://exemple.cm/dossier/" in m.texte for m in recus)
    avant = len(courriel.envoyes)
    passer(date(2021, 1, 6))                                   # le lendemain : rien de nouveau
    assert len(courriel.envoyes) == avant
    passer(date(2021, 2, 1))                                   # le personnel est en retard : un rappel de plus
    assert any("est en retard" in m.texte and "Mettre à jour le personnel" in m.texte for m in courriel.envoyes[avant:])
    # Sans expéditeur, rien ne part et rien n'est noté.
    assert annuel.rappeler_partout(bases[1], None, None, date(2021, 3, 5)) == 0
