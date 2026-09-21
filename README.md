# Intrakarst

Consolidation des chroniques des stations hydrometriques du systeme karstique de
l'Ouysse. Un notebook par station.

Tous suivent la meme logique : une colonne par sonde, une sonde choisie
automatiquement a chaque pas dans l'ordre `ORDRE`, des periodes imposees a la main
quand le graphe montre que ce choix n'est pas le bon, un recalage mesure a chaque
changement de sonde, puis calage sur les points de controle, filtre IQR, interpolation
des lacunes de moins de 12 h et statut par grandeur.

## La librairie `ouysse`

Les fonctions communes aux cinq stations (lecture des exports bruts, corrections, 
choix de sonde et fusion, filtre IQR, interpolation, graphes) sont dans le
package `ouysse`. Les notebook portent les chemins, les corrections, 
les courbes de tarage, la cote NGF, propres à chaque station.

    from ouysse import *

le dossier `ouysse/` doit être à la racine du dépôt (à coté du notebook) et s'importe tel quel.
Le code d'une fonction se lit avec :

    import inspect; print(inspect.getsource(fusionner))
