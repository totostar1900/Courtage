"""Lecture d'un tableur de départs passés (spec prestations §4) : les mêmes règles que le fichier du personnel.

Colonnes reconnues en français ou en anglais, dans n'importe quel ordre ; une
colonne de noms est repérée pour être écartée sans lecture. Le salaire est le
salaire MENSUEL de référence (l'IFC se compte en mois de salaire), sauf si
l'intitulé dit « annuel ».
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from .lecture import (Anomalie, _NOMS, _date, _grille_csv, _grille_xlsx, _montant, _normaliser, _periodicite_de,
                      _texte_matricule, _vide)

OBLIGATOIRES = ("matricule", "embauche", "depart", "motif", "salaire")
LIBELLES = {"matricule": "matricule", "embauche": "date d'embauche", "depart": "date de départ", "motif": "motif",
            "salaire": "salaire de référence", "verse": "montant versé", "fonds": "payé par le fonds",
            "payee_le": "date de paiement", "naissance": "date de naissance", "categorie": "catégorie"}
_SYNONYMES = {
    "matricule": ["matricule", "mat", "no", "numero", "id", "employee id", "employee number", "staff id"],
    "embauche": ["date d embauche", "embauche", "date d entree", "entree", "date entree", "date embauche",
                 "hire date", "date of hire", "start date"],
    "depart": ["date de depart", "depart", "date depart", "date de sortie", "sortie", "date sortie",
               "departure date", "exit date", "leaving date", "end date", "termination date"],
    "motif": ["motif", "motif de depart", "motif du depart", "motif de sortie", "cause", "raison", "reason",
              "reason for leaving", "exit reason"],
    "verse": ["montant verse", "verse", "ifc versee", "indemnite versee", "montant paye", "montant paye au salarie",
              "amount paid", "paid to employee"],
    "fonds": ["paye par le fonds", "part du fonds", "part fonds", "paye par l assureur", "rembourse par l assureur",
              "prise en charge", "paid by fund", "paid by insurer", "insurer paid"],
    "payee_le": ["date de paiement", "paye le", "date paiement", "date du paiement", "payment date", "paid on"],
    "naissance": ["date de naissance", "naissance", "date naissance", "birth date", "date of birth", "dob"],
    "categorie": ["categorie", "categorie professionnelle", "category", "college", "csp", "classification"],
}
MOTIFS = {
    "retraite": ["retraite", "depart en retraite", "depart a la retraite", "retraite anticipee", "mise a la retraite",
                 "retirement", "retired"],
    "demission": ["demission", "resignation", "resigned"],
    "licenciement": ["licenciement", "licencie", "dismissal", "dismissed", "fin de contrat", "rupture"],
    "deces": ["deces", "decede", "death", "deceased"],
    "autre": ["autre", "other"],
}


@dataclass
class LigneDepart:
    numero: int
    matricule: str | None = None
    motif: str | None = None
    date_embauche: date | None = None
    date_depart: date | None = None
    salaire_mensuel_reference: int | None = None
    verse: int | None = None
    part_fonds_payee: int | None = None
    payee_le: date | None = None
    date_naissance: date | None = None
    categorie: str | None = None
    bloquee: bool = False


@dataclass
class LectureDeparts:
    lignes: list[LigneDepart] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    colonnes: dict[str, str] = field(default_factory=dict)
    colonnes_ignorees: list[str] = field(default_factory=list)


def champ_de(intitule) -> str | None:
    n = _normaliser(intitule)
    if not n:
        return None
    if n in _NOMS:
        return "_nom"
    for champ, synonymes in _SYNONYMES.items():
        if n in synonymes:
            return champ
    if n.startswith(("salaire", "salary", "remuneration")):
        return "salaire"
    return None


def motif_de(x) -> str | None:
    n = _normaliser(x)
    return next((m for m, mots in MOTIFS.items() if n in mots), None)


def lire_departs(contenu: bytes, nom_fichier: str) -> LectureDeparts:
    lecture = LectureDeparts()
    extension = nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""
    if extension in ("xlsx", "xlsm"):
        grille = _grille_xlsx(contenu)
    elif extension in ("csv", "txt"):
        grille = _grille_csv(contenu)
    else:
        lecture.anomalies.append(Anomalie("bloquant", "format_non_pris_en_charge",
                                          f"Format « .{extension} » non pris en charge : envoyer un fichier xlsx ou csv."))
        return lecture

    i_entete = next((i for i, r in enumerate(grille[:15])
                     if len({champ_de(c) for c in r if c is not None} & set(OBLIGATOIRES)) >= 3), None)
    index: dict[str, int] = {}
    if i_entete is not None:
        for j, intitule in enumerate(grille[i_entete]):
            if _vide(intitule):
                continue
            champ = champ_de(intitule)
            if champ in LIBELLES and champ not in index:
                index[champ] = j
                lecture.colonnes[champ] = str(intitule)
            else:
                lecture.colonnes_ignorees.append(str(intitule))
    manquants = [LIBELLES[c] for c in OBLIGATOIRES if c not in index]
    if i_entete is None or manquants:
        attendus = ", ".join(LIBELLES[c] for c in OBLIGATOIRES)
        lecture.anomalies.append(Anomalie("bloquant", "colonnes_introuvables",
                                          f"Colonne introuvable : {', '.join(manquants) or attendus}. "
                                          f"Colonnes attendues : {attendus}."))
        return lecture

    annuel = _periodicite_de(lecture.colonnes["salaire"]) == "annuel"
    vus: dict[tuple, int] = {}
    for i in range(i_entete + 1, len(grille)):
        rangee = grille[i]
        v = {c: (rangee[j] if j < len(rangee) else None) for c, j in index.items()}
        if all(_vide(x) for x in v.values()):
            continue
        ligne = _lire_ligne(i + 1, v, annuel, lecture)
        cle = (ligne.matricule, ligne.date_depart)
        if ligne.matricule and ligne.date_depart:
            if cle in vus:
                _bloquer(lecture, ligne, "depart_en_double",
                         f"Le départ du matricule {ligne.matricule} au {ligne.date_depart:%d/%m/%Y} figure deux fois "
                         f"(lignes {vus[cle]} et {ligne.numero}).")
            vus[cle] = ligne.numero
        lecture.lignes.append(ligne)
    if not lecture.lignes:
        lecture.anomalies.append(Anomalie("bloquant", "fichier_vide", "Le fichier ne contient aucun départ."))
    return lecture


def _bloquer(lecture: LectureDeparts, ligne: LigneDepart, code: str, message: str, colonne: str | None = None):
    ligne.bloquee = True
    lecture.anomalies.append(Anomalie("bloquant", code, message, ligne=ligne.numero, colonne=colonne))


def _lire_ligne(numero: int, v: dict, annuel: bool, lecture: LectureDeparts) -> LigneDepart:
    ligne = LigneDepart(numero=numero)

    def date_de(champ):
        if _vide(v.get(champ)):
            return None
        d = _date(v[champ])
        if d is None:
            _bloquer(lecture, ligne, "date_illisible", f"Date illisible : « {v[champ]} » (attendu jj/mm/aaaa).",
                     LIBELLES[champ])
        return d

    def montant_de(champ, diviser=False):
        if _vide(v.get(champ)):
            return None
        m = _montant(v[champ])
        if m is None or m < 0:
            _bloquer(lecture, ligne, "montant_illisible", f"Montant illisible : « {v[champ]} ».", LIBELLES[champ])
            return None
        if diviser:
            m = m / 12
        return int(Decimal(m).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    ligne.matricule = None if _vide(v.get("matricule")) else _texte_matricule(v["matricule"])
    ligne.date_embauche, ligne.date_depart = date_de("embauche"), date_de("depart")
    ligne.date_naissance, ligne.payee_le = date_de("naissance"), date_de("payee_le")
    ligne.salaire_mensuel_reference = montant_de("salaire", diviser=annuel)
    ligne.verse, ligne.part_fonds_payee = montant_de("verse"), montant_de("fonds")
    ligne.categorie = None if _vide(v.get("categorie")) else str(v["categorie"]).strip()
    if not _vide(v.get("motif")):
        ligne.motif = motif_de(v["motif"])
        if ligne.motif is None:
            _bloquer(lecture, ligne, "motif_inconnu", f"Motif inconnu : « {v['motif']} » (retraite, démission, "
                     "licenciement, décès ou autre).", "motif")

    for champ, valeur in (("matricule", ligne.matricule), ("embauche", ligne.date_embauche),
                          ("depart", ligne.date_depart), ("motif", ligne.motif),
                          ("salaire", ligne.salaire_mensuel_reference)):
        if valeur is None and _vide(v.get(champ)):
            _bloquer(lecture, ligne, "champ_manquant", f"{LIBELLES[champ].capitalize()} manquant(e).", LIBELLES[champ])
    if ligne.date_embauche and ligne.date_depart and ligne.date_depart < ligne.date_embauche:
        _bloquer(lecture, ligne, "depart_avant_embauche", "Départ antérieur à l'embauche.", "date de départ")
    if ligne.part_fonds_payee is not None and ligne.payee_le is None:
        _bloquer(lecture, ligne, "date_paiement_requise", "Un paiement du fonds sans sa date.", "date de paiement")
    return ligne
