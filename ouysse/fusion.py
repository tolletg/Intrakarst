# -*- coding: utf-8 -*-
"""Assemblage des voies, choix de la sonde, fusion et post-traitement."""
import numpy as np
import pandas as pd

from .correction import raccorder

__all__ = ["empiler", "sur_grille", "reunir_doublons", "choisir_sondes", "fusionner",
           "filtre_iqr", "interpoler_avec_statut"]


def empiler(files, colonnes):
    """Empile plusieurs sources d'une meme sonde, un enregistrement par pas.

    Les campagnes se recouvrent : la premiere du tri stable gagne.
    """
    pile = pd.concat(files, ignore_index=True).dropna(subset=["DATE"])
    pile = pile[["DATE"] + [c for c in colonnes if c in pile.columns]]
    return (pile.sort_values("DATE", kind="stable")
            .drop_duplicates("DATE", keep="first").set_index("DATE"))


def sur_grille(piles, pas="1h"):
    """Une colonne par voie sur une grille de temps reguliere et complete."""
    grille = pd.date_range(min(p.index.min() for p in piles),
                           max(p.index.max() for p in piles), freq=pas, name="DATE")
    full_data = pd.DataFrame(index=grille)
    for pile in piles:
        for col in pile.columns:
            full_data[col] = pile[col].reindex(grille)
    print(f"{len(full_data)} pas de {pas}, du {grille.min():%d/%m/%Y} au {grille.max():%d/%m/%Y}")
    return full_data


def reunir_doublons(df, doublons):
    """Deux chemins d'acquisition du MEME capteur : (voie directe, voie relayee).

    Le direct est prioritaire, le relais ne comble que ses trous, sans recalage.
    """
    for direct, relais in doublons:
        if direct not in df.columns or relais not in df.columns:
            continue
        trou = (df[direct].isna() & df[relais].notna()).to_numpy()
        df[direct] = df[direct].where(~trou, df[relais])
        print(f"  {direct:34s} {int(trou.sum()):6d} pas")
    return df


def choisir_sondes(voies, ordre, periodes_imposees=(), duree_mini_h=12):
    """Decoupe la chronique en periodes (debut, fin, sonde).

    A chaque pas, la premiere sonde disponible de `ordre`. Sur une periode
    imposee (debut, fin, sonde), la sonde nommee passe en tete la ou elle
    mesure. Un bloc plus court que `duree_mini_h` est absorbe par le
    precedent : on ne change pas de sonde pour boucher un trou de quelques
    heures, c'est l'interpolation qui s'en charge.
    """
    index = next(iter(voies.values())).index
    choix = pd.Series(pd.NA, index=index, dtype="object")
    for sonde in [s for s in ordre if s in voies] + [s for s in voies if s not in ordre]:
        choix = choix.where(choix.notna() | voies[sonde].isna(), sonde)
    for entree in periodes_imposees:
        if len(entree) != 3:
            raise ValueError(f"Une période imposée attend (début, fin, sonde), reçu {entree!r}")
        debut, fin, sonde = entree
        if sonde not in voies:
            raise ValueError(f"Période imposée : sonde inconnue {sonde!r} "
                             f"(attendu : {', '.join(voies)})")
        d, f = pd.to_datetime(debut), pd.to_datetime(fin)
        if f < d:
            raise ValueError(f"Période imposée {sonde} : fin ({fin}) antérieure au début ({debut})")
        p = np.asarray((index >= d) & (index <= f))
        choix = choix.where(~(p & voies[sonde].notna().to_numpy()), sonde)

    choix, blocs = choix.dropna(), []
    mini = pd.Timedelta(hours=duree_mini_h)
    for _, g in choix.groupby((choix != choix.shift()).cumsum()):
        if blocs and (g.iloc[0] == blocs[-1][2] or g.index[-1] - g.index[0] < mini):
            blocs[-1][1] = g.index[-1]
        else:
            blocs.append([g.index[0], g.index[-1], g.iloc[0]])
    return [tuple(b) for b in blocs]


def fusionner(voies, periodes, unite="", trou_max_h=12, fenetre_h=24):
    """Chronique d'une grandeur. `voies` = {sonde: serie}.

    Chaque periode n'utilise QUE sa sonde : aucune autre ne vient combler ses
    lacunes. A chaque changement de sonde, la nouvelle est recalee sur la
    precedente A LA JONCTION, en cascade depuis la premiere periode, qui fixe
    le zero.
    """
    index = next(iter(voies.values())).index
    valeur = pd.Series(np.nan, index=index)
    source = pd.Series(pd.NA, index=index, dtype="object")
    decalage, precedente = 0.0, None
    for debut, fin, sonde in periodes:
        transition = pd.to_datetime(debut)
        p = np.asarray((index >= transition) & (index <= pd.to_datetime(fin)))
        serie = voies[sonde]
        print(f"  {transition:%d/%m/%Y %H:%M} - {pd.to_datetime(fin):%d/%m/%Y %H:%M}  {sonde}")
        if precedente is not None and sonde != precedente:
            decalage = raccorder(voies[precedente] + decalage, serie, transition,
                                 sonde, unite, trou_max_h, fenetre_h)
        pris = p & serie.notna().to_numpy()
        valeur[pris], source[pris] = serie[pris] + decalage, sonde
        precedente = sonde
    return valeur, source


def filtre_iqr(serie, fenetre="48h", k=1.5, min_periods=8, lissage_h=0):
    """Ecarte ce qui sort de [Q1 - k.IQR, Q3 + k.IQR] sur fenetre glissante
    centree, puis lisse a la mediane si `lissage_h`. `k = 0` : pas de filtre.
    """
    hors = pd.Series(False, index=serie.index)
    if k:
        r = serie.rolling(fenetre, center=True, min_periods=min_periods)
        q1, q3 = r.quantile(0.25), r.quantile(0.75)
        hors = ((serie < q1 - k * (q3 - q1)) | (serie > q3 + k * (q3 - q1))).fillna(False)
    nette = serie.mask(hors)
    print(f"Filtre IQR ({fenetre}, k={k}) : {int(hors.sum())} valeurs écartées")
    if lissage_h:
        nette = nette.rolling(f"{lissage_h}h", center=True, min_periods=1).median()
        print(f"Lissage : médiane glissante sur {lissage_h} h")
    return nette


def interpoler_avec_statut(df, colonnes, max_trou_h=12, pas="1h"):
    """Comble les lacunes de moins de `max_trou_h` et trace l'origine de chaque
    valeur dans `Statut_<colonne>` : Mesuree, Interpolee ou Manquante.
    """
    max_pas = int(pd.Timedelta(f"{max_trou_h}h") / pd.Timedelta(pas))
    for col in colonnes:
        origine = df[col]
        manquant = origine.isna().to_numpy()
        groupe = np.cumsum(np.r_[True, manquant[1:] != manquant[:-1]])
        tailles = pd.Series(groupe).groupby(groupe).transform("size").to_numpy()
        comble = origine.interpolate(method="time", limit_direction="both")
        comble = comble.mask(manquant & (tailles > max_pas))
        mesures = np.flatnonzero(~manquant)        # pas d'extrapolation hors plage mesuree
        if mesures.size:
            comble.iloc[:mesures[0]] = origine.iloc[:mesures[0]]
            comble.iloc[mesures[-1] + 1:] = origine.iloc[mesures[-1] + 1:]
        df[col] = comble
        df[f"Statut_{col}"] = np.where(
            ~manquant, "Mesurée", np.where(comble.notna().to_numpy(), "Interpolée", "Manquante"))
    return df
