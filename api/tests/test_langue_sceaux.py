"""Un document scellé est en français, quelle que soit la langue de l'écran qui l'a fait émettre."""
import pymupdf

from tests.outils import V1, en_tant_que, etude

EN = {"X-Langue": "en"}


def texte_pdf(contenu: bytes) -> str:
    with pymupdf.open(stream=contenu, filetype="pdf") as doc:
        return " ".join(page.get_text() for page in doc)


def test_un_rapport_emis_depuis_un_ecran_anglais_reste_en_francais(client, azito):
    e = etude(client, azito).json()                     # le fichier d'AZITO porte des avertissements non bloquants
    lu = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}",
                    headers={**en_tant_que(azito["drh"]), **EN}).json()
    anglais = {a["message"] for a in lu["anomalies"]}
    francais = {a["message"] for a in e["anomalies"]}
    assert anglais != francais                                                   # l'écran lit en anglais
    r = client.post(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/emission",
                    headers={**en_tant_que(azito["conseiller"]), **EN})
    assert r.status_code == 200, r.text
    pdf = client.get(f"{V1}/organisations/{azito['org']}/etudes/{e['id']}/rapport", headers=en_tant_que(azito["drh"]))
    contenu = " ".join(texte_pdf(pdf.content).split())
    assert "Dette actuarielle" in contenu or "dette actuarielle" in contenu
    for message in anglais - francais:
        assert " ".join(message.split())[:40] not in contenu                    # pas une ligne d'anglais au rapport
