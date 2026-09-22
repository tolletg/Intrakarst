# -*- coding: utf-8 -*-
"""Les stations a une seule sonde CTD Diver.

Ce que porte chaque station : ses chemins, le prefixe de ses campagnes, la
presence ou non d'une table UTC et d'un ancien consolide a raccorder.
Tout le reste est commun et vit dans `ouysse`.
"""

RACINE = r"Y:\MISSIONS\Eau\1 - Projet Hydrogéologique Ouysse\3 - Hydrodynamique\0 - Stations en continu"
BARO = RACINE + r"\1 - Données BARO\Gourdon baro\Patm Calès et Thémines.xlsx"
PLUIE = RACINE + r"\Pluie_BV_Ouysse.csv"
BARO_COL = "Patm Thémines [hPa]"

STATIONS = {
    "Combettes": {
        "fichier": "Code pour consolider les données-Combettes.ipynb",
        "base": RACINE + r"\Combettes\Gaetan",
        "prefixe": "Combettes",
        "sorties": r"Données consolidées",
        "old": r"Données consolidées\Combettes_Old.xlsx",
        "utc": True,
        "gammes": None,
    },
    "Plana_Lac": {
        "fichier": "Code pour consolider les données-Plana_Lac.ipynb",
        "base": RACINE + r"\Lac Planagrèze\Gaetan",
        "prefixe": "Lac Plana",
        "sorties": r"données consolidées",
        "old": r"données consolidées\Plana_Old.xlsx",
        "utc": True,
        "gammes": None,
    },
    "Plana_Riviere": {
        "fichier": "Code pour consolider les données-Plana_Riviere.ipynb",
        "base": RACINE + r"\Rivière Planagrèze\Gaetan",
        "prefixe": "Plana_Riviere",
        "sorties": r"données consolidées",
        "old": r"données consolidées\PlanaRiv_Old.xlsx",
        "utc": False,          # pas de table UTC : les horodatages restent tels quels
        "gammes": None,
    },
    "Goudou": {
        "fichier": "Code pour consolider les données-Goudou.ipynb",
        "base": RACINE + r"\Goudou\Gaetan",
        "prefixe": "Goudou",
        "sorties": "",
        "old": r"Goudou brutes\GOUDOU_Old.xlsx",
        "utc": True,
        #: la sonde rend des valeurs basses hors d'eau : plancher a 300 µS/cm
        "gammes": '{**GAMMES, "cond": (300, 5000)}',
    },
    "Zobépine": {
        "fichier": "Code pour consolider les données-Zobepine.ipynb",
        "base": RACINE + r"\Zobépine\Gaetan",
        "prefixe": "Zobépine",
        "sorties": r"Données consolidées",
        "old": r"Données consolidées\Zobépine_Old.xlsx",
        "utc": False,          # pas de table UTC : les horodatages restent tels quels
        "gammes": None,
    },
}
