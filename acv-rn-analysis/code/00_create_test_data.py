################################################################################
# 00_create_test_data.py
# Génère des données synthétiques réalistes pour valider le pipeline end-to-end.
# ATTENTION : CES DONNÉES SONT FICTIVES. Elles servent uniquement à tester que
# le code fonctionne. Remplacer par les vraies données (voir TELECHARGEMENTS_MANUELS.md)
# avant toute analyse substantielle.
#
# Structure reproduit fidèlement les formats officiels :
#   - Liste ACV : format Caisse des Dépôts
#   - Résultats électoraux : format Ministère de l'Intérieur (présidentielle)
#   - INSEE : format populations légales + Filosofi
################################################################################

import sys
import numpy as np
import pandas as pd
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from setup import PATHS, SEED, SCRUTINS

np.random.seed(SEED)
rng = np.random.default_rng(SEED)

print("=" * 60)
print("  GÉNÉRATION DE DONNÉES SYNTHÉTIQUES (TEST UNIQUEMENT)")
print("=" * 60)

# ── Paramètres du DGP (data-generating process) ──────────────────────────────
N_TRAITES   = 222    # villes ACV
N_CONTROLES = 500    # villes moyennes non-ACV
ATT_VRAI    = -0.02  # effet causal simulé : -2 pp sur part RN
BRUIT_STD   = 0.03   # bruit idiosyncratique

# ── 1. Génération des communes ────────────────────────────────────────────────

# Départements métropolitains (hors 75, 92, 93, 94)
depts = [f"{i:02d}" for i in range(1, 96) if i not in (75, 92, 93, 94)]
depts += ["2A", "2B"]

def gen_code_insee(dept: str, n: int) -> list:
    if dept in ("2A", "2B"):
        nums = rng.integers(1, 350, size=n)
        return [f"{dept}{x:03d}" for x in nums]
    d = int(dept)
    nums = rng.integers(1, 600, size=n)
    return [f"{d:02d}{x:03d}" for x in nums]

# Pool total de villes moyennes
n_total = N_TRAITES + N_CONTROLES
depts_sample = rng.choice(depts, size=n_total, replace=True)

codes = []
for d in depts_sample:
    codes.append(gen_code_insee(d, 1)[0])

# Dédupliquer
codes = list(dict.fromkeys(codes))[:n_total]
if len(codes) < n_total:
    extra = [f"99{i:03d}" for i in range(n_total - len(codes))]
    codes += extra

codes_traites  = codes[:N_TRAITES]
codes_controles = codes[N_TRAITES:N_TRAITES + N_CONTROLES]
tous_codes = codes_traites + codes_controles

# Noms communes fictifs (pour lisibilité)
prefixes = ["Ville", "Bourg", "Saint", "Sainte", "Le", "La", "Les"]
suffixes = ["sur-Loire", "en-Provence", "lès-Bains", "du-Midi",
            "les-Pins", "sur-Mer", "la-Forêt"]
noms = [f"{rng.choice(prefixes)}-{chr(65+i%26)}{i // 26}-{rng.choice(suffixes)}"
        for i in range(len(tous_codes))]

# ── 2. Caractéristiques socio-économiques ─────────────────────────────────────

# Traités : sélection légèrement biaisée (villes plus déclassées)
# Contrôle : villes proches mais légèrement mieux loties
population_t = rng.integers(22_000, 95_000, size=N_TRAITES).astype(float)
population_c = rng.integers(20_000, 100_000, size=N_CONTROLES).astype(float)

rev_t = rng.normal(19_500, 2_500, N_TRAITES).clip(14_000, 28_000)
rev_c = rng.normal(20_500, 3_000, N_CONTROLES).clip(14_000, 30_000)

chom_t = rng.normal(13.5, 2.5, N_TRAITES).clip(5, 25)
chom_c = rng.normal(11.5, 3.0, N_CONTROLES).clip(4, 22)

cadres_t = rng.normal(12, 3, N_TRAITES).clip(4, 30)
cadres_c = rng.normal(14, 4, N_CONTROLES).clip(4, 35)

ouvriers_t = rng.normal(25, 5, N_TRAITES).clip(8, 45)
ouvriers_c = rng.normal(22, 6, N_CONTROLES).clip(6, 42)

# Propension de base au vote RN (liée aux covariates)
def rn_base(chom, rev, ouvriers):
    return (0.20 + 0.008 * chom - 0.000005 * rev + 0.004 * ouvriers).clip(0.05, 0.60)

rn_base_t = rn_base(chom_t, rev_t, ouvriers_t)
rn_base_c = rn_base(chom_c, rev_c, ouvriers_c)

# ── 3. Résultats électoraux par scrutin ───────────────────────────────────────

def gen_election(codes_t, codes_c, rn_base_t, rn_base_c,
                 annee: int, scrutin: str,
                 post: bool = False,
                 att: float = 0.0) -> pd.DataFrame:
    """
    Génère un fichier CSV au format Ministère de l'Intérieur (présidentielle).
    Post=True et att<0 → effet ACV simulé.
    """
    n_t = len(codes_t)
    n_c = len(codes_c)

    # Bruit temporel commun (trend global du vote RN)
    trend = {2012: 0.00, 2014: 0.03, 2017: 0.06, 2019: 0.08, 2022: 0.12, 2024: 0.14}
    t_eff = trend.get(annee, 0.0)

    rn_t = (rn_base_t + t_eff + (att if post else 0)
            + rng.normal(0, BRUIT_STD, n_t)).clip(0.02, 0.85)
    rn_c = (rn_base_c + t_eff
            + rng.normal(0, BRUIT_STD, n_c)).clip(0.02, 0.85)

    def faire_lignes(codes, rn_vals):
        rows = []
        for code, rn in zip(codes, rn_vals):
            inscrits  = int(rng.integers(15_000, 80_000))
            particip  = rng.uniform(0.55, 0.80)
            votants   = int(inscrits * particip)
            blancs    = int(votants * rng.uniform(0.01, 0.04))
            exprimes  = votants - blancs
            voix_rn   = int(exprimes * rn)
            voix_aut  = exprimes - voix_rn  # simplifié
            rows.append({
                "Code du département": code[:2],
                "Code de la commune": code[2:],
                "Code INSEE": code,
                "Libellé de la commune": f"Commune_{code}",
                "Inscrits": inscrits,
                "Abstentions": inscrits - votants,
                "Votants": votants,
                "Blancs": blancs,
                "Nuls": 0,
                "Exprimés": exprimes,
                "Nom_candidat_RN": "LE PEN" if "pres" in scrutin else "RASSEMBLEMENT NATIONAL",
                "Prénom_candidat_RN": "Marine" if "pres" in scrutin else "",
                "Voix_RN": voix_rn,
                "Pct_RN_exp": round(rn * 100, 2),
                "Nom_candidat_2": "MACRON",
                "Voix_candidat_2": voix_aut,
            })
        return rows

    lignes = faire_lignes(codes_t, rn_t) + faire_lignes(codes_c, rn_c)
    df = pd.DataFrame(lignes)
    return df


# Scrutins à générer
scrutins_config = [
    ("pres2012", 2012, False),
    ("eur2014",  2014, False),
    ("pres2017", 2017, False),
    ("eur2019",  2019, True),   # post-ACV
    ("pres2022", 2022, True),
    ("eur2024",  2024, True),
]

print(f"\n  Génération de {len(scrutins_config)} scrutins × {len(tous_codes)} communes...")

for scrutin, annee, post in scrutins_config:
    df = gen_election(codes_traites, codes_controles,
                      rn_base_t, rn_base_c,
                      annee, scrutin, post=post, att=ATT_VRAI)
    dest = PATHS["raw_elections"] / f"{scrutin}_communes.csv"
    df.to_csv(dest, index=False, sep=";")
    n = len(df)
    print(f"  ✓ {scrutin} : {n} communes → {dest.name}")

# ── 4. Liste ACV ──────────────────────────────────────────────────────────────

df_acv = pd.DataFrame({
    "code_insee": codes_traites,
    "nom_commune": noms[:N_TRAITES],
    "departement": [c[:2] for c in codes_traites],
    "region": rng.choice(
        ["Bretagne", "Normandie", "Hauts-de-France", "Grand Est",
         "Bourgogne-Franche-Comté", "Centre-Val de Loire", "Nouvelle-Aquitaine",
         "Occitanie", "Auvergne-Rhône-Alpes", "Provence-Alpes-Côte d'Azur",
         "Pays de la Loire", "Île-de-France"],
        size=N_TRAITES
    ),
    "est_binome": rng.choice([True, False], size=N_TRAITES, p=[0.08, 0.92]),
    "annee_selection": 2018,
})

dest_acv = PATHS["raw_acv"] / "acv_liste_officielle.csv"
df_acv.to_csv(dest_acv, index=False, sep=";")
print(f"\n  ✓ Liste ACV : {len(df_acv)} villes → {dest_acv.name}")

# ── 5. Données INSEE ──────────────────────────────────────────────────────────

# Populations légales
pop_rows = []
for annee in [2012, 2014, 2016, 2017, 2018]:
    for i, code in enumerate(tous_codes):
        if i < N_TRAITES:
            base = population_t[i]
        else:
            base = population_c[i - N_TRAITES]
        pop = int(base * rng.uniform(0.97, 1.03))
        pop_rows.append({"CODGEO": code, "PMUN": pop, "annee": annee})

df_pop = pd.DataFrame(pop_rows)
dest_pop = PATHS["raw_insee"] / "populations_legales_2017.csv"
df_pop[df_pop["annee"] == 2017].to_csv(dest_pop, index=False, sep=";")
print(f"  ✓ Populations légales 2017 : {len(df_pop[df_pop['annee']==2017])} communes → {dest_pop.name}")

# Aussi une version multi-années
dest_pop_all = PATHS["raw_insee"] / "populations_legales_multi.csv"
df_pop.to_csv(dest_pop_all, index=False, sep=";")

# Filosofi — revenu médian
filo_rows = []
for annee in [2012, 2015, 2017]:
    for i, code in enumerate(tous_codes):
        if i < N_TRAITES:
            rev = rev_t[i] * rng.uniform(0.97, 1.03)
        else:
            rev = rev_c[i - N_TRAITES] * rng.uniform(0.97, 1.03)
        filo_rows.append({"CODGEO": code, "Q2": round(rev, 0), "annee": annee})

df_filo = pd.DataFrame(filo_rows)
dest_filo = PATHS["raw_insee"] / "filosofi_2017.csv"
df_filo[df_filo["annee"] == 2017].to_csv(dest_filo, index=False, sep=";")
print(f"  ✓ Filosofi 2017 : {len(df_filo[df_filo['annee']==2017])} communes → {dest_filo.name}")

# Recensement population — emploi/CSP
rp_rows = []
for i, code in enumerate(tous_codes):
    if i < N_TRAITES:
        chom = chom_t[i]
        cadr = cadres_t[i]
        ouvr = ouvriers_t[i]
    else:
        chom = chom_c[i - N_TRAITES]
        cadr = cadres_c[i - N_TRAITES]
        ouvr = ouvriers_c[i - N_TRAITES]
    rp_rows.append({
        "CODGEO": code,
        "taux_chomage": round(chom, 2),
        "part_cadres": round(cadr, 2),
        "part_ouvriers": round(ouvr, 2),
        "annee": 2017,
    })

df_rp = pd.DataFrame(rp_rows)
dest_rp = PATHS["raw_insee"] / "rp2017_commune.csv"
df_rp.to_csv(dest_rp, index=False, sep=";")
print(f"  ✓ RP 2017 emploi/CSP : {len(df_rp)} communes → {dest_rp.name}")

# ── Bilan ─────────────────────────────────────────────────────────────────────

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  DONNÉES SYNTHÉTIQUES GÉNÉRÉES                               ║
║                                                              ║
║  ⚠️  FICTIVES — NE PAS UTILISER POUR PUBLICATION            ║
║                                                              ║
║  DGP simulé :                                                ║
║    ATT vrai       = {ATT_VRAI*100:+.1f} pp (réduit vote RN)          ║
║    Communes ACV   = {N_TRAITES}                                      ║
║    Communes ctrl  = {N_CONTROLES}                                      ║
║    Scrutins       = {len(scrutins_config)}                                        ║
║                                                              ║
║  Pour les vraies données → TELECHARGEMENTS_MANUELS.md        ║
╚══════════════════════════════════════════════════════════════╝
""")
