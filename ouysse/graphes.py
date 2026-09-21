# -*- coding: utf-8 -*-
"""Graphes de controle. Plotly pour l'interactif, matplotlib pour la synthese."""
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go

__all__ = ["COULEURS", "graphe", "graphe_sondes", "graphe_statuts", "graphe_synthese"]

#: Couleur de chaque sonde, la meme sur tous les graphes.
COULEURS = {"OTT": "#1f77b4", "TROLL": "#d62728", "CTD": "#2ca02c"}


def graphe(traces, titre="", ylab="", points=None, col_point=None):
    """`traces` = liste de (serie, nom, couleur). Scattergl : une chronique
    horaire pluriannuelle s'affiche sans saturer le navigateur."""
    fig = go.Figure()
    for serie, nom, couleur in traces:
        fig.add_trace(go.Scattergl(x=serie.index, y=serie, mode="lines", name=nom,
                                   line=dict(color=couleur, width=1.3)))
    if points is not None and col_point in points.columns:
        corr = points.get("Correction", pd.Series("Non", index=points.index))
        fig.add_trace(go.Scattergl(
            x=points["Datetime"], y=points[col_point], mode="markers", name="points de contrôle",
            marker=dict(symbol="x", size=10,
                        color=["red" if str(v).strip() == "Oui" else "royalblue" for v in corr])))
    fig.update_layout(title=titre, xaxis_title="Date", yaxis_title=ylab,
                      template="plotly_white", hovermode="x unified")
    fig.show()


def graphe_sondes(voies, fusion=None, corrigee=None, titre="", ylab="",
                  points=None, col_point=None):
    """Les sondes telles qu'elles entrent dans la fusion, puis le resultat.

    Les ecarts visibles entre sondes sont ceux dont il faut tenir compte pour
    ecrire une periode imposee.
    """
    traces = [(serie, f"sonde {sonde}", COULEURS.get(sonde)) for sonde, serie in voies.items()]
    if fusion is not None:
        traces.append((fusion, "fusion, avant correction", "lightgrey"))
    if corrigee is not None:
        traces.append((corrigee, "chronique corrigée", "black"))
    graphe(traces, titre=titre, ylab=ylab or titre, points=points, col_point=col_point)


def graphe_statuts(full_data, colonnes):
    """Un parametre a la fois, choisi dans le menu : mesure en noir, interpole
    en rouge. Les trous laisses ouverts restent vides."""
    fig = go.Figure()
    for p in colonnes:
        for nom, couleur in [("Mesurée", "lightgrey"), ("Interpolée", "crimson")]:
            m = (full_data[f"Statut_{p}"] == nom).to_numpy()
            fig.add_trace(go.Scattergl(x=full_data.index[m], y=full_data[p][m], mode="markers",
                                       name=nom, marker=dict(color=couleur, size=3),
                                       visible=(p == colonnes[0])))
    fig.update_layout(
        updatemenus=[dict(buttons=[dict(label=p, method="update",
                                        args=[{"visible": [q == p for q in colonnes for _ in (0, 1)]},
                                              {"yaxis.title.text": p}])
                                   for p in colonnes],
                          x=0, xanchor="left", y=1.18)],
        title="Statut des données", xaxis_title="Date", yaxis_title=colonnes[0],
        template="plotly_white", hovermode="x unified")
    fig.show()
    print(pd.DataFrame({p: full_data[f"Statut_{p}"].value_counts() for p in colonnes})
          .fillna(0).astype(int).T.to_string())


def graphe_synthese(full_data, principal, label_principal, pluie=None, sortie=None,
                    marge_jours=0):
    """Trois panneaux : le parametre hydrologique et la pluie, la conductivite
    et la temperature, puis turbidite, oxygene et chlorophylle si la station
    les mesure (deux panneaux sinon).

    L'axe des dates est cale sur la plage ou le NIVEAU existe, eventuellement
    elargie de `marge_jours` : sans cela le fichier de pluie, trace en entier,
    etire le graphe bien au-dela de la chronique.
    """
    optionnels = [c for c in ("Turbidité_(NTU)", "O2_(mg/l)", "Chlorophylle_(RFU)")
                  if c in full_data]
    mesure = full_data["Niveau_(cm)"].dropna()
    marge = pd.Timedelta(days=marge_jours)
    debut, fin = mesure.index.min() - marge, mesure.index.max() + marge

    n = 3 if optionnels else 2
    fig, axes = plt.subplots(n, 1, figsize=(15, 10 if n == 3 else 7), sharex=True,
                             gridspec_kw={"hspace": 0.05})

    axes[0].plot(full_data.index,
                 full_data[principal].rolling(12, center=True, min_periods=1).mean(),
                 color="lightseagreen")
    axes[0].set_ylabel(label_principal, color="lightseagreen")
    axes[0].tick_params(axis="y", labelcolor="lightseagreen")
    if pluie and os.path.exists(pluie):
        p = pd.read_csv(pluie)
        p["Date"] = pd.to_datetime(p["Date"], errors="coerce")
        p = p[p["Date"].between(debut, fin)]
        ax = axes[0].twinx()
        ax.bar(p["Date"], p["Precipitation (mm)"], width=0.8, color="royalblue")
        ax.invert_yaxis()
        ax.set_ylabel("Précipitations (mm)", color="royalblue")
        ax.tick_params(axis="y", labelcolor="royalblue")

    axes[1].plot(full_data.index, full_data["Conductivité_Moyenne_Mobile"], color="black")
    axes[1].set_ylabel("Conductivité (µS/cm)")
    ax = axes[1].twinx()
    ax.plot(full_data.index,
            full_data["Température"].rolling(12, center=True, min_periods=1).mean(),
            color="crimson")
    ax.set_ylabel("Température (°C)", color="crimson")
    ax.tick_params(axis="y", labelcolor="crimson")

    if optionnels:
        axes[2].plot(full_data.index,
                     full_data["Turbidité_(NTU)"].rolling(24, center=True, min_periods=1).mean(),
                     color="darkorange")
        axes[2].set_ylabel("Turbidité (NTU)", color="darkorange")
        axes[2].tick_params(axis="y", labelcolor="darkorange")
        axes[2].set_ylim(0, 100)
        ax = axes[2].twinx()
        ax.plot(full_data.index,
                full_data["O2_(mg/l)"].rolling(24, center=True, min_periods=1).mean(),
                color="darkmagenta")
        ax.set_ylabel("Oxygène (mg/L)", color="darkmagenta")
        ax.tick_params(axis="y", labelcolor="darkmagenta")
        ax = axes[2].twinx()
        ax.spines["right"].set_position(("outward", 45))
        ax.plot(full_data.index,
                full_data["Chlorophylle_(RFU)"].rolling(24, center=True, min_periods=1).mean(),
                color="green")
        ax.set_ylabel("Chlorophylle (RFU)", color="green")
        ax.tick_params(axis="y", labelcolor="green")

    axes[0].set_xlim(debut, fin)          # sharex : les autres panneaux suivent
    if sortie:
        plt.savefig(sortie, format="svg")
    plt.show()