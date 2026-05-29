################################################################################
# 07_matching.py
# Propensity score matching : villes ACV vs villes moyennes non-ACV
# Méthode : nearest neighbor 1:3, caliper 0.25 SD du propensity score
# Output : processed/matched_panel.parquet
#          processed/pscore_model.pkl
#          output/tables/tableA1_matching_balance.tex
#          output/figures/fig_pscore_overlap.pdf
################################################################################

import sys
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, SEED

np.random.seed(SEED)
rng = np.random.default_rng(SEED)

FONT = {"family": "DejaVu Sans", "size": 10}
matplotlib.rc("font", **FONT)
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False,
                      "savefig.dpi": 300, "savefig.bbox": "tight"})


def charger_panel() -> pd.DataFrame:
    p = PATHS["processed"] / "panel_final.parquet"
    if not p.exists():
        raise FileNotFoundError("panel_final.parquet absent")
    return pd.read_parquet(p)


# ── Variables de matching ─────────────────────────────────────────────────────

COVARIATES_MATCHING = [
    "population",       # taille commune
    "rev_median",       # revenu médian pré-traitement
    "taux_chomage",     # taux de chômage
    "part_cadres",      # structure socio-professionnelle
    "part_ouvriers",
    "part_rn_pre",      # vote RN moyen pré-traitement (construit ci-dessous)
]


def preparer_donnees_matching(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Construit le dataset commune × covariates pré-traitement pour le matching.
    Utilise la dernière observation pré-traitement disponible pour chaque covariate.
    """
    pre = panel[panel["annee"] < 2018].copy()

    # Vote RN moyen pré-traitement par commune
    rn_pre = (pre.groupby("code_insee")["part_rn"]
              .mean().rename("part_rn_pre").reset_index())

    # Covariates INSEE : valeur 2017 ou plus récente pré-2018
    covariates_insee = ["population", "rev_median", "taux_chomage",
                         "part_cadres", "part_ouvriers"]
    cov_dispo = [c for c in covariates_insee if c in pre.columns]

    if cov_dispo:
        cov_pre = (
            pre[pre["annee"] == pre["annee"].max()]
            .drop_duplicates("code_insee")[["code_insee", "traite"] + cov_dispo]
        )
    else:
        cov_pre = pre.drop_duplicates("code_insee")[["code_insee", "traite"]]
        for c in covariates_insee:
            cov_pre[c] = np.nan

    df_match = cov_pre.merge(rn_pre, on="code_insee", how="left")
    return df_match


# ── Estimation du propensity score ────────────────────────────────────────────

def estimer_pscore(df: pd.DataFrame) -> tuple[pd.DataFrame, LogisticRegression, StandardScaler]:
    """
    Régression logistique pour estimer le propensity score P(ACV | X).
    Gère les valeurs manquantes par imputation médiane.
    """
    covariates_dispo = [c for c in COVARIATES_MATCHING if c in df.columns]
    covariates_dispo = [c for c in covariates_dispo if df[c].notna().sum() > 10]

    print(f"  Covariates pour matching : {covariates_dispo}")

    if not covariates_dispo:
        print("  ⚠️  AUCUNE covariate disponible pour le matching")
        print("       Le matching sera effectué sur vote RN pré-traitement uniquement si disponible")
        if "part_rn_pre" not in df.columns:
            df["pscore"] = np.nan
            df["poids_match"] = 1.0
            return df, None, None
        covariates_dispo = ["part_rn_pre"]

    X = df[covariates_dispo].values
    y = df["traite"].values

    # Imputation médiane
    imputer = SimpleImputer(strategy="median")
    X_imp = imputer.fit_transform(X)

    # Normalisation
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_imp)

    # Logit
    model = LogisticRegression(max_iter=1000, random_state=SEED, C=1.0)
    model.fit(X_scaled, y)

    df["pscore"] = model.predict_proba(X_scaled)[:, 1]

    auc = _roc_auc(y, df["pscore"].values)
    print(f"  AUC propensity score : {auc:.3f}")
    print(f"  P(traité) — traités  : {df[df['traite']==1]['pscore'].mean():.3f}")
    print(f"  P(traité) — contrôles: {df[df['traite']==0]['pscore'].mean():.3f}")

    return df, model, scaler


def _roc_auc(y_true, y_score) -> float:
    from sklearn.metrics import roc_auc_score
    try:
        return roc_auc_score(y_true, y_score)
    except Exception:
        return np.nan


# ── Matching nearest neighbor 1:3 avec caliper ────────────────────────────────

def nearest_neighbor_matching(df: pd.DataFrame,
                               ratio: int = 3,
                               caliper_sd: float = 0.25) -> pd.DataFrame:
    """
    Pour chaque traité, trouve les `ratio` contrôles les plus proches
    en propensity score, dans un caliper de `caliper_sd` * SD(pscore).
    Sans remise.
    """
    if "pscore" not in df.columns or df["pscore"].isna().all():
        print("  ⚠️  Propensity score non disponible — matching non effectué")
        df["matched"] = True
        df["match_weight"] = 1.0
        return df

    traites  = df[df["traite"] == 1].copy()
    controles = df[df["traite"] == 0].copy().reset_index(drop=True)

    caliper = caliper_sd * df["pscore"].std()
    print(f"  Caliper = {caliper:.4f} ({caliper_sd} × SD={df['pscore'].std():.4f})")

    controles_idx_utilises = set()
    matches = []  # liste (code_traite, [code_controles])

    traites_shuffled = traites.sample(frac=1, random_state=SEED)

    n_sans_match = 0
    for _, row in traites_shuffled.iterrows():
        ps = row["pscore"]
        # Candidats contrôles dans le caliper, non encore utilisés
        candidats = controles[
            (~controles.index.isin(controles_idx_utilises)) &
            (np.abs(controles["pscore"] - ps) <= caliper)
        ].copy()

        if len(candidats) == 0:
            n_sans_match += 1
            continue

        # Trier par distance au propensity score
        candidats["dist"] = np.abs(candidats["pscore"] - ps)
        candidats = candidats.nsmallest(ratio, "dist")

        matches.append({
            "code_traite": row["code_insee"],
            "code_controles": list(candidats["code_insee"]),
            "n_controles": len(candidats)
        })
        controles_idx_utilises.update(candidats.index.tolist())

    if n_sans_match > 0:
        print(f"  ⚠️  {n_sans_match} traités sans match dans le caliper")

    # Construire le dataset matché
    codes_traites = {m["code_traite"] for m in matches}
    codes_controles = {c for m in matches for c in m["code_controles"]}
    codes_gardes = codes_traites | codes_controles

    df_match = df[df["code_insee"].isin(codes_gardes)].copy()
    df_match["matched"] = True

    n_t = len(codes_traites)
    n_c = len(codes_controles)
    ratio_eff = n_c / n_t if n_t > 0 else 0
    print(f"  ✓ Matched : {n_t} traités × {n_c} contrôles (ratio effectif = {ratio_eff:.2f})")

    return df_match, pd.DataFrame(matches)


# ── Table balance post-matching ───────────────────────────────────────────────

def table_balance_matching(df_avant: pd.DataFrame,
                            df_apres: pd.DataFrame) -> None:
    covariates_dispo = [c for c in COVARIATES_MATCHING if c in df_avant.columns]
    rows = []
    for col in covariates_dispo:
        t_av = df_avant[df_avant["traite"] == 1][col].dropna()
        c_av = df_avant[df_avant["traite"] == 0][col].dropna()
        t_ap = df_apres[df_apres["traite"] == 1][col].dropna()
        c_ap = df_apres[df_apres["traite"] == 0][col].dropna()

        smd_avant = _smd(t_av, c_av)
        smd_apres = _smd(t_ap, c_ap)

        rows.append({
            "Variable": col,
            "ACV (avant)":     f"{t_av.mean():.3f}",
            "Ctrl (avant)":    f"{c_av.mean():.3f}",
            "SMD avant":       f"{smd_avant:.3f}",
            "ACV (après)":     f"{t_ap.mean():.3f}",
            "Ctrl (après)":    f"{c_ap.mean():.3f}",
            "SMD après":       f"{smd_apres:.3f}",
        })

    tab = pd.DataFrame(rows)
    print("\n  Table balance matching :")
    print(tab.to_string(index=False))

    dest = PATHS["tables"] / "tableA1_matching_balance.tex"
    tab.to_latex(dest, index=False, escape=True,
                 caption="Balance avant/après matching (SMD = standardized mean difference)",
                 label="tab:matching_balance")
    print(f"  → {dest}")


def _smd(t: pd.Series, c: pd.Series) -> float:
    """Standardized mean difference."""
    if len(t) < 2 or len(c) < 2:
        return np.nan
    denom = np.sqrt((t.var() + c.var()) / 2)
    return (t.mean() - c.mean()) / denom if denom > 0 else 0.0


# ── Figure : Overlap propensity scores ────────────────────────────────────────

def figure_overlap(df: pd.DataFrame) -> None:
    if "pscore" not in df.columns or df["pscore"].isna().all():
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    bins = np.linspace(0, 1, 40)

    t = df[df["traite"] == 1]["pscore"].dropna()
    c = df[df["traite"] == 0]["pscore"].dropna()

    ax.hist(c, bins=bins, alpha=0.5, color="gray",   label="Non-ACV (contrôle)", density=True)
    ax.hist(t, bins=bins, alpha=0.7, color="black",  label="ACV (traité)", density=True)

    ax.set_xlabel("Propensity score estimé")
    ax.set_ylabel("Densité")
    ax.set_title("Support commun — Propensity score matching")
    ax.legend(frameon=False)

    dest = PATHS["figures"] / "fig_pscore_overlap.pdf"
    fig.savefig(dest)
    plt.close(fig)
    print(f"  → {dest}")


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 07_matching.py ===")
    panel = charger_panel()

    df_match_input = preparer_donnees_matching(panel)
    print(f"\n  Dataset matching : {len(df_match_input)} communes")
    print(f"  Traitées : {df_match_input['traite'].sum()} | "
          f"Contrôles : {(df_match_input['traite']==0).sum()}")

    df_match_input, model, scaler = estimer_pscore(df_match_input)
    figure_overlap(df_match_input)

    result = nearest_neighbor_matching(df_match_input, ratio=3, caliper_sd=0.25)
    if isinstance(result, tuple):
        df_matched, df_matches_tbl = result
    else:
        df_matched = result
        df_matches_tbl = pd.DataFrame()

    table_balance_matching(df_match_input, df_matched)

    # Sauvegarder le dataset matché
    matched_codes = set(df_matched["code_insee"])
    panel_matched = panel[panel["code_insee"].isin(matched_codes)].copy()

    # Ajouter le pscore au panel
    pscore_map = df_match_input.set_index("code_insee")["pscore"].to_dict()
    panel_matched["pscore"] = panel_matched["code_insee"].map(pscore_map)

    dest = PATHS["processed"] / "matched_panel.parquet"
    panel_matched.to_parquet(dest, index=False)
    print(f"\n  Panel matché sauvegardé : {dest}")
    print(f"  Dimensions : {panel_matched.shape}")

    # Sauvegarder le modèle de pscore
    if model is not None:
        with open(PATHS["processed"] / "pscore_model.pkl", "wb") as f:
            pickle.dump({"model": model, "scaler": scaler,
                         "covariates": COVARIATES_MATCHING}, f)

    if not df_matches_tbl.empty:
        df_matches_tbl.to_parquet(PATHS["processed"] / "matches_table.parquet", index=False)

    return panel_matched


if __name__ == "__main__":
    main()
