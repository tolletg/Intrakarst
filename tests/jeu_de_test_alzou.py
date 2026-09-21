"""Jeu de test synthetique pour le notebook d'Alzou.

Fabrique un faux export prestataire qui reproduit les pieges du fichier reel
(horodatage a l'heure ronde au debut puis a HH:59:59.995, colonnes restees en
texte avec des cellules vides, chlorophylle a zero), execute toutes les
cellules de code du notebook, puis verifie que rien ne disparait.

    python3 tests/jeu_de_test_alzou.py "Code pour consolider les données-Alzou.ipynb" /tmp/jdt
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pandas as pd

DEBUT = pd.Timestamp("2018-03-02 14:00")
FIN = pd.Timestamp("2026-07-28 12:00")
HEURES = pd.date_range(DEBUT, FIN, freq="1h")
RNG = np.random.default_rng(12)

#: A partir de cette date le prestataire horodate a HH:59:59.995.
BASCULE = pd.Timestamp("2024-01-01")
#: Le TROLL n'est pose qu'en 2021 : avant, ses voies sont vides.
POSE_TROLL = pd.Timestamp("2021-06-01")
NGF = 284.233

t = np.arange(len(HEURES), dtype=float)
VERITE = pd.DataFrame({
    "niveau": 60 + 40 * np.sin(2 * np.pi * t / (24 * 365.25)) + RNG.normal(0, 0.6, t.size),
    "debit": np.clip(120 + 900 * np.sin(2 * np.pi * t / (24 * 365.25)), 0, None),
    "cond": 1900 + 150 * np.sin(2 * np.pi * t / (24 * 365.25) + 1.1) + RNG.normal(0, 5, t.size),
    "temp": 14 + 5 * np.sin(2 * np.pi * t / (24 * 365.25) + 0.4) + RNG.normal(0, 0.1, t.size),
    "turbi": np.clip(8 + RNG.normal(0, 3, t.size), 0, None),
    "o2": np.clip(5 + RNG.normal(0, 0.5, t.size), 0, None),
}, index=HEURES)


def fabriquer(base):
    """Ecrit Alzou_consolide.xlsx et les points de controle."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)

    dates = pd.Series(HEURES, index=HEURES)
    tardif = HEURES >= BASCULE
    dates[tardif] = HEURES[tardif] - pd.Timedelta(seconds=5, microseconds=-5000)

    def en_texte(valeurs, nd=2):
        """Colonne 'object' : des nombres, des espaces, des virgules decimales."""
        out = [f"{v:.{nd}f}" for v in valeurs]
        for i in range(0, len(out), 997):          # cellules vides eparses
            out[i] = " "
        for i in range(3, len(out), 1503):         # virgule decimale francaise
            out[i] = out[i].replace(".", ",")
        return out

    avant_troll = HEURES < POSE_TROLL
    cond = VERITE["cond"].to_numpy().copy()
    temp = VERITE["temp"].to_numpy().copy()
    turbi = VERITE["turbi"].to_numpy().copy()
    o2 = VERITE["o2"].to_numpy().copy()

    df = pd.DataFrame({
        "DATE": dates.to_numpy(),
        "Niveau_(cm)": en_texte(VERITE["niveau"], 0),
        "Niveau_(mNGF)": NGF + VERITE["niveau"].to_numpy() / 100,
        "Q_(L/s)": VERITE["debit"].to_numpy(),
        "Turbidity_Troll_(NTU)": en_texte(turbi),
        "O2_Troll_(mg/l)": en_texte(o2),
        "FluorescenceChloro_a_Troll_(RFU)": 0.0,          # la sonde rend zero
        "Cond_Troll_(µS/cm)": en_texte(cond, 0),
        "température_(°C)": en_texte(temp),
    })
    for col in ("Turbidity_Troll_(NTU)", "O2_Troll_(mg/l)", "Cond_Troll_(µS/cm)",
                "température_(°C)"):
        df.loc[avant_troll, col] = " "                    # TROLL pas encore pose
    df.to_excel(base / "Alzou_consolide.xlsx", index=False)

    d = pd.Timestamp("2025-06-12 10:00")
    i = HEURES.get_loc(d)
    pd.DataFrame({
        "Date": ["12/06/2025 10:00", "03/04/2026 10:00"],
        "Conductivité": [float(cond[i]) + 25.0, 1850.0],
        "Correction": ["Oui", "Non"],
    }).to_excel(base / "Punctual measurements .xlsx", index=False)

    pluie = pd.DataFrame({"Date": pd.date_range(DEBUT, FIN, freq="1D")})
    pluie["Precipitation (mm)"] = np.clip(RNG.gamma(0.6, 4, len(pluie)) - 1, 0, None)
    pluie.to_csv(base / "Pluie_BV_Ouysse.csv", index=False)


def cellule_chemins(base):
    return f'''
import os
BASE = {str(base)!r}
PLUIE_PATH = os.path.join(BASE, "Pluie_BV_Ouysse.csv")
PRESTATAIRE   = os.path.join(BASE, "Alzou_consolide.xlsx")
PUNCTUAL      = os.path.join(BASE, "Punctual measurements .xlsx")
SORTIE_FINALE = os.path.join(BASE, "Alzou_final.xlsx")
SORTIE_SVG    = os.path.join(BASE, "Graphes.svg")
PAS = "1h"
COLONNES = {{
    "Niveau_(cm)":        "Niveau_(cm)",
    "Débit_(L/s)":        "Q_(L/s)",
    "Conductivité":       "Cond_Troll_(µS/cm)",
    "Température":        "température_(°C)",
    "Turbidité_(NTU)":    "Turbidity_Troll_(NTU)",
    "O2_(mg/l)":          "O2_Troll_(mg/l)",
    "Chlorophylle_(RFU)": "FluorescenceChloro_a_Troll_(RFU)",
}}
PARAMETRES = list(COLONNES)
'''


def executer(notebook, base):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    nb = json.loads(Path(notebook).read_text(encoding="utf-8"))
    code = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    code[1] = cellule_chemins(base)          # la 2e cellule de code porte les chemins
    espace = {"__name__": "__notebook__", "display": lambda *a, **k: None}
    for i, src in enumerate(code, start=1):
        try:
            exec(compile(src, f"<cellule {i}>", "exec"), espace)
        except Exception:
            print(f"\n=== ECHEC cellule de code {i} ===\n{src}")
            raise
    print(f"{len(code)} cellules de code executees sans erreur.")
    return espace


def verifier(espace):
    ok = True

    def check(nom, condition, detail=""):
        nonlocal ok
        ok = ok and bool(condition)
        print(f"  [{'OK ' if condition else 'KO '}] {nom}" + (f"  {detail}" if detail else ""))

    full = espace["full_data"]

    attendu = pd.date_range(full.index.min(), full.index.max(), freq="1h")
    check("grille horaire reguliere et complete", full.index.equals(attendu), f"{len(full)} pas")

    check("la chronique va jusqu'a la derniere mesure",
          full.index.max() >= FIN, f"jusqu'au {full.index.max():%d/%m/%Y %H:%M}")

    # Le piege principal : l'horodatage change en cours de chronique.
    for nom, quand in [("avant la bascule", BASCULE - pd.Timedelta(days=30)),
                       ("apres la bascule", BASCULE + pd.Timedelta(days=30)),
                       ("en fin de chronique", FIN - pd.Timedelta(days=2))]:
        fenetre = full.loc[quand:quand + pd.Timedelta(days=1), "Conductivité"]
        check(f"conductivite presente {nom}", fenetre.notna().any(),
              f"{int(fenetre.notna().sum())}/{len(fenetre)} pas")

    for col in espace["PARAMETRES"]:
        check(f"{col} numerique", pd.api.types.is_float_dtype(full[col]), str(full[col].dtype))

    tardif = full.loc[BASCULE:]
    check("les donnees recentes ne sont pas vides",
          tardif["Conductivité"].notna().mean() > 0.9,
          f"{tardif['Conductivité'].notna().mean():.1%} de pas renseignes")

    check("chlorophylle a zero conservee, pas ecartee",
          full["Chlorophylle_(RFU)"].notna().any(),
          f"{int(full['Chlorophylle_(RFU)'].notna().sum())} pas")

    # Le point de controle marque Oui est applique, l'autre non.
    d = pd.Timestamp("2025-06-12 10:00")
    i = HEURES.get_loc(d)
    attendu_cond = float(VERITE["cond"].to_numpy()[i]) + 25.0
    ecart = abs(float(full.loc[d, "Conductivité"]) - attendu_cond)
    check("serie calee sur le point de controle", ecart < 30.0,
          f"{full.loc[d, 'Conductivité']:.1f} attendu ~{attendu_cond:.1f}")

    check("statuts ecrits", all(f"Statut_{c}" in full for c in espace["PARAMETRES"]))
    return ok


if __name__ == "__main__":
    notebook = (sys.argv[1] if len(sys.argv) > 1
                else "Code pour consolider les données-Alzou.ipynb")
    base = Path(sys.argv[2] if len(sys.argv) > 2 else "jeu_de_test_alzou")
    print(f"Jeu de test dans {base}\n")
    fabriquer(base)
    espace = executer(notebook, base)
    print("\nVerifications :")
    sys.exit(0 if verifier(espace) else 1)
