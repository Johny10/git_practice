################################################################################
# 06_descriptive.py
# Statistiques descriptives, Table 1 (balance), Figure 1 (tendances brutes),
# Carte 1 (localisation des villes ACV)
################################################################################

import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from scipy import stats

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, SCRUTINS, SEED

np.random.seed(SEED)

FONT = {"family": "DejaVu Sans", "size": 10}
matplotlib.rc("font", **FONT)
plt.rcParams.update({
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
})


def charger_panel() -> pd.DataFrame:
    p = PATHS["processed"] / "panel_final.parquet"
    if not p.exists():
        raise FileNotFoundError("panel_final.parquet absent — exécuter 05_build_panel.py")
    return pd.read_parquet(p)


# ── Table 1 : Balance pré-traitement ─────────────────────────────────────────

def table_balance(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Compare les communes traitées vs contrôles sur les variables pré-traitement.
    Calcule différence de moyennes + test de Welch.
    """
    covariates = {
        "population":    "Population (hab.)",
        "rev_median":    "Revenu médian par UC (€)",
        "taux_chomage":  "Taux de chômage (%)",
        "part_cadres":   "Part cadres (%)",
        "part_ouvriers": "Part ouvriers (%)",
        "part_rn":       "Vote RN moyen pré-traitement (%)",
    }

    # Utiliser la moyenne des scrutins pré-traitement pour le vote RN
    pre = panel[panel["annee"] < 2018].copy()
    pre_agg = (pre.groupby("code_insee")
               .agg(part_rn=("part_rn", "mean"),
                    traite=("traite", "first"),
                    population=("population", "first"),
                    rev_median=("rev_median", "first"),
                    taux_chomage=("taux_chomage", "first"),
                    part_cadres=("part_cadres", "first"),
                    part_ouvriers=("part_ouvriers", "first"))
               .reset_index())

    rows = []
    for col, label in covariates.items():
        if col not in pre_agg.columns:
            continue
        t = pre_agg[pre_agg["traite"] == 1][col].dropna()
        c = pre_agg[pre_agg["traite"] == 0][col].dropna()
        if len(t) < 2 or len(c) < 2:
            continue
        stat, pval = stats.ttest_ind(t, c, equal_var=False)
        rows.append({
            "Variable":    label,
            "ACV (N={})".format(len(t)):          f"{t.mean():.3f}",
            "Contrôle (N={})".format(len(c)):     f"{c.mean():.3f}",
            "Différence":  f"{t.mean()-c.mean():.3f}",
            "p-value":     f"{pval:.3f}",
        })

    df_bal = pd.DataFrame(rows)
    print("\n  Table 1 — Balance pré-traitement :")
    print(df_bal.to_string(index=False))

    # Export LaTeX
    latex = df_bal.to_latex(
        index=False, escape=True,
        caption="Balance pré-traitement : ACV vs non-ACV",
        label="tab:balance",
        column_format="l" + "r" * (len(df_bal.columns) - 1)
    )
    dest = PATHS["tables"] / "table1_balance.tex"
    dest.write_text(latex)
    print(f"  → {dest}")

    return df_bal


# ── Figure 1 : Tendances brutes part RN ──────────────────────────────────────

def figure_tendances_brutes(panel: pd.DataFrame) -> None:
    # Scritus avec annee numérique (pour abscisse)
    # Présidentielles + européennes (exclure législatives pour cohérence)
    scrutins_plot = ["pres2012", "eur2014", "pres2017", "eur2019", "pres2022", "eur2024"]
    df = panel[panel["scrutin"].isin(scrutins_plot)].copy()

    moyennes = (df.groupby(["scrutin", "annee", "traite"])["part_rn"]
                .agg(["mean", "sem"]).reset_index())
    moyennes.columns = ["scrutin", "annee", "traite", "mean_rn", "sem_rn"]

    t = moyennes[moyennes["traite"] == 1].sort_values("annee")
    c = moyennes[moyennes["traite"] == 0].sort_values("annee")

    fig, ax = plt.subplots(figsize=(8, 5))

    ax.plot(t["annee"], t["mean_rn"] * 100, "o-", color="black",
            linewidth=2, markersize=6, label="Villes ACV (traitées)")
    ax.fill_between(t["annee"],
                    (t["mean_rn"] - 1.96 * t["sem_rn"]) * 100,
                    (t["mean_rn"] + 1.96 * t["sem_rn"]) * 100,
                    alpha=0.15, color="black")

    ax.plot(c["annee"], c["mean_rn"] * 100, "s--", color="gray",
            linewidth=2, markersize=6, label="Villes non-ACV (contrôle)")
    ax.fill_between(c["annee"],
                    (c["mean_rn"] - 1.96 * c["sem_rn"]) * 100,
                    (c["mean_rn"] + 1.96 * c["sem_rn"]) * 100,
                    alpha=0.10, color="gray")

    ax.axvline(x=2018, color="black", linestyle=":", linewidth=1.2, alpha=0.7)
    ax.text(2018.1, ax.get_ylim()[1] * 0.95, "ACV\n(2018)", fontsize=8, va="top")

    ax.set_xlabel("Année")
    ax.set_ylabel("Part RN/FN (% suffrages exprimés)")
    ax.set_title("Évolution brute du vote RN : villes ACV vs non-ACV", fontsize=11)
    ax.legend(frameon=False)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
    ax.set_xticks(sorted(df["annee"].unique()))

    plt.tight_layout()
    dest = PATHS["figures"] / "fig1_raw_trends.pdf"
    fig.savefig(dest)
    plt.close(fig)
    print(f"  → {dest}")


# ── Carte 1 : Localisation des villes ACV ────────────────────────────────────

def carte_acv(panel: pd.DataFrame) -> None:
    try:
        import geopandas as gpd
    except ImportError:
        print("  ⚠️  geopandas non disponible — carte non générée")
        return

    # Chercher un shapefile France communes dans data/raw/geo
    shp_candidats = (
        list(PATHS["raw_geo"].glob("*.shp")) +
        list(PATHS["raw_geo"].glob("*.geojson")) +
        list(PATHS["raw_geo"].glob("*.gpkg"))
    )

    if not shp_candidats:
        print("  ⚠️  Shapefile communes France absent — carte non générée")
        print("       URL : https://geoservices.ign.fr/adminexpress (ADMIN-EXPRESS COG)")
        print("       Ou   : https://www.data.gouv.fr/fr/datasets/contours-des-communes-de-france-simplifie/")
        print(f"       → Placer dans : {PATHS['raw_geo']}")
        return

    gdf = gpd.read_file(shp_candidats[0])
    print(f"  Shapefile chargé : {shp_candidats[0].name} ({len(gdf)} communes)")

    # Détecter colonne code INSEE dans le shapefile
    col_insee_shp = next((c for c in gdf.columns if any(
        kw in c.lower() for kw in ["insee", "codgeo", "code_com", "com"]
    )), None)

    if col_insee_shp is None:
        print(f"  ⚠️  Code INSEE introuvable dans shapefile — colonnes : {list(gdf.columns)}")
        return

    acv_codes = set(panel[panel["traite"] == 1]["code_insee"].dropna())
    gdf["acv"] = gdf[col_insee_shp].str.strip().isin(acv_codes)

    # Projection Lambert 93
    try:
        gdf = gdf.to_crs("EPSG:2154")
    except Exception:
        pass

    # Exclure DOM-TOM pour la carte principale
    if "geometry" in gdf.columns:
        gdf_metro = gdf[~gdf[col_insee_shp].str.startswith(("97", "98"), na=False)]
    else:
        gdf_metro = gdf

    fig, ax = plt.subplots(figsize=(8, 9))
    gdf_metro[~gdf_metro["acv"]].plot(
        ax=ax, color="#dddddd", edgecolor="white", linewidth=0.1
    )
    gdf_metro[gdf_metro["acv"]].plot(
        ax=ax, color="black", edgecolor="white", linewidth=0.3, markersize=4
    )
    ax.set_axis_off()
    ax.set_title("Localisation des 222 villes Action Cœur de Ville",
                 fontsize=12, pad=10)
    ax.annotate("Note : Points noirs = villes ACV (sélectionnées mars 2018).",
                xy=(0.01, 0.02), xycoords="axes fraction", fontsize=7)

    dest = PATHS["figures"] / "map1_acv_location.pdf"
    fig.savefig(dest)
    plt.close(fig)
    print(f"  → {dest}")


# ── Statistiques descriptives générales ───────────────────────────────────────

def stats_descriptives(panel: pd.DataFrame) -> None:
    print("\n  === Statistiques descriptives ===")
    covariates = ["part_rn", "population", "rev_median",
                  "taux_chomage", "part_cadres", "part_ouvriers"]
    cols_dispo = [c for c in covariates if c in panel.columns]

    desc = panel[cols_dispo].describe().T
    print(desc.round(3).to_string())

    dest = PATHS["tables"] / "tableA0_desc_stats.tex"
    desc.round(3).to_latex(dest, caption="Statistiques descriptives", label="tab:desc")
    print(f"  → {dest}")


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 06_descriptive.py ===")
    panel = charger_panel()

    if panel.empty:
        print("  ⚠️  Panel vide — statistiques descriptives non générées")
        return

    stats_descriptives(panel)
    table_balance(panel)
    figure_tendances_brutes(panel)
    carte_acv(panel)

    print("\n  ✓ Statistiques descriptives terminées")


if __name__ == "__main__":
    main()
