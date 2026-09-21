# -*- coding: utf-8 -*-
"""Consolidation des chroniques des stations hydrometriques de l'Ouysse.

Les fonctions communes aux notebooks de station : lecture des exports bruts,
corrections de voie, choix de sonde et fusion, post-traitement, graphes de
controle. Les decisions (chemins, priorites, periodes ecartees, calages,
tarage, cote NGF) restent dans le notebook de chaque station.

    from ouysse import *
    print(ouysse.__version__)   # a reporter dans le fichier de sortie

Le code d'une fonction se lit sans quitter le notebook :

    import inspect; print(inspect.getsource(fusionner))
"""
__version__ = "0.1.0"

from .lecture import (fichiers, lire_CTD, lire_VuSitu, lire_OTT, en_utc, appliquer_gammes,
                      NOMS_TROLL, NOMS_OTT, NOMS_OTT_CTD, GAMMES, HPA_EN_CMH2O)
from .correction import (decaler, ecarter, lire_points, caler, raccorder, raccorder_campagnes)
from .fusion import (empiler, sur_grille, reunir_doublons, choisir_sondes, fusionner,
                     filtre_iqr, interpoler_avec_statut)
from .graphes import COULEURS, graphe, graphe_sondes, graphe_statuts, graphe_synthese

__all__ = ["fichiers", "lire_CTD", "lire_VuSitu", "lire_OTT", "en_utc", "appliquer_gammes",
           "NOMS_TROLL", "NOMS_OTT", "NOMS_OTT_CTD", "GAMMES", "HPA_EN_CMH2O",
           "decaler", "ecarter", "lire_points", "caler", "raccorder", "raccorder_campagnes",
           "empiler", "sur_grille", "reunir_doublons", "choisir_sondes", "fusionner",
           "filtre_iqr", "interpoler_avec_statut",
           "COULEURS", "graphe", "graphe_sondes", "graphe_statuts", "graphe_synthese",
           "__version__"]
