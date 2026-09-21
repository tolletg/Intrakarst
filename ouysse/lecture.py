# -*- coding: utf-8 -*-
"""Lecture des exports bruts : CTD Diver, Aqua TROLL (VuSitu), centrale OTT.

Chaque fonction encapsule les pieges du format correspondant. Le notebook ne
garde que les chemins et le prefixe des campagnes.
"""
import os
import re
import unicodedata
from io import StringIO

import numpy as np
import pandas as pd

__all__ = ["fichiers", "lire_CTD", "lire_VuSitu", "lire_OTT", "en_utc",
           "appliquer_gammes", "NOMS_TROLL", "NOMS_OTT", "NOMS_OTT_CTD", "GAMMES",
           "HPA_EN_CMH2O"]

#: 1 hPa = 1.019716 cmH2O, pour la compensation barometrique.
HPA_EN_CMH2O = 1.019716


def _sans_accents(t):
    d = unicodedata.normalize("NFKD", str(t))
    return "".join(c for c in d if not unicodedata.combining(c)).lower()


def _lire_lignes(chemin):
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            with open(chemin, "r", encoding=enc) as f:
                return f.read().splitlines(), enc
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Aucun encodage ne convient pour {chemin}")


def _en_datetime(serie):
    """Garde le format qui convertit le plus de lignes."""
    txt = serie.astype("string").str.strip()
    meilleur, n_ok = None, -1
    for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        e = pd.to_datetime(txt, format=fmt, errors="coerce")
        if e.notna().sum() > n_ok:
            meilleur, n_ok = e, e.notna().sum()
    if n_ok < txt.notna().sum():             # des lignes non vides resistent : lecture libre
        libre = pd.to_datetime(txt, format="mixed", errors="coerce", dayfirst=True)
        meilleur = libre if libre.notna().sum() > n_ok else meilleur
    return meilleur


def fichiers(path, motif):
    """Fichiers du dossier contenant `motif`, tries par numero."""
    noms = [f for f in os.listdir(path)
            if motif.lower() in f.lower() and f.lower().endswith((".csv", ".txt", ".mon"))]
    return sorted(noms, key=lambda n: (int(re.findall(r"\d+", n)[0])
                                       if re.findall(r"\d+", n) else 10 ** 9, n))


def lire_CTD(nom, path, pas="1h"):
    """Export Diver : en-tete cherchee par contenu, pied END OF DATA reconnu,
    conductivite convertie d'apres l'unite entre crochets."""
    chemin = os.path.join(path, nom)
    lignes, encodage = _lire_lignes(chemin)
    entete = next((i for i, l in enumerate(lignes[:200])
                   if _sans_accents(l).lstrip("﻿").startswith("date/time")), None)
    if entete is None:
        raise ValueError(f"En-tête 'Date/time' introuvable dans {nom}")

    df = pd.read_csv(chemin, sep=";", encoding=encodage, skiprows=entete, dtype=str,
                     engine="python")
    df.columns = [c.strip() for c in df.columns]
    col = df.columns[0]
    brut = df[col].astype("string")
    fin = brut.map(lambda v: pd.notna(v) and "end of data" in _sans_accents(v)).fillna(False)
    df = df.loc[~(fin | brut.isna() | (brut.str.strip() == ""))].copy()

    df["Date/time"] = _en_datetime(df[col]).dt.round(pas)
    for c in df.columns:
        if c not in ("Date/time", col):
            df[c] = pd.to_numeric(df[c].astype("string").str.strip()
                                  .str.replace(",", ".", regex=False), errors="coerce")
    for c in list(df.columns):
        if "cond" in _sans_accents(c):
            u = re.search(r"\[([^\]]*)\]", c)
            df[c] = df[c] * (1000.0 if u and _sans_accents(u.group(1)).startswith("ms/cm") else 1.0)
            df = df.rename(columns={c: "Cond_(µS/cm)"})
            break
    return df.loc[df["Date/time"].notna()].sort_values("Date/time")


#: Libelles VuSitu (sans numero de serie, sans accent) vers les noms du projet.
NOMS_TROLL = {
    "conductivite specifique (us/cm)":        "Cond_Troll_(µS/cm)",
    "temperature (c)":                        "température_Troll_(°C)",
    "turbidite (ntu)":                        "Turbidity_Troll_(NTU)",
    "concentration rdo (mg/l)":               "O2_Troll_(mg/l)",
    "saturation rdo (%sat)":                  "O2 (%Sat)",
    "fluorescence de chlorophylle-a (rfu)":   "FluorescenceChloro_a_Troll_(RFU)",
    "concentration de chlorophylle-a (ug/l)": "ConcentrationChloro_a_(µg/l)",
}


def lire_VuSitu(nom, path, pas="1h", noms=None):
    """Export VuSitu : guillemets retires, numero de serie retire par regex."""
    noms = NOMS_TROLL if noms is None else noms
    lignes, _ = _lire_lignes(os.path.join(path, nom))
    df = pd.read_csv(StringIO("\n".join(l.replace('"', "") for l in lignes)), sep=",")
    cle = lambda c: (_sans_accents(re.sub(r"\s*\(\d{4,}\)\s*$", "", str(c)).strip())
                     .replace("μ", "u").replace("µ", "u").replace("°", ""))
    col = next((c for c in df.columns if "date" in _sans_accents(c)), df.columns[0])
    df["DATE"] = _en_datetime(df[col]).dt.round(pas)
    return df.drop(columns=[col]).rename(
        columns={c: noms[cle(c)] for c in df.columns if cle(c) in noms})


#: Voies de la centrale. level, C1, T1 = SA sonde CTD.
#: C2, T2, Turbi, O2, Chlorophyl = le TROLL rapatrie, donc un doublon.
NOMS_OTT = {"level": "Niveau_CTDOTT_(cm)",
            "c1": "Cond_CTDOTT_(µS/cm)",   "t1": "Temp_CTDOTT_(°C)",
            "c2": "Cond_TrollOTT_(µS/cm)", "t2": "Temp_TrollOTT_(°C)",
            "turbi": "Turbidity_TrollOTT_(NTU)", "o2": "O2_TrollOTT_(mg/l)",
            "chlorophyl": "FluorescenceChloro_a_TrollOTT_(RFU)"}

#: Station sans TROLL : la centrale ne rapatrie que sa propre sonde CTD.
NOMS_OTT_CTD = {c: NOMS_OTT[c] for c in ("level", "c1", "t1")}


def lire_OTT(nom, path, noms=None, pas="1h"):
    """Centrale, deja en UTC : -99999 = absence, horodatages en double departages."""
    noms = NOMS_OTT if noms is None else noms
    chemin = os.path.join(path, nom)
    _, encodage = _lire_lignes(chemin)
    df = pd.read_csv(chemin, sep=";", encoding=encodage, dtype=str, engine="python")
    df.columns = [c.strip() for c in df.columns]
    col = df.columns[0]
    df["DATE"] = _en_datetime(df[col]).dt.round(pas)
    df = df.drop(columns=[col])
    for c in df.columns:
        if c != "DATE":
            df[c] = pd.to_numeric(df[c].astype("string").str.strip()
                                  .str.replace(",", ".", regex=False), errors="coerce")
            df.loc[df[c].isin([-99999, -9999, 9999]), c] = np.nan
    df = df.rename(columns={c: noms[c.lower()] for c in df.columns if c.lower() in noms})
    return df.dropna(subset=["DATE"]).groupby("DATE", as_index=False).median(numeric_only=True)


def en_utc(df, nom, metadata, col_date="Date/time", col_utc="UTC Fichier"):
    """Ramene les horodatages en UTC. Correspondance EXACTE sur le nom du
    fichier : sinon la campagne est ignoree et le message la nomme."""
    ligne = metadata.loc[metadata["Nom fichier"] == nom, col_utc]
    if ligne.empty:
        raise ValueError(f"'{nom}' absent de la colonne 'Nom fichier'. "
                         f"À corriger dans la table UTC.")
    v = ligne.values[0]
    m = re.search(r"([+-]?\d+(?:[.,]\d+)?)", str(v))
    decalage = float(v) if isinstance(v, (int, float, np.number)) and pd.notna(v) else (
        float(m.group(1).replace(",", ".")) if m else 0.0)
    df = df.copy()
    df[col_date] = df[col_date] - pd.Timedelta(hours=decalage)
    return df, decalage


#: Gamme physique par mot-cle de nom de colonne. Le niveau est compense du baro
#: mais PAS ENCORE cale : sa valeur n'a pas d'origine absolue, d'ou des bornes
#: larges, qui ne servent qu'a ecarter l'absurde (sonde hors d'eau, defaut de
#: lecture), pas a juger de la vraisemblance hydrologique.
GAMMES = {"niveau": (-50, 1000), "cond": (100, 5000), "temp": (-2, 30),
          "turbid": (0, 4000), "o2": (1, 25), "chloro": (1, 500)}

def appliquer_gammes(df, gammes=None):
    """Met a NaN ce qui est physiquement impossible, voie par voie."""
    gammes = GAMMES if gammes is None else gammes
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        for cle, (mini, maxi) in gammes.items():
            if cle in _sans_accents(col):
                hors = (df[col] < mini) | (df[col] > maxi)
                if hors.any():
                    print(f"  {col:36s} {int(hors.sum()):6d} hors [{mini}, {maxi}]")
                    df.loc[hors, col] = np.nan
                break
    return df
