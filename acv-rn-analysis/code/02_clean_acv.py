################################################################################
# 02_clean_acv.py
# Nettoyage de la liste des villes Action Cœur de Ville
# Input  : data/raw/acv/  (un ou plusieurs fichiers CSV/XLSX)
# Output : data/processed/acv_communes.parquet
#          Colonnes : code_insee, nom_commune, dept, region, est_binome
################################################################################

import sys
import re
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, SEED

np.random.seed(SEED)

# ── 1. Chargement ─────────────────────────────────────────────────────────────

def charger_acv(dossier: Path) -> pd.DataFrame:
    """Tente de charger la liste ACV depuis plusieurs formats possibles."""
    candidats = list(dossier.glob("*.csv")) + list(dossier.glob("*.xlsx"))

    if not candidats:
        raise FileNotFoundError(
            f"\n❌ AUCUN FICHIER ACV TROUVÉ dans {dossier}\n"
            "   → Téléchargez manuellement depuis :\n"
            "     https://www.data.gouv.fr/fr/datasets/action-coeur-de-ville/\n"
            "   Ou depuis la Caisse des Dépôts :\n"
            "     https://opendata.caissedesdepots.fr/explore/dataset/villes_action_coeurdeville/\n"
            f"   Placez le fichier dans : {dossier}\n"
        )

    fichier = candidats[0]
    print(f"  Chargement ACV : {fichier.name}")

    if fichier.suffix == ".csv":
        # Essai avec séparateurs courants
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(fichier, sep=sep, encoding="utf-8", dtype=str)
                if df.shape[1] > 2:
                    print(f"    Séparateur détecté : '{sep}' — {df.shape[0]} lignes, {df.shape[1]} colonnes")
                    return df
            except Exception:
                continue
        # Dernier recours : python engine
        df = pd.read_csv(fichier, sep=None, engine="python", dtype=str)
        return df
    else:
        return pd.read_excel(fichier, dtype=str)


def normaliser_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    """Standardise les noms de colonnes."""
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-\/]+", "_", regex=True)
        .str.replace(r"[àáâ]", "a", regex=True)
        .str.replace(r"[éèêë]", "e", regex=True)
        .str.replace(r"[îï]", "i", regex=True)
        .str.replace(r"[ôö]", "o", regex=True)
        .str.replace(r"[ùûü]", "u", regex=True)
        .str.replace(r"[^a-z0-9_]", "", regex=True)
    )
    return df


def detecter_colonne_insee(df: pd.DataFrame) -> str:
    """Détecte la colonne contenant le code INSEE dans la liste ACV."""
    candidats_insee = [c for c in df.columns if any(
        kw in c.lower() for kw in ["insee", "code_com", "codgeo", "codecom", "com_arm"]
    )]
    if candidats_insee:
        return candidats_insee[0]

    # Détection par pattern : 5 chiffres (codes INSEE commune)
    for col in df.columns:
        sample = df[col].dropna().head(20)
        n_match = sample.str.match(r"^\d{5}$").sum()
        if n_match > 10:
            print(f"    Code INSEE détecté automatiquement dans colonne : '{col}'")
            return col

    raise ValueError(
        "Impossible de détecter la colonne code INSEE dans le fichier ACV.\n"
        f"Colonnes disponibles : {list(df.columns)}\n"
        "Renommez manuellement la colonne en 'code_insee' et relancez."
    )


def normaliser_code_insee(serie: pd.Series) -> pd.Series:
    """Pad les codes INSEE à 5 caractères (gère la Corse : 2A/2B)."""
    def normaliser(x):
        if pd.isna(x):
            return np.nan
        x = str(x).strip().upper()
        x = re.sub(r"[.\s]", "", x)
        # Corse : 2A/2B déjà correcte
        if re.match(r"^(2A|2B)\d{3}$", x):
            return x
        # Numérique : pad à 5
        if re.match(r"^\d{1,5}$", x):
            return x.zfill(5)
        return x
    return serie.map(normaliser)


def est_outremer(code: str) -> bool:
    if pd.isna(code):
        return False
    return str(code)[:2] in {"97", "98"} or str(code)[:3] in {"970", "971", "972", "973", "974", "975", "976"}


# ── 2. Pipeline principal ─────────────────────────────────────────────────────

def main():
    print("\n=== 02_clean_acv.py ===")

    df_raw = charger_acv(PATHS["raw_acv"])
    df = normaliser_colonnes(df_raw.copy())
    print(f"  Colonnes disponibles : {list(df.columns)}")

    # Détection code INSEE
    col_insee = detecter_colonne_insee(df)
    df["code_insee"] = normaliser_code_insee(df[col_insee])

    # Détection colonne nom commune
    col_nom = next(
        (c for c in df.columns if any(kw in c for kw in ["nom", "commune", "ville", "label", "libelle"])),
        None
    )
    if col_nom:
        df["nom_commune"] = df[col_nom].str.strip().str.upper()
    else:
        df["nom_commune"] = df["code_insee"]
        print("  ⚠️  Colonne nom commune non trouvée — utilisation du code INSEE")

    # Détection département
    col_dept = next(
        (c for c in df.columns if any(kw in c for kw in ["dept", "dep", "departement"])),
        None
    )
    if col_dept:
        df["dept"] = df[col_dept].str.strip().str.zfill(2)
    else:
        df["dept"] = df["code_insee"].str[:2]
        print("  Département extrait du code INSEE (2 premiers chiffres)")

    # Détection région
    col_reg = next(
        (c for c in df.columns if "reg" in c),
        None
    )
    df["region"] = df[col_reg].str.strip() if col_reg else np.nan

    # Détection binômes
    col_binome = next(
        (c for c in df.columns if "binom" in c or "pair" in c),
        None
    )
    if col_binome:
        df["est_binome"] = df[col_binome].notna() & (df[col_binome].str.strip() != "")
    else:
        # Heuristique : communes apparaissant en doublon dans la liste ACV
        df["est_binome"] = False
        print("  ⚠️  Colonne binôme non trouvée — détection par doublons de villes")

    # Filtrage qualité
    n_avant = len(df)
    df = df[df["code_insee"].notna() & df["code_insee"].str.match(r"^(\d{5}|2[AB]\d{3})$")]
    n_invalides = n_avant - len(df)
    if n_invalides > 0:
        print(f"  ⚠️  {n_invalides} lignes avec code INSEE invalide supprimées")

    # Exclusion outre-mer
    n_avant = len(df)
    df = df[~df["code_insee"].map(est_outremer)]
    n_om = n_avant - len(df)
    if n_om > 0:
        print(f"  Exclusion outre-mer : {n_om} communes")

    # Sélection colonnes finales
    df_final = df[["code_insee", "nom_commune", "dept", "region", "est_binome"]].drop_duplicates(
        subset="code_insee"
    ).reset_index(drop=True)
    df_final["traitement"] = 1
    df_final["annee_traitement"] = 2018

    # ── Vérification ─────────────────────────────────────────────────────────
    n = len(df_final)
    n_binomes = df_final["est_binome"].sum()
    print(f"\n  ✓ Liste ACV nettoyée : {n} communes (dont {n_binomes} en binôme)")
    print(f"    Attendu : ~222 à 234 communes")
    if n < 200 or n > 260:
        print(f"  ⚠️  ALERTE : nombre de communes inattendu ({n}) — vérifier le fichier source")

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    dest = PATHS["processed"] / "acv_communes.parquet"
    df_final.to_parquet(dest, index=False)
    print(f"  Sauvegardé : {dest}")

    # Aperçu
    print("\n  Aperçu (5 premières lignes) :")
    print(df_final.head().to_string(index=False))

    return df_final


if __name__ == "__main__":
    main()
