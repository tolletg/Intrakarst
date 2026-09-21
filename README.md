# station

Consolidation des chroniques des stations hydrometriques du systeme karstique de
l'Ouysse (Causses du Quercy). Un notebook par station, tenu a la main, qui sert aussi
d'historique des corrections appliquees.

| Station | Notebook | Sondes |
|---|---|---|
| Cabouy (reference) | `Code pour consolider les données-Cabouy_V4.ipynb` | CTD + TROLL + OTT |
| Fontbelle | `Code pour consolider les données-Fontbelle_V4.ipynb` | CTD + TROLL + OTT |
| Saint-Sauveur | `Code pour consolider les données-Saint_Sauveur_V3.ipynb` | CTD + TROLL |
| Thémines | `Code pour consolider les données-Thémines_V2.ipynb` | CTD + TROLL + OTT |
| Ouysse - Calès | `Code pour consolider les données-Ouysse_V3.ipynb` | CTD + OTT |

Tous suivent la meme logique : une colonne par sonde, une sonde choisie
automatiquement a chaque pas dans l'ordre `ORDRE`, des periodes imposees a la main
quand le graphe montre que ce choix n'est pas le bon, un recalage mesure a chaque
changement de sonde, puis calage sur les points de controle, filtre IQR, interpolation
des lacunes de moins de 12 h et statut par grandeur.

## La librairie `ouysse`

Les fonctions communes aux cinq stations (lecture des exports bruts, corrections de
voie, choix de sonde et fusion, filtre IQR, interpolation, graphes) sont dans le
package `ouysse`. Le notebook ne garde que les decisions : chemins, priorites,
mesures ecartees, calages, reglages, courbe de tarage, cote NGF.

    pip install -e .            # a la racine du depot
    from ouysse import *

Sans acces a pip, le dossier `ouysse/` pose a cote du notebook s'importe tel quel.
Le code d'une fonction se lit sans quitter le notebook :

    import inspect; print(inspect.getsource(fusionner))

La version de la librairie est affichee a l'execution et reportee dans le fichier de
sortie : elle dit avec quel code une chronique a ete produite.

## Outils

    python3 tests/generer_stations.py                       # regenere les cinq notebooks
    python3 tests/test_ouysse.py                            # tests unitaires de la librairie
    python3 tests/jeu_de_test_cabouy.py <notebook> <dossier>
    python3 tests/jeu_de_test_stations.py --toutes <dossier>
    python3 tests/comparer_notebooks.py <ancien> <nouveau> <dossier>

`tests/stations.py` porte les chemins, les priorites et les corrections propres a
chaque station ; `tests/generer_stations.py` en fabrique les notebooks.
