################################################################################
# 05_build_panel.py
# Construction du panel commune × scrutin pour l'analyse DiD
# Input  : processed/{acv_communes, elections_panel, insee_panel}.parquet
# Output : processed/panel_final.parquet
#
# Structure du panel :
#   - code_insee (str)          : identifiant commune
#   - annee (int)               : année du scrutin
#   - scrutin (str)             : identifiant scrutin (pres2012, eur2019, ...)
#   - part_rn (float)           : part RN sur suffrages exprimés [0,1]
#   - traite (int 0/1)          : 1 = ville ACV
#   - post (int 0/1)            : 1 = scrutin >= 2018
#   - annee_traitement (int)    : 2018 pour traités, 0 pour contrôles (CS2021)
#   + covariates INSEE : population, rev_median, taux_chomage, part_cadres,
#                        part_ouvriers (valeurs pré-traitement, extrapolées si besoin)
################################################################################

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from setup import (PATHS, POP_MIN, POP_MAX, DEPT_EXCL_IDF_PC,
                   ANNEE_TRAITEMENT, SEED)

np.random.seed(SEED)
rng = np.random.default_rng(SEED)


def est_outremer(code: str) -> bool:
    if pd.isna(code):
        return False
    return str(code)[:2] in {"97", "98"}


def est_idf_pc(code: str) -> bool:
    if pd.isna(code):
        return False
    return str(code)[:2] in DEPT_EXCL_IDF_PC


# ── Chargement ────────────────────────────────────────────────────────────────

def charger_processed(nom: str) -> pd.DataFrame:
    p = PATHS["processed"] / f"{nom}.parquet"
    if not p.exists():
        raise FileNotFoundError(f"Fichier absent : {p}\n  → Exécuter les scripts précédents.")
    return pd.read_parquet(p)


# ── Interpolation/extrapolation covariates INSEE ──────────────────────────────

def interpoler_covariates(insee: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque commune, interpole/extrapole les covariates socio-démo
    vers les années de scrutin manquantes via forward/backward fill.
    Les données RP sont en millésimes 2012, 2014, 2016, 2018, 2020.
    On remplit les années manquantes par la valeur la plus proche.
    """
    if insee.empty:
        return insee

    covariates = ["population", "rev_median", "taux_chomage", "part_cadres", "part_ouvriers"]
    covariates_dispo = [c for c in covariates if c in insee.columns]

    if not covariates_dispo:
        return insee

    # Reindex par (code_insee, annee) et fill
    insee = insee.sort_values(["code_insee", "annee"])
    insee_interp = (
        insee.set_index(["code_insee", "annee"])[covariates_dispo]
        .groupby(level="code_insee")
        .apply(lambda g: g.interpolate(method="index").ffill().bfill())
        .reset_index()
    )
    return insee_interp


# ── Construction univers de contrôle ─────────────────────────────────────────

def construire_univers(elections: pd.DataFrame,
                       acv: pd.DataFrame,
                       insee: pd.DataFrame) -> pd.DataFrame:
    """
    1. Toutes les communes avec au moins un résultat électoral
    2. Filtre : taille 20k-100k (si pop disponible), hors OM, hors IDF-PC
    3. Ajoute indicatrice traité/contrôle
    """
    toutes_communes = elections["code_insee"].dropna().unique()
    df_communes = pd.DataFrame({"code_insee": toutes_communes})

    # Exclusions géographiques
    df_communes = df_communes[~df_communes["code_insee"].map(est_outremer)]
    df_communes = df_communes[~df_communes["code_insee"].map(est_idf_pc)]

    # Indicatrice ACV
    acv_codes = set(acv["code_insee"].dropna())
    df_communes["traite"] = df_communes["code_insee"].isin(acv_codes).astype(int)

    # Filtre taille population (si disponible)
    if not insee.empty and "population" in insee.columns:
        # Population de référence : année la plus proche de 2017 pré-traitement
        pop_ref = (
            insee[insee["annee"].between(2015, 2018)]
            .sort_values("annee", ascending=False)
            .drop_duplicates("code_insee")[["code_insee", "population"]]
        )
        df_communes = df_communes.merge(pop_ref, on="code_insee", how="left")

        # Garder : traitées ACV (quelle que soit taille — elles sont dans la cible)
        #          + contrôles dans strate 20k-100k
        masque_taille = (
            df_communes["traite"] == 1
        ) | (
            df_communes["population"].between(POP_MIN, POP_MAX)
        )
        n_avant = len(df_communes)
        df_communes = df_communes[masque_taille | df_communes["population"].isna()]
        print(f"  Filtre taille 20k–100k : {n_avant} → {len(df_communes)} communes")
        print(f"    (communes sans pop conservées provisoirement)")
    else:
        df_communes["population"] = np.nan
        print("  ⚠️  Population non disponible — filtre taille désactivé")

    n_traites  = df_communes["traite"].sum()
    n_controles = (df_communes["traite"] == 0).sum()
    print(f"  Groupe traité  : {n_traites} communes")
    print(f"  Groupe contrôle: {n_controles} communes")

    return df_communes


# ── Merge panel ───────────────────────────────────────────────────────────────

def construire_panel(communes: pd.DataFrame,
                     elections: pd.DataFrame,
                     insee: pd.DataFrame) -> pd.DataFrame:
    """
    Crée le panel long commune × scrutin avec toutes les variables.
    """
    # Panel électoral filtré sur les communes retenues
    codes_retenus = set(communes["code_insee"])
    elec = elections[elections["code_insee"].isin(codes_retenus)].copy()

    # Merge avec indicatrice traitement
    panel = elec.merge(
        communes[["code_insee", "traite"]],
        on="code_insee", how="left"
    )

    # Variable post-traitement
    panel["post"] = (panel["annee"] >= ANNEE_TRAITEMENT).astype(int)

    # Variable annee_traitement pour CS2021 :
    #   - traités : 2018
    #   - jamais traités : 0 (convention du package `differences`)
    panel["annee_traitement"] = np.where(panel["traite"] == 1, ANNEE_TRAITEMENT, 0)

    # Merge covariates INSEE (valeur de l'année la plus proche)
    if not insee.empty:
        cov_cols = [c for c in ["population", "rev_median", "taux_chomage",
                                 "part_cadres", "part_ouvriers"] if c in insee.columns]
        if cov_cols:
            insee_interp = interpoler_covariates(insee)
            panel = panel.merge(
                insee_interp[["code_insee", "annee"] + cov_cols],
                on=["code_insee", "annee"],
                how="left"
            )
    else:
        for col in ["rev_median", "taux_chomage", "part_cadres", "part_ouvriers"]:
            panel[col] = np.nan

    return panel


# ── Vérifications et statistiques du panel ────────────────────────────────────

def verifier_panel(panel: pd.DataFrame) -> None:
    print("\n  === Vérifications panel ===")

    # Balance : nombre de scrutins par commune
    n_scrutins = panel.groupby("code_insee")["scrutin"].count()
    print(f"  Scrutins par commune : min={n_scrutins.min()}, "
          f"median={n_scrutins.median():.0f}, max={n_scrutins.max()}")

    # Part RN manquante
    n_missing_rn = panel["part_rn"].isna().sum()
    pct = n_missing_rn / len(panel) * 100
    print(f"  part_rn manquant : {n_missing_rn}/{len(panel)} ({pct:.1f}%)")

    # Traités vs contrôles par scrutin
    tab = panel.groupby(["scrutin", "traite"])["part_rn"].agg(["mean", "count"]).round(3)
    print(f"\n  Statistiques part_rn par scrutin × traitement :\n{tab}")

    # Parallel trends visuels : pré-traitement
    pre = panel[panel["annee"] < 2018]
    diff_pre = (pre.groupby(["annee", "traite"])["part_rn"]
                .mean().unstack("traite").rename(columns={0: "controle", 1: "traite"}))
    if "traite" in diff_pre.columns and "controle" in diff_pre.columns:
        diff_pre["diff"] = diff_pre["traite"] - diff_pre["controle"]
        print(f"\n  Diff brute traité-contrôle (pré-traitement) :\n{diff_pre.round(4)}")

    # Taux de valeurs manquantes covariates
    for col in ["rev_median", "taux_chomage", "part_cadres", "part_ouvriers", "population"]:
        if col in panel.columns:
            pct_na = panel[col].isna().mean() * 100
            print(f"  {col:20s} : {pct_na:.1f}% manquant")


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 05_build_panel.py ===")

    acv       = charger_processed("acv_communes")
    elections = charger_processed("elections_panel")
    insee     = charger_processed("insee_panel")

    print(f"\n  ACV : {len(acv)} communes traitées")
    print(f"  Elections : {elections.shape[0]} obs, {elections['code_insee'].nunique()} communes")
    print(f"  INSEE : {insee.shape[0]} obs")

    print("\n  Construction univers communes...")
    communes = construire_univers(elections, acv, insee)

    print("\n  Construction panel long...")
    panel = construire_panel(communes, elections, insee)

    verifier_panel(panel)

    # Statistiques finales
    n_communes = panel["code_insee"].nunique()
    n_obs      = len(panel)
    n_traites  = panel[panel["traite"] == 1]["code_insee"].nunique()
    n_controles = panel[panel["traite"] == 0]["code_insee"].nunique()
    scrutins   = sorted(panel["scrutin"].unique())

    print(f"\n  ╔══════════════════════════════════════════════╗")
    print(f"  ║  PANEL FINAL                                 ║")
    print(f"  ║  Observations : {n_obs:>8}                    ║")
    print(f"  ║  Communes     : {n_communes:>8}                    ║")
    print(f"  ║    → Traitées : {n_traites:>8}                    ║")
    print(f"  ║    → Contrôle : {n_controles:>8}                    ║")
    print(f"  ║  Scrutins     : {len(scrutins):>8}                    ║")
    print(f"  ╚══════════════════════════════════════════════╝")

    dest = PATHS["processed"] / "panel_final.parquet"
    panel.to_parquet(dest, index=False)
    print(f"\n  Sauvegardé : {dest}")

    return panel


if __name__ == "__main__":
    main()
