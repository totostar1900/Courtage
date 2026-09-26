"""Fichier du personnel : lecture et contrôles (spec §6).

Le fichier arrive tel qu'une DRH l'exporte : xlsx ou csv, une ligne de titre
au-dessus des intitulés, des intitulés en français ou en anglais, des dates en
jj/mm/aaaa, des montants avec des espaces. On reconnaît les colonnes par leur
intitulé. Les colonnes de nom sont repérées pour être IGNORÉES : leurs valeurs
ne sont jamais lues (spec §2.8).
"""
from .controles import controler, controler_parametres, controler_resultat
from .lecture import Anomalie, Lecture, LigneLue, lire_fichier, salaries

__all__ = [
    "Anomalie",
    "Lecture",
    "LigneLue",
    "controler",
    "controler_parametres",
    "controler_resultat",
    "lire_fichier",
    "salaries",
]
