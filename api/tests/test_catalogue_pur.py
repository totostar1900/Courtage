"""Le catalogue anonyme, sans base : les groupes visibles et les noms de catégories."""
from courtage.catalogue import Partage, anonymiser_categories, groupes_visibles


def p(n: int, pays="CM", secteur="commerce", taille="50_a_250", entreprise=None) -> Partage:
    return Partage(id=f"p{n}", empreinte=entreprise or f"e{n}", pays=pays, secteur=secteur, taille=taille,
                   convention_code="CM_COMMERCE", categories=[])


def test_sous_cinq_entreprises_rien_ne_se_voit():
    assert groupes_visibles([p(i) for i in range(4)]) == []


def test_une_entreprise_qui_partage_deux_fois_compte_pour_une():
    assert groupes_visibles([p(i, entreprise="meme") for i in range(6)]) == []


def test_cinq_entreprises_d_une_meme_case_montrent_tout():
    [(attributs, membres)] = groupes_visibles([p(i) for i in range(5)])
    assert attributs == {"pays": "CM", "secteur": "commerce", "taille": "50_a_250"} and len(membres) == 5


def test_une_petite_case_garde_tout_son_groupe_au_niveau_du_dessus():
    """Six commerces de taille moyenne, deux petits : montrer la taille des six désignerait les deux
    autres comme « la petite case ». Les huit restent ensemble, au niveau du secteur."""
    partages = [p(i) for i in range(6)] + [p(10 + i, taille="moins_de_50") for i in range(2)]
    [(attributs, membres)] = groupes_visibles(partages)
    assert attributs == {"pays": "CM", "secteur": "commerce"} and len(membres) == 8


def test_des_groupes_qui_forment_une_partition_chacun_d_au_moins_cinq():
    partages = ([p(i) for i in range(5)] + [p(10 + i, taille="plus_de_250") for i in range(5)]
                + [p(20 + i, secteur="banque_assurance") for i in range(7)]
                + [p(30 + i, pays="GA", secteur="energie_mines") for i in range(3)])
    groupes = groupes_visibles(partages)
    # Le Gabon n'a que trois entreprises : la CEMAC reste un seul groupe, sans pays.
    assert [a for a, _ in groupes] == [{}]
    sans_gabon = groupes_visibles([x for x in partages if x.pays == "CM"])
    assert [a for a, _ in sans_gabon] == [
        {"pays": "CM", "secteur": "banque_assurance", "taille": "50_a_250"},
        {"pays": "CM", "secteur": "commerce", "taille": "50_a_250"},
        {"pays": "CM", "secteur": "commerce", "taille": "plus_de_250"}]
    vus = [m.id for _, ms in sans_gabon for m in ms]
    assert sorted(vus) == sorted(x.id for x in partages if x.pays == "CM") and len(vus) == len(set(vus))
    assert all(len({m.empreinte for m in ms}) >= 5 for _, ms in sans_gabon)


def test_un_nom_de_categorie_inhabituel_devient_une_lettre():
    categories = [{"categorie": "Pilotes de ligne"}, {"categorie": "cadres"}, {"categorie": "Agent de maitrise"},
                  {"categorie": "Navigants"}, {"categorie": "*"}]
    assert [c["categorie"] for c in anonymiser_categories(categories)] == [
        "Catégorie A", "cadres", "Agent de maitrise", "Catégorie B", "*"]
