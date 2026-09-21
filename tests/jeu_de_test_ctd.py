"""Jeu de test synthetique des stations a une seule sonde CTD.

Fabrique des exports Diver avec leurs pieges (en-tete a ligne variable, pied
END OF DATA, virgules decimales, mS/cm, cp1252, campagnes qui se recouvrent),
un ancien consolide separe par un trou, puis execute le notebook de la station
et verifie que la chronique est continue et complete.

    python3 tests/jeu_de_test_ctd.py                # toutes les stations
    python3 tests/jeu_de_test_ctd.py Goudou /tmp/jdt
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from stations_ctd import STATIONS, BARO_COL

DEBUT = pd.Timestamp("2019-01-01")
FIN = pd.Timestamp("2026-04-30 23:00")
HEURES = pd.date_range(DEBUT, FIN, freq="1h")
RNG = np.random.default_rng(7)

OFFSET_CTD_BRUT = -76.86         # la CTD lit 76.86 cm de moins que l'echelle
PERIODE_ANCIEN = (DEBUT, pd.Timestamp("2021-05-31 23:00"))
TROU = pd.Timestamp("2021-07-01")            # reprise apres un mois d'arret
CAMPAGNES = [(TROU, pd.Timestamp("2023-06-30 23:00"), "UTC+1"),
             (pd.Timestamp("2023-06-20"), pd.Timestamp("2025-03-31 23:00"), "UTC+2"),
             (pd.Timestamp("2025-03-25"), FIN, "UTC+1")]

t = np.arange(len(HEURES), dtype=float)
VERITE = pd.DataFrame({
    "niveau": (95 + 30 * np.sin(2 * np.pi * t / (24 * 365.25))
               + 6 * np.sin(2 * np.pi * t / (24 * 30)) + RNG.normal(0, 0.6, t.size)),
    "cond": 520 + 45 * np.sin(2 * np.pi * t / (24 * 365.25) + 1.1) + RNG.normal(0, 2.0, t.size),
    "temp": 12.1 + 1.8 * np.sin(2 * np.pi * t / (24 * 365.25) + 0.4) + RNG.normal(0, 0.05, t.size),
    "baro": 1013 + 8 * np.sin(2 * np.pi * t / (24 * 11)) + RNG.normal(0, 1.5, t.size),
}, index=HEURES)


def _fr(x, nd=3):
    return "" if pd.isna(x) else f"{x:.{nd}f}".replace(".", ",")


def ecrire_ctd(chemin, debut, fin, decalage, en_ms, encodage):
    sous = VERITE.loc[debut:fin]
    dates = sous.index + pd.Timedelta(hours=decalage)
    unite, facteur = ("mS/cm", 0.001) if en_ms else ("µS/cm", 1.0)
    lignes = ["Data file for DataLogger.", "=" * 30]
    lignes += [f"Ligne de preambule {i}" for i in range(RNG.integers(20, 60))] + ["[Data]"]
    lignes.append(f"Date/time;Pression[cmH2O];Température[°C];2:Cond. spéc.[{unite}]")
    pression = sous["niveau"].to_numpy() + OFFSET_CTD_BRUT + sous["baro"].to_numpy() * 1.019716
    for d, p, tt, c in zip(dates, pression, sous["temp"], sous["cond"] * facteur):
        lignes.append(f"{d:%Y/%m/%d %H:%M:%S};{_fr(p)};{_fr(tt)};{_fr(c, 5 if en_ms else 2)}")
    lignes.append("END OF DATA FILE OF DATALOGGER FOR WINDOWS")
    Path(chemin).write_text("\n".join(lignes), encoding=encodage)


def fabriquer(base, st):
    """Sans table UTC, les exports sont ecrits deja en UTC : le notebook ne
    convertit pas, la chronique doit quand meme tomber sur la verite."""
    base = Path(base)
    (base / "Données brutes").mkdir(parents=True, exist_ok=True)
    (base / "sorties").mkdir(parents=True, exist_ok=True)

    sous = VERITE.loc[PERIODE_ANCIEN[0]:PERIODE_ANCIEN[1]]
    pd.DataFrame({
        st["col_date_old"]: sous.index,
        "Niveau_(cm)": sous["niveau"].to_numpy(),
        "Cond_(µS/cm)": sous["cond"].to_numpy(),
        "Temp_(°C)": sous["temp"].to_numpy(),
    }).to_excel(base / "old.xlsx", index=False)

    noms, fuseaux = [], []
    for i, (d, f, fuseau) in enumerate(CAMPAGNES, start=1):
        nom = f"{st['prefixe']}_{i}_diver.csv"
        decalage = {"UTC+1": 1, "UTC+2": 2}[fuseau] if st["utc"] else 0
        ecrire_ctd(base / "Données brutes" / nom, d, f, decalage,
                   en_ms=(i == 2), encodage="cp1252" if i == 3 else "utf-8")
        noms.append(nom)
        fuseaux.append(fuseau)
    if st["utc"]:
        pd.DataFrame({"Nom fichier": noms, "UTC fichier": fuseaux}).to_excel(
            base / "UTC_CTD.xlsx", index=False)

    pd.DataFrame({"DATE": VERITE.index, BARO_COL: VERITE["baro"].to_numpy()}
                 ).to_excel(base / "baro.xlsx", index=False)

    pluie = pd.DataFrame({"Date": pd.date_range(DEBUT, FIN, freq="1D")})
    pluie["Precipitation (mm)"] = np.clip(RNG.gamma(0.6, 4, len(pluie)) - 1, 0, None)
    pluie.to_csv(base / "Pluie_BV_Ouysse.csv", index=False)


def cellule_chemins(base, st):
    utc = ('UTC_CTD_PATH = os.path.join(BASE, "UTC_CTD.xlsx")\nCOL_UTC = "UTC fichier"\n'
           if st["utc"] else "")
    return f'''
import os
BASE = {str(base)!r}
CTD_PATH    = os.path.join(BASE, "Données brutes")
BARO_PATH   = os.path.join(BASE, "baro.xlsx")
PLUIE_PATH  = os.path.join(BASE, "Pluie_BV_Ouysse.csv")
OLDDATA_PATH     = os.path.join(BASE, "old.xlsx")
{utc}SORTIE_CONSOLIDE = os.path.join(BASE, "sorties", "consolide.xlsx")
SORTIE_FINALE    = os.path.join(BASE, "sorties", "final.xlsx")
SORTIE_SVG       = os.path.join(BASE, "sorties", "Graphes.svg")
PREFIXE_CTD = {st["prefixe"]!r}
BARO_COL    = {BARO_COL!r}
PAS         = "1h"
PARAMETRES = ["Niveau_(cm)", "Conductivité", "Température"]
'''


def executer(notebook, base, st):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    nb = json.loads(Path(notebook).read_text(encoding="utf-8"))
    code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    code[1] = cellule_chemins(base, st)       # la 2e cellule de code porte les chemins
    espace = {"__name__": "__notebook__", "display": lambda *a, **k: None}
    for i, src in enumerate(code, start=1):
        try:
            exec(compile(src, f"<cellule {i}>", "exec"), espace)
        except Exception:
            print(f"\n=== ECHEC cellule de code {i} ===\n{src}")
            raise
    return espace


def verifier(espace, base):
    ok = True

    def check(nom, condition, detail=""):
        nonlocal ok
        ok = ok and bool(condition)
        print(f"  [{'OK ' if condition else 'KO '}] {nom}" + (f"  {detail}" if detail else ""))

    full = espace["full_data"]

    attendu = pd.date_range(full.index.min(), full.index.max(), freq="1h")
    check("grille horaire reguliere et complete", full.index.equals(attendu), f"{len(full)} pas")

    check("les 3 campagnes sont lues", len(espace["morceaux"]) == 3,
          f"{len(espace['morceaux'])} campagnes")

    # La compensation baro doit etre en cmH2O : sinon le niveau suit la pression
    # atmospherique. Se mesure avant raccordement, qui n'ajoute qu'une constante.
    ctd = espace["merge_ctd_df"].set_index("DATE")["Niveau_(cm)"]
    resid = (ctd - VERITE["niveau"].reindex(ctd.index)).dropna()
    check("compensation baro en cmH2O", resid.std() < 1.5, f"ecart-type {resid.std():.3f} cm")

    # Le raccordement doit supprimer la marche a la reprise.
    avant = full.loc[TROU - pd.Timedelta(hours=3):TROU - pd.Timedelta(hours=1), "Niveau_(cm)"]
    apres = full.loc[TROU:TROU + pd.Timedelta(hours=2), "Niveau_(cm)"]
    saut = abs(float(apres.mean() - avant.mean())) if avant.notna().any() else 0.0
    check("pas de marche a la reprise apres le trou", saut < 5.0, f"saut {saut:.2f} cm")

    # mS/cm de la 2e campagne converti en µS/cm.
    d = pd.Timestamp("2022-06-01 12:00")
    check("conductivite en µS/cm sur toute la chronique",
          400 < float(full.loc[d, "Conductivité"]) < 700,
          f"{full.loc[d, 'Conductivité']:.1f} µS/cm")

    for col in espace["PARAMETRES"]:
        check(f"{col} renseigne", full[col].notna().mean() > 0.9,
              f"{full[col].notna().mean():.1%}")

    check("statuts ecrits", all(f"Statut_{c}" in full for c in espace["PARAMETRES"]))
    check("fichier final ecrit", (Path(base) / "sorties" / "final.xlsx").exists())
    return ok


def tester(nom, base):
    st = STATIONS[nom]
    print(f"\n=== {nom}")
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    fabriquer(base, st)
    espace = executer(Path(__file__).resolve().parent.parent / st["fichier"], base, st)
    return verifier(espace, base)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sys.exit(0 if tester(sys.argv[1], sys.argv[2] if len(sys.argv) > 2
                             else f"jeu_de_test_{sys.argv[1]}") else 1)
    import tempfile
    tous = True
    with tempfile.TemporaryDirectory() as tmp:
        for nom in STATIONS:
            tous = tester(nom, Path(tmp) / nom) and tous
    print("\nTOUTES LES STATIONS OK" if tous else "\nECHEC")
    sys.exit(0 if tous else 1)
