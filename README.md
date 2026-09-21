# Intrakarst

Consolidation des chroniques des stations hydrometriques du systeme karstique de
l'Ouysse. Un notebook par station.

Tous les traitements suivent la même logique de construction des séries temporelles. Chaque sonde est représentée par une colonne. Lorsqu'un même paramètre est mesuré par plusieurs sondes, une sonde est sélectionnée automatiquement selon un ordre de priorité défini par l'utilisateur. Il est également possible d'imposer manuellement une sonde comme prioritaire sur une période donnée.

À chaque changement de sonde, un recalage est effectué par rapport à la sonde précédente afin d'assurer la continuité de la série, puis un ajustement est réalisé à partir des points de contrôle. Les données sont ensuite traitées avec un filtre IQR pour éliminer les valeurs aberrantes, les lacunes de moins de 12 heures sont interpolées, et un statut de qualité est attribué pour chaque grandeur.

## La librairie `ouysse`

Elle regroupe les fonctions communes aux stations (lecture des exports bruts, corrections, 
choix de sonde et fusion, filtre IQR, interpolation, graphes), les fonctions sont dans le
package `ouysse`. Les notebook portent les chemins, les corrections, 
les courbes de tarage, la cote NGF, propres à chaque station.

    from ouysse import *

le dossier `ouysse/` doit être à la racine du dépôt (à coté du notebook) et s'importe tel quel.
Le code d'une fonction se lit avec :

    import inspect; print(inspect.getsource(fusionner))
