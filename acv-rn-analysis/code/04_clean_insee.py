################################################################################
# 04_clean_insee.py
# Nettoyage des données socio-démographiques INSEE
# Input  : data/raw/insee/ + data/raw/geo/
# Output : data/processed/insee_panel.parquet
#          Colonnes : code_insee, annee, population, rev_median,
#                     taux_chomage, part_cadres, part_ouvriers
################################################################################

import sys
import re
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, POP_MIN, POP_MAX, SEED

np.random.seed(SEED)


# ── Harmonisation codes INSEE (gestion des fusions de communes) ───────────────

def charger_cog(dossier: Path) -> pd.DataFrame | None:
    """Charge le Code Officiel Géographique pour harmonisation."""
    candidats = list(dossier.glob("cog_communes*.csv")) + list(dossier.glob("commune_*.csv"))
    if not candidats:
        print("  ⚠️  COG non disponible — harmonisation des fusions désactivée")
        print("       Télécharger : https://www.insee.fr/fr/information/6800675")
        return None
    return pd.read_csv(candidats[0], dtype=str, encoding="utf-8")


def normaliser_code_insee(serie: pd.Series) -> pd.Series:
    def norm(x):
        if pd.isna(x):
            return np.nan
        x = str(x).strip().upper().replace(".", "").replace(" ", "")
        if re.match(r"^(2A|2B)\d{3}$", x):
            return x
        if re.match(r"^\d{1,5}$", x):
            return x.zfill(5)
        return np.nan
    return serie.map(norm)


# ── 1. Populations légales ───────────────────────────────────────────────────

def charger_populations(dossier: Path) -> pd.DataFrame:
    """
    Charge les populations légales INSEE.
    Formats attendus : CSV avec code_insee + population par millésime.
    """
    candidats = list(dossier.glob("*population*legale*.csv")) + \
                list(dossier.glob("*pop_legale*.csv")) + \
                list(dossier.glob("*pop*.csv"))

    if not candidats:
        print("  ⚠️  POPULATIONS LÉGALES MANQUANTES")
        print("       URL : https://www.insee.fr/fr/statistiques/6683031")
        print("       → Télécharger et placer dans data/raw/insee/")
        return pd.DataFrame(columns=["code_insee", "annee", "population"])

    frames = []
    for f in candidats:
        print(f"    Chargement : {f.name}")
        try:
            for enc in ["utf-8", "latin-1"]:
                for sep in [";", ","]:
                    try:
                        df = pd.read_csv(f, sep=sep, encoding=enc, dtype=str)
                        if df.shape[1] < 2:
                            continue
                        # Détection colonnes
                        cols = df.columns.str.lower()
                        col_insee = next((c for c in df.columns if any(
                            kw in c.lower() for kw in ["codgeo", "code_com", "insee", "code"]
                        )), None)
                        col_pop = next((c for c in df.columns if any(
                            kw in c.lower() for kw in ["pmun", "pop_mun", "population", "pop"]
                        )), None)
                        col_an = next((c for c in df.columns if any(
                            kw in c.lower() for kw in ["annee", "millesime", "year"]
                        )), None)

                        if col_insee and col_pop:
                            df_clean = pd.DataFrame({
                                "code_insee": normaliser_code_insee(df[col_insee]),
                                "population": pd.to_numeric(df[col_pop], errors="coerce"),
                                "annee": pd.to_numeric(df[col_an], errors="coerce")
                                         if col_an else None,
                            })
                            # Extraire millésime du nom de fichier si pas de colonne annee
                            if col_an is None:
                                m = re.search(r"(20\d{2})", f.name)
                                if m:
                                    df_clean["annee"] = int(m.group(1))
                            frames.append(df_clean)
                            break
                    except Exception:
                        continue
        except Exception as e:
            print(f"    Erreur lecture {f.name} : {e}")

    if not frames:
        return pd.DataFrame(columns=["code_insee", "annee", "population"])

    pop = pd.concat(frames).dropna(subset=["code_insee", "population"])
    return pop


# ── 2. Filosofi — revenu médian ──────────────────────────────────────────────

def charger_filosofi(dossier: Path) -> pd.DataFrame:
    """
    Charge les revenus médians Filosofi par commune.
    Attention : disponible uniquement pour communes > ~1000 hab.
    Millésimes typiques : 2012, 2015, 2017, 2018, 2019
    """
    candidats = list(dossier.glob("*filosof*")) + list(dossier.glob("*revenu*")) + \
                list(dossier.glob("*rfr*")) + list(dossier.glob("*mrd*"))

    if not candidats:
        print("  ⚠️  FILOSOFI MANQUANT")
        print("       URL : https://www.insee.fr/fr/statistiques (rubrique Filosofi)")
        print("       Variables : revenu médian par UC par commune et millésime")
        print("       → Placer dans data/raw/insee/")
        return pd.DataFrame(columns=["code_insee", "annee", "rev_median"])

    frames = []
    for f in candidats:
        try:
            for enc in ["utf-8", "latin-1"]:
                for sep in [";", ","]:
                    try:
                        df = pd.read_csv(f, sep=sep, encoding=enc, dtype=str)
                    except Exception:
                        continue
                    if df.shape[1] < 2:
                        continue

                    col_insee = next((c for c in df.columns if any(
                        kw in c.lower() for kw in ["codgeo", "code", "insee"]
                    )), None)
                    col_rev = next((c for c in df.columns if any(
                        kw in c.lower() for kw in ["q2", "med", "meduc", "revenu_median",
                                                     "revmoy", "rdm", "disp_med"]
                    )), None)
                    col_an = next((c for c in df.columns if any(
                        kw in c.lower() for kw in ["annee", "millesime"]
                    )), None)

                    if col_insee and col_rev:
                        df_c = pd.DataFrame({
                            "code_insee": normaliser_code_insee(df[col_insee]),
                            "rev_median": pd.to_numeric(df[col_rev].str.replace(",", "."),
                                                         errors="coerce"),
                            "annee": pd.to_numeric(df[col_an], errors="coerce") if col_an else None
                        })
                        if col_an is None:
                            m = re.search(r"(20\d{2})", f.name)
                            if m:
                                df_c["annee"] = int(m.group(1))
                        frames.append(df_c)
                        print(f"    Filosofi : {f.name} — {df_c['code_insee'].nunique()} communes")
                        break
        except Exception:
            pass

    if not frames:
        return pd.DataFrame(columns=["code_insee", "annee", "rev_median"])
    return pd.concat(frames).dropna(subset=["code_insee", "rev_median"])


# ── 3. Recensement de population (emploi, catégories socio-pro) ──────────────

def charger_rp(dossier: Path) -> pd.DataFrame:
    """
    Charge les données emploi/CSP du Recensement de Population.
    Variables : part cadres (CS3), part ouvriers (CS6), taux chômage (CHOM).
    Millésimes RP disponibles : 2012, 2014, 2016, 2018, 2020.
    """
    candidats = (list(dossier.glob("*rp*commune*")) +
                 list(dossier.glob("*recensement*")) +
                 list(dossier.glob("*emploi*commune*")))

    if not candidats:
        print("  ⚠️  DONNÉES RP (emploi/CSP) MANQUANTES")
        print("       URL : https://www.insee.fr/fr/statistiques (Recensement de population)")
        print("       → Placer dans data/raw/insee/")
        return pd.DataFrame(columns=["code_insee", "annee",
                                      "taux_chomage", "part_cadres", "part_ouvriers"])

    frames = []
    for f in candidats:
        print(f"    Chargement RP : {f.name}")
        try:
            for enc in ["utf-8", "latin-1"]:
                df = pd.read_csv(f, sep=None, encoding=enc, dtype=str, engine="python")
                if df.shape[1] < 3:
                    continue

                col_insee = next((c for c in df.columns if any(
                    kw in c.lower() for kw in ["codgeo", "code_com", "code"]
                )), None)

                # Taux chômage : part pop active au chômage
                col_chom = next((c for c in df.columns if any(
                    kw in c.lower() for kw in ["chom", "taux_ch", "p_chom"]
                )), None)
                # Part cadres (CSP 3)
                col_cadres = next((c for c in df.columns if any(
                    kw in c.lower() for kw in ["cadre", "cs3", "csp3"]
                )), None)
                # Part ouvriers (CSP 6)
                col_ouvriers = next((c for c in df.columns if any(
                    kw in c.lower() for kw in ["ouvrier", "cs6", "csp6"]
                )), None)

                if col_insee is None:
                    continue

                col_an = next((c for c in df.columns if any(
                    kw in c.lower() for kw in ["annee", "millesime"]
                )), None)

                df_c = pd.DataFrame({"code_insee": normaliser_code_insee(df[col_insee])})
                if col_chom:
                    df_c["taux_chomage"] = pd.to_numeric(df[col_chom].str.replace(",", "."),
                                                          errors="coerce")
                if col_cadres:
                    df_c["part_cadres"] = pd.to_numeric(df[col_cadres].str.replace(",", "."),
                                                         errors="coerce")
                if col_ouvriers:
                    df_c["part_ouvriers"] = pd.to_numeric(df[col_ouvriers].str.replace(",", "."),
                                                           errors="coerce")
                if col_an:
                    df_c["annee"] = pd.to_numeric(df[col_an], errors="coerce")
                else:
                    m = re.search(r"(20\d{2})", f.name)
                    df_c["annee"] = int(m.group(1)) if m else np.nan

                frames.append(df_c.dropna(subset=["code_insee"]))
                break
        except Exception as e:
            print(f"    Erreur RP {f.name}: {e}")

    if not frames:
        return pd.DataFrame(columns=["code_insee", "annee",
                                      "taux_chomage", "part_cadres", "part_ouvriers"])
    return pd.concat(frames)


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 04_clean_insee.py ===")
    dossier_insee = PATHS["raw_insee"]
    dossier_geo   = PATHS["raw_geo"]

    pop      = charger_populations(dossier_insee)
    filosofi = charger_filosofi(dossier_insee)
    rp       = charger_rp(dossier_insee)

    print(f"\n  Populations : {len(pop)} obs")
    print(f"  Filosofi    : {len(filosofi)} obs")
    print(f"  RP emploi   : {len(rp)} obs")

    # Merge progressif sur (code_insee, annee)
    # On aligne les millésimes : pop légales → scrutins, filosofi → scrutins
    if pop.empty and filosofi.empty and rp.empty:
        raise RuntimeError(
            "\n❌ AUCUNE donnée INSEE disponible.\n"
            "   Voir TELECHARGEMENTS_MANUELS.md\n"
        )

    # Union des codes et années connus
    all_data = []
    for df, nom in [(pop, "pop"), (filosofi, "filosofi"), (rp, "rp")]:
        if not df.empty and "code_insee" in df.columns and "annee" in df.columns:
            all_data.append(df)

    if all_data:
        # Fusion sur (code_insee, annee) par outer join
        base = all_data[0]
        for df_other in all_data[1:]:
            cols_merge = ["code_insee", "annee"]
            new_cols = [c for c in df_other.columns if c not in base.columns]
            base = base.merge(df_other[cols_merge + new_cols],
                              on=cols_merge, how="outer")
        panel = base
    else:
        panel = pd.DataFrame()

    if not panel.empty:
        # Filtrage communes métropolitaines
        panel = panel[panel["code_insee"].notna()]
        panel = panel[panel["code_insee"].str.match(r"^(\d{5}|2[AB]\d{3})$", na=False)]
        dept = panel["code_insee"].str[:2]
        panel = panel[~dept.isin({"97", "98"})]  # outre-mer

        print(f"\n  Panel INSEE : {panel.shape[0]} obs | {panel['code_insee'].nunique()} communes")
        if "population" in panel.columns:
            print(f"  Années pop  : {sorted(panel[panel['population'].notna()]['annee'].dropna().unique())}")

    dest = PATHS["processed"] / "insee_panel.parquet"
    if not panel.empty:
        panel.to_parquet(dest, index=False)
        print(f"  Sauvegardé : {dest}")
    else:
        # Sauvegarder un DataFrame vide pour ne pas bloquer les étapes suivantes
        pd.DataFrame(columns=["code_insee", "annee", "population",
                               "rev_median", "taux_chomage",
                               "part_cadres", "part_ouvriers"]).to_parquet(dest, index=False)
        print(f"  ⚠️  Panel INSEE vide sauvegardé — matching sans covariates INSEE")

    return panel


if __name__ == "__main__":
    main()
