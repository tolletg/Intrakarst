# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

__all__ = ["decaler", "ecarter", "lire_points", "caler", "raccorder", "raccorder_campagnes"]


def decaler(serie, date, valeur, sens="tout"):
    if sens == "tout":
        return serie + valeur
    if sens not in ("amont", "aval"):
        raise ValueError(f"sens attendu : 'amont', 'aval' ou 'tout', recu {sens!r}")
    date = pd.to_datetime(date)
    m = np.asarray(serie.index >= date if sens == "aval" else serie.index < date)
    return serie.where(~m, serie + valeur)


def ecarter(df, voies_ecartees):
    for entree in voies_ecartees:
        if len(entree) != 4:
            raise ValueError(f"VOIES_ECARTEES attend (début, fin, colonne, motif), "
                             f"reçu {entree!r}")
        debut, fin, col, motif = entree
        if col not in df.columns:
            raise ValueError(f"VOIES_ECARTEES : colonne inconnue {col!r}")
        debut, fin = sorted([pd.to_datetime(debut), pd.to_datetime(fin)])
        m = np.asarray((df.index >= debut) & (df.index <= fin))
        print(f"  {debut:%d/%m/%Y %H:%M} - {fin:%d/%m/%Y %H:%M}  {col} : "
              f"{int((m & df[col].notna().to_numpy()).sum())} pas écartés ({motif})")
        df[col] = df[col].mask(m)
    return df


def lire_points(chemin, col_jour="Jour"):
    points = pd.read_excel(chemin)
    points["Datetime"] = pd.to_datetime(points[col_jour], dayfirst=True, errors="coerce")
    return points


def caler(serie, points, col_valeur, tolerance_h=1):
    for _, l in points.dropna(subset=["Datetime"]).sort_values("Datetime").iterrows():
        date, cible = l["Datetime"], l.get(col_valeur)
        if pd.isna(cible) or str(l.get("Correction", "Non")).strip() != "Oui":
            continue
        mesures = serie.dropna()
        i = (mesures.index[np.abs((mesures.index - date).to_numpy()).argmin()]
             if len(mesures) else None)
        if i is None or abs((i - date).total_seconds()) > tolerance_h * 3600:
            print(f"  {date:%d/%m/%Y %H:%M} : ignoré, pas de mesure à moins de {tolerance_h} h")
            continue
        d = float(cible) - float(serie.loc[i])
        print(f"  {date:%d/%m/%Y %H:%M} : {float(serie.loc[i]):.1f} vers {float(cible):.1f}, "
              f"décalage {d:+.2f} appliqué vers l'aval")
        serie = decaler(serie, date, d, "aval")
    return serie


def raccorder(ancienne, nouvelle, transition, sonde, unite="", trou_max_h=12, fenetre_h=24):
    a = ancienne[ancienne.index <= transition].dropna()
    b = nouvelle[nouvelle.index >= transition].dropna()
    if not len(a) or not len(b):
        d, note = 0.0, "pas de mesure de part et d'autre, aucun recalage"
    else:
        trou = (b.index[0] - a.index[-1]).total_seconds() / 3600
        if trou <= trou_max_h:
            d = float(a.iloc[-1] - b.iloc[0])
            note = (f"{a.iloc[-1]:.2f} vers {b.iloc[0]:.2f} "
                    f"le {b.index[0]:%d/%m/%Y %H:%M}"
                    + (f", après {trou:.0f} h de trou" if trou >= 1 else ""))
        else:
            d, note = 0.0, f"trou {trou:.0f} h, pas de recalage"
    print(f"  {sonde:6s} {d:+9.2f} {unite:6s} {note}")
    return d
    
def raccorder_campagnes(ancien, nouveau, grandeurs, jours=7, fenetre_h=1, tracer=True):

    import matplotlib.pyplot as plt

    fin_ancien, debut_nouveau = ancien["DATE"].max(), nouveau["DATE"].min()
    print(f"Dernière date des anciennes données : {fin_ancien:%d/%m/%Y %H:%M}")
    print(f"Première date des nouvelles données : {debut_nouveau:%d/%m/%Y %H:%M}")

    for nom, col_a, col_n, unite in grandeurs:
        a = ancien.set_index("DATE")[col_a].dropna()
        n = nouveau.set_index("DATE")[col_n].dropna()
        communs = a.index.intersection(n.index)
        if len(communs):
            fin = communs.max()
            proches = communs[communs > fin - pd.Timedelta(hours=fenetre_h)]
            d = float((a[proches] - n[proches]).median())
            note = (f"jonction au {fin:%d/%m/%Y %H:%M}"
                    + (f", médiane sur {len(proches)} h" if len(proches) > 1 else ""))
        elif len(a) and len(n):
            d = float(a.iloc[-1] - n.iloc[0])
            note = (f"{a.index[-1]:%d/%m/%Y %H:%M} vers {n.index[0]:%d/%m/%Y %H:%M}, "
                    f"trou de {(n.index[0] - a.index[-1]).total_seconds() / 3600:.0f} h")
        else:
            print(f"{nom:13s} :     aucun raccord possible, série vide")
            continue
        print(f"{nom:13s} : {d:+9.2f} {unite:6s} {note}")
        nouveau[col_n] = nouveau[col_n] + d

    if not tracer:
        return nouveau
    marge = pd.Timedelta(days=jours)
    debut, fin = fin_ancien - marge, fin_ancien + marge

    fig, ax1 = plt.subplots(figsize=(11, 2))
    axes = [ax1] + ([ax1.twinx()] if len(grandeurs) > 1 else [])
    for ax, (nom, col_a, col_n, unite), (c_a, c_n) in zip(
            axes, grandeurs, [("green", "blue"), ("orange", "red")]):
        s_a = ancien.set_index("DATE")[col_a].dropna().sort_index().loc[debut:fin]
        s_n = (nouveau.set_index("DATE")[col_n].dropna().sort_index()
               .loc[fin_ancien:fin])                    # seulement ce qui est retenu
        ax.plot(s_a.index, s_a.to_numpy(), color=c_a, label=f"{nom} (consolidé)")
        ax.plot(s_n.index, s_n.to_numpy(), color=c_n, label=f"{nom} (nouveau, corrigé)")
        ax.set_ylabel(f"{nom} ({unite})")
        ax.tick_params(axis="y")
    ax1.set_xlim(debut, fin)
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.10), ncol=4)
    plt.tight_layout()
    plt.show()
    return nouveau
    
    n_corr = nouveau[nouveau["DATE"] <= debut_nouveau + fenetre]   # apres correction
    fig, ax1 = plt.subplots(figsize=(11, 3))
    nom, col_a, col_n, unite = grandeurs[0]
    ax1.plot(a_pres["DATE"], a_pres[col_a], color="green", label=f"{nom} (consolidé)")
    ax1.plot(n_corr["DATE"], n_corr[col_n], color="blue", label=f"{nom} (nouveau, corrigé)")
    ax1.set_ylabel(f"{nom} ({unite})")
    if len(grandeurs) > 1:
        nom2, col_a2, col_n2, unite2 = grandeurs[1]
        ax2 = ax1.twinx()
        ax2.plot(a_pres["DATE"], a_pres[col_a2], color="orange", label=f"{nom2} (consolidé)")
        ax2.plot(n_corr["DATE"], n_corr[col_n2], color="red", label=f"{nom2} (nouveau, corrigé)")
        ax2.set_ylabel(f"{nom2} ({unite2})")
    fig.legend(loc="upper center", bbox_to_anchor=(0.5, 1.12), ncol=4)
    plt.tight_layout()
    plt.show()
    return nouveau
