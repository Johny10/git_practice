################################################################################
# 03_clean_elections.py
# Nettoyage des résultats électoraux du Ministère de l'Intérieur
# Input  : data/raw/elections/  (un fichier par scrutin)
# Output : data/processed/elections_panel.parquet
#          Colonnes : code_insee, scrutin, annee, part_rn (0-1), voix_rn,
#                     exprimes, inscrits
################################################################################

import sys
import re
import warnings
import pandas as pd
import numpy as np
from pathlib import Path

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, SCRUTINS, RN_LABELS, SEED

np.random.seed(SEED)

# ── Noms de fichiers attendus ─────────────────────────────────────────────────
FICHIERS_ELECTIONS = {
    "pres2012": ["pres2012_t1_communes.csv", "Presidentielle_2012_T1.csv",
                 "presidentielle2012_t1.csv", "resultats_pres_2012_t1.csv"],
    "leg2012":  ["leg2012_t1_communes.csv", "Legislatives_2012_T1.csv"],
    "eur2014":  ["eur2014_communes.csv", "Europeennes_2014.csv", "europeennes2014.csv"],
    "pres2017": ["pres2017_t1_communes.csv", "Presidentielle_2017_T1.csv"],
    "leg2017":  ["leg2017_t1_communes.csv", "Legislatives_2017_T1.csv"],
    "eur2019":  ["eur2019_communes.csv", "Europeennes_2019.csv", "europeennes2019.csv"],
    "pres2022": ["pres2022_t1_communes.csv", "Presidentielle_2022_T1.csv"],
    "leg2022":  ["leg2022_t1_communes.csv", "Legislatives_2022_T1.csv"],
    "eur2024":  ["eur2024_communes.csv", "Europeennes_2024.csv"],
    "leg2024":  ["leg2024_t1_communes.csv", "Legislatives_2024_T1.csv"],
}


def trouver_fichier(scrutin: str, dossier: Path) -> Path | None:
    """Recherche un fichier de scrutin dans le dossier (noms alternatifs)."""
    noms_candidats = FICHIERS_ELECTIONS.get(scrutin, [])
    for nom in noms_candidats:
        p = dossier / nom
        if p.exists():
            return p
    # Recherche par glob approximatif
    for pattern in [f"*{scrutin}*", f"*{scrutin[:4]}*{scrutin[4:]}*"]:
        found = list(dossier.glob(pattern))
        if found:
            return found[0]
    return None


def charger_csv_interieur(fichier: Path) -> pd.DataFrame:
    """Charge un fichier du Ministère de l'Intérieur, teste les encodages et séparateurs."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        for sep in [";", ",", "\t"]:
            try:
                df = pd.read_csv(fichier, sep=sep, encoding=encoding,
                                 dtype=str, low_memory=False)
                if df.shape[1] > 3:
                    return df
            except Exception:
                continue
    raise ValueError(f"Impossible de lire {fichier}")


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


def detecter_col_insee(cols: list) -> str | None:
    """Identifie la colonne code INSEE parmi les colonnes du fichier."""
    candidats = [c for c in cols if any(kw in c.lower() for kw in
                 ["codinsee", "codecommune", "code_com", "codgeo", "insee",
                  "com_arm", "code_de_la_commune", "code commune"])]
    return candidats[0] if candidats else None


def detecter_col_exprimes(cols: list) -> str | None:
    candidats = [c for c in cols if any(kw in c.lower() for kw in
                 ["exprimes", "exprimés", "nb_exprimes", "voix_exprimes",
                  "suffrages_exprimes", "nbre_exprimes"])]
    return candidats[0] if candidats else None


def detecter_col_inscrits(cols: list) -> str | None:
    candidats = [c for c in cols if any(kw in c.lower() for kw in
                 ["inscrits", "nb_inscrits", "nbre_inscrits"])]
    return candidats[0] if candidats else None


def extraire_voix_rn_presidentielle(df: pd.DataFrame, annee: int) -> pd.DataFrame:
    """
    Extrait les voix RN/FN pour une présidentielle.
    Formats Ministère de l'Intérieur : format 'large' avec un bloc par candidat.
    Chaque candidat a des colonnes : Nom, Prénom, Voix, % Voix/Ins, % Voix/Exp
    """
    cols = list(df.columns)
    cols_lower = [c.lower().strip() for c in cols]

    # Chercher les colonnes contenant les noms de candidats
    noms_rn = [n.upper() for n in RN_LABELS.get(annee, [])]

    # Approche 1 : colonnes nommées explicitement par candidat
    # Format : "Nom candidat1", "Voix candidat1", ...
    col_voix_rn = None

    # Recherche d'une colonne "voix" adjacente à une colonne "nom" contenant LE PEN
    for i, col in enumerate(cols):
        val_sample = df[col].dropna().head(50).str.upper()
        if any(any(nom in str(v) for nom in noms_rn) for v in val_sample):
            # Chercher "voix" dans les colonnes proches
            for j in range(max(0, i-3), min(len(cols), i+6)):
                if any(kw in cols[j].lower() for kw in ["voix", "votes", "nb_voi"]):
                    col_voix_rn = cols[j]
                    print(f"    → Voix RN détectée : col '{cols[j]}' (près de '{col}')")
                    break
            if col_voix_rn:
                break

    # Approche 2 : colonnes nommées directement "Voix_LE_PEN" etc.
    if col_voix_rn is None:
        for col in cols:
            col_up = col.upper()
            if "VOIX" in col_up and any(nom in col_up for nom in noms_rn):
                col_voix_rn = col
                print(f"    → Voix RN par nom de colonne : '{col}'")
                break

    # Approche 3 : format long — colonne "Voix" avec ligne filtrée sur nom candidat
    if col_voix_rn is None:
        col_nom = next((c for c in cols if "nom" in c.lower()
                        and "commune" not in c.lower()), None)
        col_voix_gen = next((c for c in cols if c.lower().strip() in
                             ["voix", "nb_voix", "nbre_voix"]), None)
        if col_nom and col_voix_gen:
            masque_rn = df[col_nom].str.upper().str.contains(
                "|".join(noms_rn), na=False
            )
            if masque_rn.sum() > 0:
                print(f"    → Format long détecté, filtre sur '{col_nom}'")
                df_rn = df[masque_rn].copy()
                df_rn["voix_rn"] = pd.to_numeric(df_rn[col_voix_gen]
                                                   .str.replace(" ", ""), errors="coerce")
                return df_rn

    if col_voix_rn is None:
        print(f"    ⚠️  Voix RN introuvables — colonnes : {cols[:15]}...")
        return pd.DataFrame()

    df["voix_rn"] = pd.to_numeric(
        df[col_voix_rn].str.replace(" ", "").str.replace(",", "."),
        errors="coerce"
    )
    return df


def extraire_voix_rn_europeennes(df: pd.DataFrame, scrutin: str) -> pd.DataFrame:
    """
    Extrait les voix RN pour une européenne.
    Cherche la liste RN dans colonnes ou valeurs.
    """
    cols = list(df.columns)
    labels_rn = RN_LABELS.get(scrutin, ["RASSEMBLEMENT NATIONAL", "FRONT NATIONAL", "RN", "FN"])
    labels_rn_upper = [l.upper() for l in labels_rn]

    # Chercher colonne liste/panneau avec valeur RN
    col_liste = next((c for c in cols if any(kw in c.lower() for kw in
                     ["liste", "panneau", "label", "libelle_liste", "nuance"])), None)
    col_voix = next((c for c in cols if any(kw in c.lower() for kw in
                    ["voix", "votes", "nb_voix"])), None)

    if col_liste and col_voix:
        masque = df[col_liste].str.upper().str.contains(
            "|".join(labels_rn_upper), na=False
        )
        if masque.sum() > 0:
            df_rn = df[masque].copy()
            df_rn["voix_rn"] = pd.to_numeric(
                df_rn[col_voix].str.replace(" ", ""), errors="coerce"
            )
            print(f"    → Européennes : {masque.sum()} lignes RN trouvées sur '{col_liste}'")
            return df_rn

    # Colonnes directement nommées avec un label RN (ex: "Voix_RN", "Voix_RASSEMBLEMENT NATIONAL")
    for col in cols:
        col_up = col.upper()
        if "VOIX" in col_up and any(lbl in col_up for lbl in labels_rn_upper):
            df["voix_rn"] = pd.to_numeric(
                df[col].str.replace(" ", ""), errors="coerce"
            )
            print(f"    → Voix RN/FN par colonne : '{col}'")
            return df

    # Fallback : colonne générique "Voix_RN" (format test ou variante MI)
    col_voix_rn_generic = next(
        (c for c in cols if c.upper().replace("_", "").replace(" ", "") in
         ("VOIXRN", "VOIXFN", "NBVOIXRN", "VOTERN")), None
    )
    if col_voix_rn_generic:
        df["voix_rn"] = pd.to_numeric(df[col_voix_rn_generic].str.replace(" ", ""),
                                       errors="coerce")
        print(f"    → Voix RN générique : '{col_voix_rn_generic}'")
        return df

    # Fallback : valeurs de col_voix associées à un nom RN dans une colonne nom
    col_nom = next((c for c in cols if "nom" in c.lower()
                    and "commune" not in c.lower()), None)
    if col_nom and col_voix:
        masque = df[col_nom].astype(str).str.upper().str.contains(
            "|".join(["LE PEN", "RN", "RASSEMBLEMENT", "FRONT NATIONAL"]), na=False
        )
        if masque.sum() > 0:
            df_rn = df[masque].copy()
            df_rn["voix_rn"] = pd.to_numeric(
                df_rn[col_voix].astype(str).str.replace(" ", ""), errors="coerce"
            )
            print(f"    → Européennes fallback nom : {masque.sum()} lignes sur '{col_nom}'")
            return df_rn

    print(f"    ⚠️  Voix RN introuvables pour {scrutin} — colonnes : {cols[:15]}...")
    return pd.DataFrame()


def extraire_voix_rn_legislatives(df: pd.DataFrame) -> pd.DataFrame:
    """
    Législatives : identifie les candidats avec nuance RN/FN.
    """
    cols = list(df.columns)
    nuances_rn = RN_LABELS.get("leg_nuances", ["RN", "FN", "RNP"])

    col_nuance = next((c for c in cols if "nuance" in c.lower()), None)
    col_voix = next((c for c in cols if any(kw in c.lower() for kw in
                    ["voix", "nb_voix"])), None)

    if col_nuance and col_voix:
        masque = df[col_nuance].str.upper().isin([n.upper() for n in nuances_rn])
        df_rn = df[masque].copy()
        df_rn["voix_rn"] = pd.to_numeric(
            df_rn[col_voix].str.replace(" ", ""), errors="coerce"
        )
        print(f"    → Législatives : {masque.sum()} candidats RN sur nuance")
        return df_rn

    print(f"    ⚠️  Nuances RN introuvables — colonnes : {cols[:15]}...")
    return pd.DataFrame()


def agreger_par_commune(df_rn: pd.DataFrame, df_tot: pd.DataFrame,
                         col_insee: str, col_exprimes: str,
                         col_inscrits: str | None) -> pd.DataFrame:
    """
    Pour les législatives (plusieurs candidats RN par commune) :
    somme les voix RN par commune, merge avec totaux exprimés.
    """
    agg = (df_rn.groupby(col_insee)["voix_rn"]
           .sum().reset_index().rename(columns={col_insee: "code_insee"}))
    agg["code_insee"] = normaliser_code_insee(agg["code_insee"])

    totaux = df_tot.copy()
    totaux["code_insee"] = normaliser_code_insee(totaux[col_insee])
    totaux["exprimes"] = pd.to_numeric(
        totaux[col_exprimes].str.replace(" ", ""), errors="coerce"
    )
    if col_inscrits:
        totaux["inscrits"] = pd.to_numeric(
            totaux[col_inscrits].str.replace(" ", ""), errors="coerce"
        )
    else:
        totaux["inscrits"] = np.nan

    totaux_agg = totaux.groupby("code_insee")[
        ["exprimes"] + (["inscrits"] if col_inscrits else [])
    ].sum().reset_index()

    merged = agg.merge(totaux_agg, on="code_insee", how="left")
    return merged


def traiter_scrutin(scrutin: str, dossier: Path) -> pd.DataFrame | None:
    """Traite un scrutin complet → renvoie un DataFrame normalisé."""
    annee = SCRUTINS[scrutin]["annee"]
    type_scrutin = SCRUTINS[scrutin]["type"]

    fichier = trouver_fichier(scrutin, dossier)
    if fichier is None:
        print(f"  ⚠️  FICHIER MANQUANT : {scrutin} → voir TELECHARGEMENTS_MANUELS.md")
        return None

    print(f"\n  [{scrutin}] Fichier : {fichier.name}")
    df_raw = charger_csv_interieur(fichier)
    print(f"    Dimensions brutes : {df_raw.shape}")

    # Nettoyage colonnes
    df_raw.columns = df_raw.columns.str.strip()

    col_insee = detecter_col_insee(list(df_raw.columns))
    col_exprimes = detecter_col_exprimes(list(df_raw.columns))
    col_inscrits = detecter_col_inscrits(list(df_raw.columns))

    if col_insee is None:
        print(f"    ❌ Code INSEE introuvable — colonnes : {list(df_raw.columns)[:10]}")
        return None
    if col_exprimes is None:
        print(f"    ❌ Suffrages exprimés introuvables")
        return None

    # Extraction voix RN selon type de scrutin
    if type_scrutin == "presidentielle":
        df_rn = extraire_voix_rn_presidentielle(df_raw.copy(), annee)
    elif type_scrutin == "europeennes":
        df_rn = extraire_voix_rn_europeennes(df_raw.copy(), scrutin)
    else:
        df_rn = extraire_voix_rn_legislatives(df_raw.copy())

    if df_rn.empty:
        return None

    # Agrégation par commune
    result = agreger_par_commune(
        df_rn, df_raw, col_insee, col_exprimes, col_inscrits
    )

    if result.empty:
        return None

    # Calcul part RN
    result["voix_rn"]    = pd.to_numeric(result["voix_rn"], errors="coerce")
    result["exprimes"]   = pd.to_numeric(result["exprimes"], errors="coerce")
    result["part_rn"]    = result["voix_rn"] / result["exprimes"]

    # Sanity check
    n_invalide = (result["part_rn"] > 1).sum() + (result["part_rn"] < 0).sum()
    if n_invalide > 0:
        print(f"    ⚠️  {n_invalide} communes avec part_rn hors [0,1] — set NaN")
        result.loc[(result["part_rn"] > 1) | (result["part_rn"] < 0), "part_rn"] = np.nan

    result["scrutin"] = scrutin
    result["annee"]   = annee

    n_communes = result["code_insee"].notna().sum()
    n_rn_ok    = result["part_rn"].notna().sum()
    print(f"    ✓ {n_communes} communes | part_rn renseignée pour {n_rn_ok} ({n_rn_ok/n_communes:.1%})")
    print(f"      Médiane part_rn = {result['part_rn'].median():.3f}")

    return result[["code_insee", "scrutin", "annee", "voix_rn",
                   "exprimes", "inscrits", "part_rn"]]


# ── Pipeline principal ────────────────────────────────────────────────────────

def main():
    print("\n=== 03_clean_elections.py ===")

    dossier = PATHS["raw_elections"]
    manquants = []
    panels = []

    for scrutin in SCRUTINS.keys():
        df = traiter_scrutin(scrutin, dossier)
        if df is not None:
            panels.append(df)
        else:
            manquants.append(scrutin)

    if not panels:
        raise RuntimeError(
            "\n❌ AUCUN fichier électoral disponible.\n"
            "   Voir TELECHARGEMENTS_MANUELS.md pour la liste des URLs à télécharger."
        )

    # Empilage
    panel = pd.concat(panels, ignore_index=True)
    panel = panel.dropna(subset=["code_insee"])
    panel = panel[panel["code_insee"].str.match(r"^(\d{5}|2[AB]\d{3})$", na=False)]

    print(f"\n  Panel électoral : {panel.shape[0]} obs | {panel['code_insee'].nunique()} communes")
    print(f"  Scrutins disponibles : {sorted(panel['scrutin'].unique())}")

    if manquants:
        print(f"\n  ⚠️  SCRUTINS MANQUANTS ({len(manquants)}) : {manquants}")
        print("     → Voir TELECHARGEMENTS_MANUELS.md")

    dest = PATHS["processed"] / "elections_panel.parquet"
    panel.to_parquet(dest, index=False)
    print(f"\n  Sauvegardé : {dest}")

    return panel


if __name__ == "__main__":
    main()
