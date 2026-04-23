################################################################################
# 08_did_main.py
# Estimation principale : Callaway-Sant'Anna (2021) DiD
# + TWFE classique (pyfixest)
# + Event study
# Output : processed/did_results.pkl
#          output/tables/table2_main_results.tex
#          output/figures/fig2_event_study.pdf
################################################################################

import sys
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, ANNEE_TRAITEMENT, SEED

np.random.seed(SEED)

FONT = {"family": "DejaVu Sans", "size": 10}
matplotlib.rc("font", **FONT)
plt.rcParams.update({
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})


def charger_panel(matche: bool = True) -> pd.DataFrame:
    nom = "matched_panel" if matche else "panel_final"
    p = PATHS["processed"] / f"{nom}.parquet"
    if not p.exists() and matche:
        print("  Matched panel absent — utilisation du panel complet")
        p = PATHS["processed"] / "panel_final.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} absent")
    return pd.read_parquet(p)


# ── Préparation du panel pour CS2021 ─────────────────────────────────────────

def preparer_cs2021(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Format requis par le package `differences` :
    - Index : (code_insee, annee_scrutin_numerique)
    - Colonne 'annee_traitement' : 2018 pour traités, 0 pour jamais traités
    - Variable dépendante : part_rn
    """
    # Créer un identifiant numérique commune
    communes = panel["code_insee"].unique()
    id_map = {c: i+1 for i, c in enumerate(sorted(communes))}
    panel = panel.copy()
    panel["id_commune"] = panel["code_insee"].map(id_map)

    # Convertir l'année du scrutin en numérique continu
    # Mapping : chaque scrutin → année (pres2012→2012, eur2014→2014, etc.)
    panel["annee_num"] = panel["annee"].astype(int)

    # Vérifier que part_rn existe et n'est pas entièrement NaN
    if panel["part_rn"].isna().all():
        raise ValueError("part_rn entièrement manquant — vérifier l'étape 3")

    # annee_traitement : 2018 pour traités, np.nan pour jamais-traités (convention differences)
    panel["cohort"] = np.where(panel["traite"] == 1, ANNEE_TRAITEMENT, np.nan)

    return panel


# ── 1. Callaway-Sant'Anna (2021) ──────────────────────────────────────────────

def estimer_cs2021(panel: pd.DataFrame) -> dict:
    """
    Estimation ATT_gt via le package `differences` (implémentation Python de CS2021).
    """
    try:
        from differences import ATTgt
    except ImportError:
        print("  ❌ Package `differences` non disponible — CS2021 non estimé")
        return {}

    df = preparer_cs2021(panel).copy()
    df = df.dropna(subset=["part_rn"])
    df = df.set_index(["id_commune", "annee_num"])

    covariates_dispo = [c for c in ["rev_median", "taux_chomage",
                                     "part_cadres", "part_ouvriers"]
                        if c in df.columns and df[c].notna().sum() > df[c].isna().sum()]

    print(f"\n  CS2021 — panel : {len(df)} obs")
    print(f"  Covariates incluses : {covariates_dispo if covariates_dispo else 'aucune'}")

    try:
        attgt = ATTgt(data=df, cohort_column="cohort")

        # Sans covariates d'abord
        def extraire_att_se(agg_df) -> tuple[float, float]:
            """Extrait ATT et SE depuis le DataFrame MultiIndex de differences."""
            # Aplatir les colonnes MultiIndex en chaînes
            cols_flat = ["_".join([s for s in col if s]).strip("_")
                         for col in agg_df.columns]
            agg_df.columns = cols_flat
            col_att = next((c for c in cols_flat if c.endswith("ATT")), None)
            col_se  = next((c for c in cols_flat if "std_error" in c or "se" in c.lower()), None)
            att = float(agg_df[col_att].iloc[0]) if col_att else np.nan
            se  = float(agg_df[col_se].iloc[0])  if col_se  else np.nan
            return att, se

        result_sans = attgt.fit(formula="part_rn ~ 1")
        agg_sans = result_sans.aggregate("simple")
        att_s, se_s = extraire_att_se(agg_sans)
        print(f"\n  ATT global (sans covariates) :")
        print(f"    ATT = {att_s:.4f}")
        print(f"    SE  = {se_s:.4f}")

        results = {"cs2021_sans_cov": {"att": att_s, "se": se_s}}

        # Avec covariates si disponibles
        if covariates_dispo:
            formula_cov = "part_rn ~ " + " + ".join(covariates_dispo)
            result_avec = attgt.fit(formula=formula_cov)
            agg_avec = result_avec.aggregate("simple")
            att_a, se_a = extraire_att_se(agg_avec)
            print(f"\n  ATT global (avec covariates) :")
            print(f"    ATT = {att_a:.4f}")
            print(f"    SE  = {se_a:.4f}")
            results["cs2021_avec_cov"] = {"att": att_a, "se": se_a}

        return results

    except Exception as e:
        print(f"  ❌ Erreur CS2021 : {e}")
        return {}


# ── 2. TWFE classique (pyfixest) ──────────────────────────────────────────────

def estimer_twfe(panel: pd.DataFrame) -> dict:
    """
    Two-Way Fixed Effects classique : part_rn ~ traite × post | commune + annee
    """
    try:
        import pyfixest as pf
    except ImportError:
        print("  ❌ pyfixest non disponible — TWFE non estimé")
        return {}

    df = panel.dropna(subset=["part_rn"]).copy()
    df["traite_x_post"] = df["traite"] * df["post"]

    # Spécification de base
    try:
        fit_base = pf.feols(
            "part_rn ~ traite_x_post | code_insee + annee_num",
            data=df.assign(annee_num=df["annee"].astype(int)),
            vcov={"CRV1": "code_insee"}
        )
        coef_base = fit_base.coef()["traite_x_post"]
        se_base   = fit_base.se()["traite_x_post"]
        print(f"\n  TWFE (base) : ATT = {coef_base:.4f} (SE = {se_base:.4f})")
        return {"twfe_base": fit_base}
    except Exception as e:
        print(f"  ❌ Erreur TWFE : {e}")
        return {}


# ── 3. Event study ────────────────────────────────────────────────────────────

def estimer_event_study(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Event study : part_rn ~ Σ β_k × (traite × 1[annee=k]) | commune + annee
    Année de référence : 2017 (dernière année pré-traitement).
    """
    try:
        import pyfixest as pf
    except ImportError:
        return pd.DataFrame()

    df = panel.dropna(subset=["part_rn"]).copy()
    annees = sorted(df["annee"].unique())
    ref_annee = 2017  # normalisé à 0

    # Créer dummies d'interaction traite × annee
    for an in annees:
        if an != ref_annee:
            df[f"d{an}"] = (df["traite"] == 1) & (df["annee"] == an)
            df[f"d{an}"] = df[f"d{an}"].astype(int)

    dummies = [f"d{an}" for an in annees if an != ref_annee]
    if not dummies:
        return pd.DataFrame()

    formula = "part_rn ~ " + " + ".join(dummies) + " | code_insee + annee_num"

    try:
        df["annee_num"] = df["annee"].astype(int)
        fit = pf.feols(formula, data=df, vcov={"CRV1": "code_insee"})
        coefs = fit.coef()
        ses   = fit.se()

        rows = []
        for an in annees:
            if an == ref_annee:
                rows.append({"annee": an, "coef": 0.0, "se": 0.0,
                             "ci_low": 0.0, "ci_high": 0.0})
            else:
                key = f"d{an}"
                if key in coefs.index:
                    c = coefs[key]
                    s = ses[key]
                    rows.append({"annee": an, "coef": c, "se": s,
                                 "ci_low": c - 1.96*s, "ci_high": c + 1.96*s})

        event_df = pd.DataFrame(rows).sort_values("annee")
        print(f"\n  Event study : {len(event_df)} points")
        print(event_df[["annee", "coef", "se"]].round(4).to_string(index=False))
        return event_df

    except Exception as e:
        print(f"  ❌ Erreur event study : {e}")
        return pd.DataFrame()


# ── Figure 2 : Event Study ────────────────────────────────────────────────────

def figure_event_study(event_df: pd.DataFrame, titre: str = "Principal") -> None:
    if event_df.empty:
        print("  ⚠️  Event study vide — figure non générée")
        return

    fig, ax = plt.subplots(figsize=(8, 5))

    pre  = event_df[event_df["annee"] < 2018]
    post = event_df[event_df["annee"] >= 2018]

    for subset, color, label in [
        (pre, "gray", "Pré-traitement"),
        (post, "black", "Post-traitement")
    ]:
        if subset.empty:
            continue
        ax.plot(subset["annee"], subset["coef"] * 100, "o-",
                color=color, linewidth=2, markersize=7, label=label)
        ax.fill_between(subset["annee"],
                        subset["ci_low"] * 100,
                        subset["ci_high"] * 100,
                        alpha=0.15, color=color)

    # Ligne de référence
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(2017.5, color="black", linewidth=1, linestyle=":", alpha=0.6)
    ax.text(2017.6, ax.get_ylim()[1] * 0.9, "Sélection\nACV (2018)",
            fontsize=8, va="top")

    ax.set_xlabel("Année du scrutin")
    ax.set_ylabel("ATT (pp, % suffrages exprimés)")
    ax.set_title(f"Event study — Effet ACV sur vote RN ({titre})", fontsize=11)
    ax.legend(frameon=False)
    ax.set_xticks(sorted(event_df["annee"].unique()))

    plt.tight_layout()
    dest = PATHS["figures"] / "fig2_event_study.pdf"
    fig.savefig(dest)
    plt.close(fig)
    print(f"  → {dest}")


# ── Table 2 : Résultats principaux ────────────────────────────────────────────

def table_resultats_principaux(results_cs: dict, results_twfe: dict) -> None:
    rows = []

    if "cs2021_sans_cov" in results_cs:
        r = results_cs["cs2021_sans_cov"]
        rows.append({
            "Spécification": "CS2021 (sans covariates)",
            "ATT": f"{r['att']*100:.3f}",
            "SE":  f"{r['se']*100:.3f}",
            "N communes": "—",
        })

    if "cs2021_avec_cov" in results_cs:
        r = results_cs["cs2021_avec_cov"]
        rows.append({
            "Spécification": "CS2021 (avec covariates)",
            "ATT": f"{r['att']*100:.3f}",
            "SE":  f"{r['se']*100:.3f}",
            "N communes": "—",
        })

    if "twfe_base" in results_twfe:
        fit = results_twfe["twfe_base"]
        c   = fit.coef()["traite_x_post"]
        s   = fit.se()["traite_x_post"]
        rows.append({
            "Spécification": "TWFE (base)",
            "ATT": f"{c*100:.3f}",
            "SE":  f"{s*100:.3f}",
            "N communes": "—",
        })

    if not rows:
        print("  ⚠️  Aucun résultat disponible pour Table 2")
        return

    tab = pd.DataFrame(rows)
    tab["ATT (pp)"] = tab["ATT"]
    tab["Notes"] = "Clustering commune"

    print("\n  Table 2 — Résultats principaux :")
    print(tab.to_string(index=False))

    dest = PATHS["tables"] / "table2_main_results.tex"
    tab.to_latex(dest, index=False, escape=True,
                 caption="Effet ACV sur vote RN — Résultats principaux (ATT en points de pourcentage)",
                 label="tab:main")
    print(f"  → {dest}")


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 08_did_main.py ===")

    panel = charger_panel(matche=True)

    if panel.empty or panel["part_rn"].isna().all():
        print("  ⚠️  Panel vide ou part_rn entièrement manquant")
        print("       Vérifier les étapes 1-5 (données brutes)")
        return {}

    print(f"\n  Panel : {panel.shape[0]} obs | {panel['code_insee'].nunique()} communes")
    print(f"  Traitées : {panel[panel['traite']==1]['code_insee'].nunique()}")
    print(f"  Contrôles: {panel[panel['traite']==0]['code_insee'].nunique()}")
    print(f"  Scrutins : {sorted(panel['scrutin'].unique())}")

    print("\n  --- Callaway-Sant'Anna (2021) ---")
    results_cs = estimer_cs2021(panel)

    print("\n  --- TWFE classique ---")
    results_twfe = estimer_twfe(panel)

    print("\n  --- Event study ---")
    event_df = estimer_event_study(panel)
    figure_event_study(event_df)

    table_resultats_principaux(results_cs, results_twfe)

    # Extraire les scalaires (pyfixest Feols objects ne sont pas picklables)
    twfe_serial = {}
    for k, fit in results_twfe.items():
        try:
            twfe_serial[k] = {
                "coef":   float(fit.coef()["traite_x_post"]),
                "se":     float(fit.se()["traite_x_post"]),
                "pvalue": float(fit.pvalue()["traite_x_post"]),
            }
        except Exception as exc:
            print(f"    ⚠️  Sérialisation TWFE '{k}' : {exc}")

    cs_serial = {k: {"att": v["att"], "se": v["se"]}
                 for k, v in results_cs.items()
                 if isinstance(v, dict) and "att" in v}

    resultats = {
        "cs2021":      cs_serial,
        "twfe":        twfe_serial,
        "event_study": event_df,
    }
    with open(PATHS["processed"] / "did_results.pkl", "wb") as f:
        pickle.dump(resultats, f)
    print(f"\n  ✓ Résultats sauvegardés : {PATHS['processed'] / 'did_results.pkl'}")

    return resultats


if __name__ == "__main__":
    main()
