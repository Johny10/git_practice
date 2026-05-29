#!/usr/bin/env python3
"""
filter_local_data.py
====================
Script à exécuter LOCALEMENT sur ta machine (pas sur le serveur).

Usage:
    python filter_local_data.py \
        --elections /chemin/vers/general_results.csv \
        --acv /chemin/vers/liste-acv-com2025-20250704.csv \
        --out /chemin/vers/acv-rn-analysis/data/raw/

Le script:
1. Inspecte la structure de general_results.csv (colonnes, premières lignes)
2. Détecte automatiquement le format (par candidat, par liste, ou résumé)
3. Extrait les votes RN/FN pour chaque scrutin ciblé
4. Exporte un petit CSV par scrutin dans data/raw/elections/
5. Copie le fichier ACV dans data/raw/acv/acv_liste_officielle.csv
"""

import argparse
import sys
import os
from pathlib import Path

import pandas as pd
import numpy as np


# ── Scrutins cibles ──────────────────────────────────────────────────────────

SCRUTINS_CIBLES = {
    "pres2012": {"annee": 2012, "tour": 1, "type": "presidentielle"},
    "leg2012":  {"annee": 2012, "tour": 1, "type": "legislatives"},
    "eur2014":  {"annee": 2014, "tour": 1, "type": "europeennes"},
    "pres2017": {"annee": 2017, "tour": 1, "type": "presidentielle"},
    "leg2017":  {"annee": 2017, "tour": 1, "type": "legislatives"},
    "eur2019":  {"annee": 2019, "tour": 1, "type": "europeennes"},
    "pres2022": {"annee": 2022, "tour": 1, "type": "presidentielle"},
    "leg2022":  {"annee": 2022, "tour": 1, "type": "legislatives"},
    "eur2024":  {"annee": 2024, "tour": 1, "type": "europeennes"},
    "leg2024":  {"annee": 2024, "tour": 1, "type": "legislatives"},
}

# Mots-clés pour identifier les lignes/colonnes RN/FN
RN_KEYWORDS = [
    "LE PEN", "LEPEN", "MARINE LE PEN",
    "RASSEMBLEMENT NATIONAL", "FRONT NATIONAL",
    "RN", "FN", "RNP",
]

# Colonnes INSEE commune possibles
INSEE_COLS = [
    "code_commune", "codecommune", "code_insee", "codeinsee",
    "com", "commune", "code_com", "codecom",
    "Code de la commune", "CodeCommune", "code",
    "Code commune", "CodeInsee", "INSEE_COM",
]

# Colonnes de votes possibles
VOTES_COLS = ["voix", "votes", "nb_voix", "nbvoix", "Vote", "Voix"]
EXPRIMES_COLS = [
    "exprimes", "exprimés", "suffrages_exprimes", "total_votes_exprimes",
    "Exprimés", "Exprimes", "suffrages exprimés",
]
INSCRITS_COLS = ["inscrits", "Inscrits", "nb_inscrits", "electeurs_inscrits"]


# ── Utilitaires ──────────────────────────────────────────────────────────────

def normaliser_col(s: str) -> str:
    """Normalise un nom de colonne pour comparaison."""
    import unicodedata
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(" ", "_").replace("-", "_").replace(".", "_")
    return s


def trouver_col(df: pd.DataFrame, candidats: list[str]) -> str | None:
    """Trouve la première colonne dont le nom normalisé matche un candidat."""
    norm_cols = {normaliser_col(c): c for c in df.columns}
    for c in candidats:
        n = normaliser_col(c)
        if n in norm_cols:
            return norm_cols[n]
    return None


def detecter_separateur(chemin: str, n_lignes: int = 5) -> str:
    """Détecte le séparateur CSV (virgule, point-virgule, tabulation)."""
    with open(chemin, "r", encoding="utf-8", errors="replace") as f:
        lignes = [f.readline() for _ in range(n_lignes)]
    sample = "".join(lignes)
    comptages = {",": sample.count(","), ";": sample.count(";"), "\t": sample.count("\t")}
    return max(comptages, key=comptages.get)


def lire_entete(chemin: str, sep: str, n: int = 3) -> pd.DataFrame:
    """Lit les n premières lignes pour inspection."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        try:
            return pd.read_csv(chemin, sep=sep, nrows=n, encoding=enc, low_memory=False)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Impossible de lire {chemin}")


def detecter_encoding(chemin: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            with open(chemin, "r", encoding=enc) as f:
                f.read(10000)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


# ── Formats de données électorales ──────────────────────────────────────────

def est_format_par_candidat(df: pd.DataFrame) -> bool:
    """Format 1 : une ligne par candidat par commune (format MinInt classique)."""
    norm = {normaliser_col(c) for c in df.columns}
    return any(n in norm for n in ["nom", "prenom", "candidat", "liste"])


def est_format_resume(df: pd.DataFrame) -> bool:
    """Format 2 : une ligne par commune, colonnes Voix_RN / Voix_FN."""
    norm = [normaliser_col(c) for c in df.columns]
    return any("rn" in n or "fn" in n or "lepen" in n for n in norm)


def est_format_large(df: pd.DataFrame) -> bool:
    """Format 3 : format large avec colonnes nommées par candidat."""
    for col in df.columns:
        n = normaliser_col(col)
        if any(kw in n for kw in ["lepen", "rassemblement_national", "front_national"]):
            return True
    return False


# ── Extraction par format ────────────────────────────────────────────────────

def extraire_format_par_candidat(df: pd.DataFrame, scrutin: str, info: dict) -> pd.DataFrame | None:
    """
    Format MinInt classique :
    colonnes : Code de la commune | Nom | Prenom | Voix | Exprimés ...
    """
    col_insee = trouver_col(df, INSEE_COLS)
    col_nom = trouver_col(df, ["Nom", "nom", "NOM", "Candidat", "Liste"])
    col_voix = trouver_col(df, VOTES_COLS)
    col_exp = trouver_col(df, EXPRIMES_COLS)
    col_ins = trouver_col(df, INSCRITS_COLS)

    if col_insee is None:
        print(f"  [!] Colonne code_insee non trouvée. Colonnes dispo : {list(df.columns[:20])}")
        return None

    # Filtrer les lignes RN/FN
    if col_nom:
        masque_rn = df[col_nom].astype(str).str.upper().apply(
            lambda x: any(kw in x for kw in RN_KEYWORDS)
        )
        df_rn = df[masque_rn].copy()
    else:
        return None

    if df_rn.empty:
        print(f"  [!] Aucune ligne RN/FN trouvée pour {scrutin}")
        return None

    # Agréger par commune (en cas de multiples candidats RN aux législatives)
    agg = df_rn.groupby(col_insee).agg(
        Voix_RN=(col_voix, "sum") if col_voix else {},
    ).reset_index()

    # Récupérer Exprimés et Inscrits depuis df (non filtré) par commune
    if col_exp:
        exprimes = df.drop_duplicates(col_insee)[[col_insee, col_exp]].copy()
        exprimes.columns = ["code_commune", "Exprimes"]
        agg = agg.rename(columns={col_insee: "code_commune"})
        agg = agg.merge(exprimes, on="code_commune", how="left")
    else:
        agg = agg.rename(columns={col_insee: "code_commune"})
        agg["Exprimes"] = np.nan

    if col_ins:
        inscrits = df.drop_duplicates(col_insee)[[col_insee, col_ins]].copy()
        inscrits.columns = ["code_commune", "Inscrits"]
        agg = agg.merge(inscrits, on="code_commune", how="left")
    else:
        agg["Inscrits"] = np.nan

    agg["scrutin"] = scrutin
    agg["annee"] = info["annee"]
    agg["type_scrutin"] = info["type"]
    return agg[["code_commune", "scrutin", "annee", "type_scrutin", "Voix_RN", "Exprimes", "Inscrits"]]


def extraire_format_resume(df: pd.DataFrame, scrutin: str, info: dict) -> pd.DataFrame | None:
    """
    Format résumé : colonnes directes Voix_RN / part_rn / etc.
    """
    col_insee = trouver_col(df, INSEE_COLS)
    if col_insee is None:
        return None

    # Chercher colonne votes RN
    col_voix_rn = None
    for col in df.columns:
        n = normaliser_col(col)
        if any(kw in n for kw in ["voix_rn", "votes_rn", "voix_fn", "nb_rn", "rn_voix", "fn_voix"]):
            col_voix_rn = col
            break
    # Chercher via keywords RN dans le nom de colonne
    if col_voix_rn is None:
        for col in df.columns:
            n = normaliser_col(col)
            if ("rn" in n or "fn" in n or "lepen" in n) and ("voix" in n or "vote" in n or "nb" in n):
                col_voix_rn = col
                break

    col_exp = trouver_col(df, EXPRIMES_COLS)
    col_ins = trouver_col(df, INSCRITS_COLS)

    if col_voix_rn is None:
        print(f"  [!] Colonne votes RN non trouvée pour {scrutin}. Colonnes : {[c for c in df.columns if 'rn' in c.lower() or 'fn' in c.lower() or 'pen' in c.lower()]}")
        return None

    out = df[[col_insee]].copy()
    out.columns = ["code_commune"]
    out["Voix_RN"] = df[col_voix_rn]
    out["Exprimes"] = df[col_exp] if col_exp else np.nan
    out["Inscrits"] = df[col_ins] if col_ins else np.nan
    out["scrutin"] = scrutin
    out["annee"] = info["annee"]
    out["type_scrutin"] = info["type"]
    return out[["code_commune", "scrutin", "annee", "type_scrutin", "Voix_RN", "Exprimes", "Inscrits"]]


def extraire_format_large(df: pd.DataFrame, scrutin: str, info: dict) -> pd.DataFrame | None:
    """
    Format large : colonnes nommées par candidat/liste.
    """
    col_insee = trouver_col(df, INSEE_COLS)
    if col_insee is None:
        return None

    # Trouver la colonne "Voix" pour RN
    col_voix_rn = None
    for col in df.columns:
        n = normaliser_col(col)
        if any(kw.lower().replace(" ", "_") in n for kw in [
            "rassemblement_national", "front_national", "le_pen", "marine_le_pen", "lepen"
        ]):
            col_voix_rn = col
            break

    col_exp = trouver_col(df, EXPRIMES_COLS)
    col_ins = trouver_col(df, INSCRITS_COLS)

    if col_voix_rn is None:
        return None

    out = df[[col_insee]].copy()
    out.columns = ["code_commune"]
    out["Voix_RN"] = df[col_voix_rn]
    out["Exprimes"] = df[col_exp] if col_exp else np.nan
    out["Inscrits"] = df[col_ins] if col_ins else np.nan
    out["scrutin"] = scrutin
    out["annee"] = info["annee"]
    out["type_scrutin"] = info["type"]
    return out[["code_commune", "scrutin", "annee", "type_scrutin", "Voix_RN", "Exprimes", "Inscrits"]]


# ── Logique principale ────────────────────────────────────────────────────────

def inspecter_colonnes_annee_type(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """Détecte les colonnes annee/type si le fichier est multi-scrutin."""
    annee_col = trouver_col(df, ["annee", "year", "annee_election", "election_year", "an"])
    type_col = trouver_col(df, ["type", "type_election", "scrutin", "election_type", "type_scrutin"])
    return annee_col, type_col


def filtrer_scrutin(df: pd.DataFrame, scrutin: str, info: dict,
                    annee_col: str | None, type_col: str | None) -> pd.DataFrame:
    """Filtre les lignes correspondant à un scrutin donné."""
    if annee_col:
        df = df[df[annee_col].astype(str).str.contains(str(info["annee"]), na=False)]
    if type_col:
        t = info["type"].lower()
        df = df[df[type_col].astype(str).str.lower().str.contains(
            t[:4], na=False  # "pres", "euro", "legi"
        )]
    return df


def traiter_fichier_elections(chemin_csv: str, dossier_out: Path) -> None:
    print(f"\n=== Traitement de {chemin_csv} ===")
    print(f"Taille : {os.path.getsize(chemin_csv) / 1e6:.1f} MB")

    sep = detecter_separateur(chemin_csv)
    enc = detecter_encoding(chemin_csv)
    print(f"Séparateur détecté : {repr(sep)}  |  Encodage : {enc}")

    # Lire l'entête
    df_head = lire_entete(chemin_csv, sep=sep, n=5)
    print(f"\nColonnes ({len(df_head.columns)}) :")
    for i, c in enumerate(df_head.columns):
        print(f"  [{i:3d}] {c!r:40s}  ex: {str(df_head[c].iloc[0])[:60]!r}")

    annee_col, type_col = inspecter_colonnes_annee_type(df_head)
    est_multi = annee_col is not None
    print(f"\nFichier multi-scrutin : {'oui' if est_multi else 'non'}")
    if annee_col:
        print(f"  Colonne année : {annee_col!r}")
    if type_col:
        print(f"  Colonne type  : {type_col!r}")

    # Lire le fichier complet par chunks pour économiser la RAM
    chunks_par_scrutin: dict[str, list[pd.DataFrame]] = {s: [] for s in SCRUTINS_CIBLES}
    total_lignes = 0
    CHUNK = 200_000

    print(f"\nLecture en chunks de {CHUNK:,} lignes ...")
    reader = pd.read_csv(chemin_csv, sep=sep, encoding=enc, chunksize=CHUNK,
                         low_memory=False, dtype=str)

    for i, chunk in enumerate(reader):
        total_lignes += len(chunk)
        print(f"  Chunk {i+1} : {len(chunk):,} lignes (total {total_lignes:,})", end="\r")

        for scrutin, info in SCRUTINS_CIBLES.items():
            sous = filtrer_scrutin(chunk.copy(), scrutin, info, annee_col, type_col)
            if len(sous) > 0:
                chunks_par_scrutin[scrutin].append(sous)

    print(f"\nTotal lignes lues : {total_lignes:,}")

    # Traiter chaque scrutin
    for scrutin, info in SCRUTINS_CIBLES.items():
        morceaux = chunks_par_scrutin[scrutin]
        if not morceaux:
            if not est_multi:
                # Fichier mono-scrutin : lire tout
                df_s = pd.read_csv(chemin_csv, sep=sep, encoding=enc, low_memory=False, dtype=str)
            else:
                print(f"\n[!] {scrutin} : aucune donnée trouvée, scrutin ignoré")
                continue
        else:
            df_s = pd.concat(morceaux, ignore_index=True)

        print(f"\n{scrutin} : {len(df_s):,} lignes brutes")

        # Convertir les colonnes numériques
        for col in df_s.columns:
            try:
                df_s[col] = pd.to_numeric(df_s[col], errors="ignore")
            except Exception:
                pass

        # Détecter le format et extraire
        result = None
        if est_format_par_candidat(df_s):
            print(f"  Format détecté : par candidat")
            result = extraire_format_par_candidat(df_s, scrutin, info)
        elif est_format_resume(df_s):
            print(f"  Format détecté : résumé (colonnes RN directes)")
            result = extraire_format_resume(df_s, scrutin, info)
        elif est_format_large(df_s):
            print(f"  Format détecté : large (colonnes par parti)")
            result = extraire_format_large(df_s, scrutin, info)
        else:
            print(f"  [!] Format non reconnu. Colonnes : {list(df_s.columns[:30])}")
            continue

        if result is None or result.empty:
            print(f"  [!] Extraction échouée pour {scrutin}")
            continue

        # Sauvegarder
        chemin_out = dossier_out / "elections" / f"{scrutin}_communes.csv"
        chemin_out.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(chemin_out, index=False)
        taille = chemin_out.stat().st_size / 1e3
        print(f"  ✓ {len(result):,} communes → {chemin_out.name}  ({taille:.0f} KB)")


def traiter_fichier_acv(chemin_csv: str, dossier_out: Path) -> None:
    print(f"\n=== Traitement ACV : {chemin_csv} ===")
    sep = detecter_separateur(chemin_csv)
    enc = detecter_encoding(chemin_csv)
    df = pd.read_csv(chemin_csv, sep=sep, encoding=enc, low_memory=False)
    print(f"{len(df):,} lignes, {len(df.columns)} colonnes")
    print("Colonnes :", list(df.columns))
    print(df.head(3).to_string())

    chemin_out = dossier_out / "acv" / "acv_liste_officielle.csv"
    chemin_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(chemin_out, index=False)
    print(f"✓ Sauvegardé → {chemin_out}  ({chemin_out.stat().st_size/1e3:.0f} KB)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Filtre les données brutes pour acv-rn-analysis")
    parser.add_argument("--elections", required=True,
                        help="Chemin vers general_results.csv (405 MB)")
    parser.add_argument("--acv", required=False, default=None,
                        help="Chemin vers liste-acv-com2025-*.csv (optionnel)")
    parser.add_argument("--out", required=True,
                        help="Dossier data/raw/ du projet")
    args = parser.parse_args()

    dossier_out = Path(args.out)

    if args.acv:
        traiter_fichier_acv(args.acv, dossier_out)

    traiter_fichier_elections(args.elections, dossier_out)

    print("\n=== Terminé ===")
    print(f"Fichiers produits dans {dossier_out}/elections/")
    print("Étape suivante : git add data/raw/ && git commit && git push")


if __name__ == "__main__":
    main()
