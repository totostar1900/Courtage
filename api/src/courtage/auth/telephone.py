"""Numéros de téléphone : une seule forme stockée, E.164 (« +237699123456 »).

Un numéro sans indicatif est camerounais (le premier marché) : 9 chiffres,
commençant par 6 (mobile) ou 2 (fixe). La Côte d'Ivoire a 10 chiffres
nationaux. Les autres indicatifs sont admis entre 8 et 15 chiffres au total.
"""
import re

_LONGUEURS_NATIONALES = {"237": (9,), "225": (10,), "241": (8, 9), "242": (9,), "235": (8,), "236": (8,), "240": (9,)}


def normaliser(saisi: str) -> str:
    brut = re.sub(r"[\s.\-()/]", "", str(saisi))
    if brut.startswith("00"):
        brut = "+" + brut[2:]
    if not re.fullmatch(r"\+?\d+", brut):
        raise ValueError("numéro de téléphone invalide")
    if brut.startswith("+"):
        chiffres = brut[1:]
    elif len(brut) == 9 and brut[0] in "62":
        chiffres = "237" + brut
    elif any(brut.startswith(ind) and len(brut) - len(ind) in longueurs
             for ind, longueurs in _LONGUEURS_NATIONALES.items()):
        chiffres = brut
    else:
        raise ValueError("numéro de téléphone invalide")
    for ind, longueurs in _LONGUEURS_NATIONALES.items():
        if chiffres.startswith(ind):
            national = chiffres[len(ind):]
            if len(national) not in longueurs or (ind == "237" and national[0] not in "62"):
                raise ValueError("numéro de téléphone invalide")
            return "+" + chiffres
    if not 8 <= len(chiffres) <= 15:
        raise ValueError("numéro de téléphone invalide")
    return "+" + chiffres
