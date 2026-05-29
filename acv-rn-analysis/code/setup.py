################################################################################
# setup.py
# Initialisation globale : chemins, constantes, utilitaires communs
# Importé par tous les autres scripts via : from setup import *
################################################################################

import os
import sys
import random
import numpy as np
import pandas as pd
from pathlib import Path

# ── Reproductibilité ──────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)
np.random.seed(SEED)

# ── Racine du projet ─────────────────────────────────────────────────────────
# Ce fichier est dans acv-rn-analysis/code/ → parent().parent() = racine projet
PROJ_ROOT = Path(__file__).resolve().parent.parent

# ── Chemins ──────────────────────────────────────────────────────────────────
PATHS = {
    "raw":       PROJ_ROOT / "data" / "raw",
    "processed": PROJ_ROOT / "data" / "processed",
    "code":      PROJ_ROOT / "code",
    "tables":    PROJ_ROOT / "output" / "tables",
    "figures":   PROJ_ROOT / "output" / "figures",
    "paper":     PROJ_ROOT / "paper",
}
PATHS["raw_acv"]       = PATHS["raw"] / "acv"
PATHS["raw_elections"] = PATHS["raw"] / "elections"
PATHS["raw_insee"]     = PATHS["raw"] / "insee"
PATHS["raw_geo"]       = PATHS["raw"] / "geo"

for p in PATHS.values():
    p.mkdir(parents=True, exist_ok=True)

# ── Constantes du design ──────────────────────────────────────────────────────
POP_MIN          = 20_000
POP_MAX          = 100_000
ANNEE_TRAITEMENT = 2018
ANNEE_DEBUT      = 2012
ANNEE_FIN_MAIN   = 2019
ANNEE_FIN_EXT    = 2024

# Départements exclus (Paris + petite couronne)
DEPT_EXCL_IDF_PC = {"75", "92", "93", "94"}

# Scrutins du projet
SCRUTINS = {
    "pres2012": {"annee": 2012, "type": "presidentielle", "label": "Présidentielle 2012 T1"},
    "leg2012":  {"annee": 2012, "type": "legislatives",   "label": "Législatives 2012 T1"},
    "eur2014":  {"annee": 2014, "type": "europeennes",    "label": "Européennes 2014"},
    "pres2017": {"annee": 2017, "type": "presidentielle", "label": "Présidentielle 2017 T1"},
    "leg2017":  {"annee": 2017, "type": "legislatives",   "label": "Législatives 2017 T1"},
    "eur2019":  {"annee": 2019, "type": "europeennes",    "label": "Européennes 2019"},
    "pres2022": {"annee": 2022, "type": "presidentielle", "label": "Présidentielle 2022 T1"},
    "leg2022":  {"annee": 2022, "type": "legislatives",   "label": "Législatives 2022 T1"},
    "eur2024":  {"annee": 2024, "type": "europeennes",    "label": "Européennes 2024"},
    "leg2024":  {"annee": 2024, "type": "legislatives",   "label": "Législatives 2024 T1"},
}

SCRUTINS_PRINCIPAUX = ["pres2012", "eur2014", "pres2017", "eur2019"]
SCRUTINS_EXTENSION  = ["pres2022", "leg2022", "eur2024", "leg2024"]

# Identifiants RN/FN selon scrutin (pour extraction automatique)
RN_LABELS = {
    2012: ["LE PEN", "Marine LE PEN", "Le Pen Marine"],
    2017: ["LE PEN", "Marine LE PEN", "Le Pen Marine"],
    2022: ["LE PEN", "Marine LE PEN", "Le Pen Marine"],
    "eur2014": ["FRONT NATIONAL", "FN", "Marine LE PEN"],
    "eur2019": ["RASSEMBLEMENT NATIONAL", "RN"],
    "eur2024": ["RASSEMBLEMENT NATIONAL", "RN"],
    "leg_nuances": ["RN", "FN", "RNP"],
}

# ── Pandas options ────────────────────────────────────────────────────────────
pd.set_option("display.max_columns", 50)
pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:.4f}".format)
