# -*- coding: utf-8 -*-
"""Genere les notebooks des stations a une seule sonde CTD.

Meme logique que `generer_stations.py` pour les stations a plusieurs sondes :
le code commun vit dans `ouysse`, le notebook ne garde que ce qui est propre a
la station, declare dans `stations_ctd.py`. Relancer apres toute evolution :

    python3 tests/generer_stations_ctd.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from stations_ctd import STATIONS, BARO, PLUIE, BARO_COL

REPO = Path(__file__).resolve().parent.parent


def md(txt):
    return {"cell_type": "markdown", "metadata": {},
            "source": txt.strip("\n").splitlines(keepends=True)}


def code(txt):
    return {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None,
            "source": txt.strip("\n").splitlines(keepends=True)}


def remplir(gabarit, **kw):
    for cle, val in kw.items():
        gabarit = gabarit.replace("__%s__" % cle, str(val))
    return gabarit


ENTETE = '''
# __NOM__ - consolidation des chroniques

Une seule sonde : **CTD** (Diver autonome : niveau, conductivité, température).
Pas de choix de sonde, pas de fusion, pas de points de contrôle.

Les fonctions communes sont dans la librairie `ouysse`. Ce notebook ne garde que
ce qui est propre à la station : chemins, mesures écartées, réglages du filtre.
'''

IMPORTS = '''
import os
import unicodedata

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import ouysse
from ouysse import *          # fonctions communes a toutes les stations

print("ouysse-hydro", ouysse.__version__)
'''

CHEMINS = '''
BASE        = r"__BASE__"
CTD_PATH    = os.path.join(BASE, r"Données brutes")
BARO_PATH   = r"__BARO__"
PLUIE_PATH  = r"__PLUIE__"

__OLD_PATH____UTC_PATH__SORTIE_CONSOLIDE = os.path.join(BASE, r"__SORTIES____NOM___consolide.xlsx")
SORTIE_FINALE    = os.path.join(BASE, r"__SORTIES____NOM___final.xlsx")
SORTIE_SVG       = os.path.join(BASE, r"__SORTIES__Graphes.svg")

PREFIXE_CTD = "__PREFIXE__"
BARO_COL    = "__BARO_COL__"
__COL_UTC__PAS         = "1h"

PARAMETRES = ["Niveau_(cm)", "Conductivité", "Température"]
'''

CTD = '''
__LIRE_META__baro = pd.read_excel(BARO_PATH)[["DATE", BARO_COL]]
baro["DATE"] = pd.to_datetime(baro["DATE"], errors="coerce")
baro = baro.dropna(subset=["DATE"]).drop_duplicates("DATE")

morceaux = []
for nom in fichiers(CTD_PATH, PREFIXE_CTD):
    try:
__LECTURE__
    except Exception as e:
        print(f"  IGNORÉ  {nom} : {e}")
        continue
    m = pd.merge(CTD, baro, left_on="Date/time", right_on="DATE", how="left")
    m["Niveau_(cm)"] = m["Pression[cmH2O]"] - m[BARO_COL] * HPA_EN_CMH2O
    m = m.rename(columns={"Cond_(µS/cm)": "Conductivité", "Température[°C]": "Température"})
    morceaux.append(m[["Date/time"] + PARAMETRES])
__TRACE__
merge_ctd_df = pd.concat(morceaux, ignore_index=True).sort_values("Date/time", kind="stable")
merge_ctd_df["DATE"] = merge_ctd_df["Date/time"]
print(f"\\n{len(morceaux)} campagne(s), {len(merge_ctd_df)} enregistrements.")
'''

RACCORD = '''
#: Les anciens consolidés n'ont pas tous les mêmes en-têtes : les clés absentes
#: sont ignorées, ce dictionnaire couvre les deux conventions rencontrées.
RENOMMAGE_OLD = {
    "Date/time": "DATE",
    "NIVEAU": "Niveau_(cm)",
    "CONDUCTIVITE": "Conductivité",
    "TEMPERATURE CTD": "Température",
    "Cond_(µS/cm)": "Conductivité",
    "Temp_(°C)": "Température",
}

#: µ (U+00B5) et μ (U+03BC) sont identiques a l'oeil : sans normalisation NFKC,
#: le renommage echoue en silence sur la conductivite.
norme = lambda c: unicodedata.normalize("NFKC", str(c)).strip()

olddata_df = pd.read_excel(OLDDATA_PATH)
olddata_df.columns = [norme(c) for c in olddata_df.columns]
olddata_df = olddata_df.rename(columns={norme(k): v for k, v in RENOMMAGE_OLD.items()})
olddata_df["DATE"] = pd.to_datetime(olddata_df["DATE"], errors="coerce")
olddata_df = olddata_df.dropna(subset=["DATE"]).sort_values("DATE")

manquantes = [c for c in PARAMETRES if c not in olddata_df]
if manquantes:
    print(f"Absentes de l'ancien consolidé : {manquantes}\\n"
          f"  colonnes lues : {list(olddata_df.columns)}\\n"
          f"  compléter RENOMMAGE_OLD si l'une d'elles porte un autre nom")

merge_ctd_df = raccorder_campagnes(olddata_df, merge_ctd_df, [
    (nom, col, col, unite)
    for nom, col, unite in [("Niveau", "Niveau_(cm)", "cm"),
                            ("Conductivité", "Conductivité", "µS/cm")]
    if col in olddata_df])
'''

ASSEMBLAGE = '''
full_data = sur_grille([empiler(__PILES__, PARAMETRES)], PAS)

print("Hors gamme physique :")
full_data = appliquer_gammes(full_data__GAMMES__)

full_data.to_excel(SORTIE_CONSOLIDE)
print(f"\\nfichier fusionné : {SORTIE_CONSOLIDE}")
'''

CORRECTIONS = '''
#: (début, fin, colonne, motif) : mesures mises à l'écart.
VOIES_ECARTEES = [
]

print("Voies écartées :")
full_data = ecarter(full_data, VOIES_ECARTEES)
'''

IQR = '''
FENETRE_IQR, K_IQR = "24h", 0.1   # k = 0 : pas de filtre
LISSAGE_H = 6                     # 0 = pas de lissage ; sinon médiane glissante, en heures

avant = full_data["Conductivité"]
full_data["Conductivité"] = filtre_iqr(avant, FENETRE_IQR, K_IQR, lissage_h=LISSAGE_H)
full_data["Conductivité_Moyenne_Mobile"] = full_data["Conductivité"].rolling("6h", center=True).mean()

graphe([(avant, "avant IQR et lissage", "darkorange"),
        (full_data["Conductivité"], "après IQR et lissage", "black")],
       titre="Conductivité", ylab="Conductivité (µS/cm)")
'''

STATUTS = '''
NIVEAU_NGF = None       # cote du zéro de l'échelle, None si elle n'est pas connue
MAX_TROU_H = 12

full_data = interpoler_avec_statut(full_data, PARAMETRES, MAX_TROU_H, PAS)

if NIVEAU_NGF is not None:
    full_data["Niveau_(mNGF)"] = NIVEAU_NGF + full_data["Niveau_(cm)"] / 100
    full_data["Statut_Niveau_(mNGF)"] = full_data["Statut_Niveau_(cm)"]
    print(f"Zéro de l'échelle à {NIVEAU_NGF:.4f} m NGF")
display(pd.DataFrame({c: full_data[f"Statut_{c}"].value_counts()
                      for c in PARAMETRES}).fillna(0).astype(int).T)
'''

SAUVEGARDE = '''
finaux = [c for c in PARAMETRES + ["Niveau_(mNGF)"] if c in full_data]
colonnes = [c for p in finaux for c in (p, f"Statut_{p}") if c in full_data]
sortie = full_data[colonnes].copy()
sortie.attrs["ouysse"] = ouysse.__version__
sortie.to_excel(SORTIE_FINALE)
print(f"{SORTIE_FINALE} : {len(sortie)} pas x {len(colonnes)} colonnes "
      f"(ouysse-hydro {ouysse.__version__})")

graphe_synthese(full_data, "Niveau_(cm)", "Niveau (cm)", pluie=PLUIE_PATH, sortie=SORTIE_SVG)
'''


def construire(nom, st):
    sorties = st["sorties"] + "\\" if st["sorties"] else ""
    if st["utc"]:
        lire_meta = "metadata = pd.read_excel(UTC_CTD_PATH)\n"
        lecture = ('        CTD, decalage = en_utc(lire_CTD(nom, CTD_PATH, PAS), nom,\n'
                   '                               metadata, col_utc=COL_UTC)')
        trace = ('    print(f"  {nom:45s} UTC+{decalage:g} vers UTC   ({len(CTD)} lignes)")\n')
        utc_path = 'UTC_CTD_PATH     = os.path.join(BASE, "UTC_CTD.xlsx")\n'
        col_utc = 'COL_UTC     = "UTC fichier"     # en-tête de la table UTC\n'
        note_utc = ""
    else:
        lire_meta = ""
        lecture = "        CTD = lire_CTD(nom, CTD_PATH, PAS)"
        trace = '    print(f"  {nom:45s} {len(CTD)} lignes")\n'
        utc_path = ""
        col_utc = ""
        note_utc = ("\n\n**Pas de table UTC pour cette station** : les horodatages sont repris\n"
                    "tels quels. Si les exports sont en heure locale, la chronique l'est aussi.\n"
                    "Pour corriger, ajouter `UTC_CTD.xlsx` et passer `utc` à True dans\n"
                    "`tests/stations_ctd.py`.")

    n = [0]

    def titre(t):
        n[0] += 1
        return "## %d. %s" % (n[0], t)

    old_path = ('OLDDATA_PATH     = os.path.join(BASE, r"%s")\n' % st["old"]
                if st["old"] else "")
    cellules = [
        md(remplir(ENTETE, NOM=nom)),
        md(titre("Imports")), code(IMPORTS),
        md(titre("Chemins d'accès")),
        code(remplir(CHEMINS, BASE=st["base"], BARO=BARO, PLUIE=PLUIE, OLD_PATH=old_path,
                     SORTIES=sorties, NOM=nom, PREFIXE=st["prefixe"], BARO_COL=BARO_COL,
                     UTC_PATH=utc_path, COL_UTC=col_utc)),
        md(titre("CTD : lecture, UTC et compensation barométrique") + "\n\n"
           "`lire_CTD` encaisse les pièges du format Diver (en-tête à une ligne variable, pied\n"
           "`END OF DATA`, virgules décimales, mS/cm ou µS/cm)." + note_utc),
        code(remplir(CTD, LIRE_META=lire_meta, LECTURE=lecture, TRACE=trace)),
        *([md(titre("Raccordement à l'ancienne chronique") + "\n\n"
              "L'ancien fichier consolidé et les campagnes récentes sont la **même sonde CTD**,\n"
              "séparées par un trou d'exploitation : le décalage est mesuré à la jonction et\n"
              "appliqué aux campagnes, pour que la chronique soit continue."),
           code(RACCORD)] if st["old"] else []),
        md(titre("Assemblage sur la grille horaire") + ("" if st["old"] else
           "\n\nPas d'ancienne chronique à raccorder pour cette station.")),
        code(remplir(ASSEMBLAGE,
                     PILES="[olddata_df, merge_ctd_df]" if st["old"] else "[merge_ctd_df]",
                     GAMMES=", " + st["gammes"] if st["gammes"] else "")),
        md(titre("Corrections capteur") + "\n\n"
           "`VOIES_ECARTEES` met des mesures à l'écart. Il n'y a pas de sonde de secours ici :\n"
           "la lacune reste, et l'interpolation ne comblera pas plus de 12 h."),
        code(CORRECTIONS),
        md(titre("Filtre IQR et lissage")), code(IQR),
        md(titre("Cote NGF, interpolation et statuts") + "\n\n"
           "Les lacunes de moins de 12 h sont comblées. `Statut_<grandeur>` dit si la valeur\n"
           "est mesurée, interpolée ou manquante."),
        code(STATUTS),
        md(titre("Sauvegarde et graphe de synthèse")), code(SAUVEGARDE),
        code("graphe_statuts(full_data, finaux)"),
    ]
    return {"cells": cellules,
            "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                        "name": "python3"},
                         "language_info": {"name": "python"}},
            "nbformat": 4, "nbformat_minor": 5}


if __name__ == "__main__":
    for nom, st in STATIONS.items():
        nb = construire(nom, st)
        (REPO / st["fichier"]).write_text(json.dumps(nb, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
        lignes = sum(len("".join(c["source"]).splitlines())
                     for c in nb["cells"] if c["cell_type"] == "code")
        print(f"{st['fichier']:58s} {len(nb['cells']):3d} cellules  {lignes:4d} lignes de code")
