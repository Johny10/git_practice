################################################################################
# 00_setup.R
# Initialisation de l'environnement R : packages, chemins, options globales
################################################################################

set.seed(42)

# ── 1. Gestion de l'environnement avec renv ──────────────────────────────────
# Si renv est disponible, l'utiliser ; sinon installer les packages directement
if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages("renv")
}

# ── 2. Packages requis ───────────────────────────────────────────────────────
required_packages <- c(
  # DiD et économétrie
  "did",            # Callaway-Sant'Anna (2021)
  "DIDmultiplegt",  # de Chaisemartin & D'Haultfoeuille
  "HonestDiD",      # Rambachan & Roth (2023)
  "fixest",         # TWFE rapide (Berge 2018), Sun-Abraham via sunab()
  "did2s",          # Borusyak-Jaravel-Spiess (2024)

  # Matching
  "MatchIt",        # Propensity score matching
  "WeightIt",       # Alternative MatchIt pour IPW
  "cobalt",         # Balance checks post-matching

  # Manipulation de données
  "tidyverse",      # dplyr, ggplot2, tidyr, readr, etc.
  "data.table",     # manipulation rapide grandes tables
  "arrow",          # lecture/écriture parquet
  "haven",          # lecture fichiers SAS/Stata
  "readxl",         # lecture Excel

  # Codes géographiques
  "COGugaison",     # harmonisation codes INSEE après fusions communes

  # Cartographie
  "sf",             # données spatiales
  "ggplot2",        # graphiques publication
  "maps",           # cartes de base

  # Tables et sorties
  "modelsummary",   # tables de régression au format LaTeX
  "gt",             # tables alternatives
  "kableExtra",     # tables LaTeX
  "stargazer",      # tables de régression classiques

  # Utilitaires
  "here",           # gestion chemins relatifs
  "glue",           # interpolation de chaînes
  "lubridate",      # manipulation dates
  "janitor",        # nettoyage noms de colonnes
  "purrr",          # programmation fonctionnelle
  "furrr"           # parallélisation purrr
)

# Installer les packages manquants
packages_manquants <- required_packages[
  !sapply(required_packages, requireNamespace, quietly = TRUE)
]

if (length(packages_manquants) > 0) {
  message("Installation des packages manquants : ",
          paste(packages_manquants, collapse = ", "))
  install.packages(packages_manquants, dependencies = TRUE)
}

# Charger tous les packages
invisible(lapply(required_packages, library, character.only = TRUE,
                 warn.conflicts = FALSE, quietly = TRUE))

# ── 3. Chemins du projet ─────────────────────────────────────────────────────
# Détection automatique du dossier racine du projet
PROJ_ROOT <- here::here()

PATHS <- list(
  raw       = file.path(PROJ_ROOT, "data", "raw"),
  processed = file.path(PROJ_ROOT, "data", "processed"),
  code      = file.path(PROJ_ROOT, "code"),
  tables    = file.path(PROJ_ROOT, "output", "tables"),
  figures   = file.path(PROJ_ROOT, "output", "figures"),
  paper     = file.path(PROJ_ROOT, "paper")
)

# Sous-dossiers données brutes
PATHS$raw_acv       <- file.path(PATHS$raw, "acv")
PATHS$raw_elections <- file.path(PATHS$raw, "elections")
PATHS$raw_insee     <- file.path(PATHS$raw, "insee")
PATHS$raw_geo       <- file.path(PATHS$raw, "geo")

# Créer les dossiers s'ils n'existent pas
lapply(PATHS, dir.create, recursive = TRUE, showWarnings = FALSE)

# ── 4. Constantes du projet ───────────────────────────────────────────────────

# Codes INSEE à exclure
EXCL_OM        <- TRUE   # exclure outre-mer (code commune >= 97000 ou dep 97x-98x)
EXCL_IDF_PC    <- TRUE   # exclure Paris petite couronne (dept 75, 92, 93, 94)

# Seuils de population pour le groupe contrôle
POP_MIN        <- 20000
POP_MAX        <- 100000

# Fenêtre temporelle
ANNEE_DEBUT    <- 2012
ANNEE_FIN_MAIN <- 2019
ANNEE_FIN_EXT  <- 2024

# Année de traitement ACV
ANNEE_TRAITEMENT <- 2018

# Liste des scrutins par ordre chronologique
SCRUTINS <- list(
  pres2012 = list(annee = 2012, type = "presidentielle", tour = 1,
                  label = "Présidentielle 2012 T1"),
  leg2012  = list(annee = 2012, type = "legislatives",   tour = 1,
                  label = "Législatives 2012 T1"),
  eur2014  = list(annee = 2014, type = "europeennes",    tour = 1,
                  label = "Européennes 2014"),
  pres2017 = list(annee = 2017, type = "presidentielle", tour = 1,
                  label = "Présidentielle 2017 T1"),
  leg2017  = list(annee = 2017, type = "legislatives",   tour = 1,
                  label = "Législatives 2017 T1"),
  eur2019  = list(annee = 2019, type = "europeennes",    tour = 1,
                  label = "Européennes 2019"),     # scrutin post-ACV principal
  pres2022 = list(annee = 2022, type = "presidentielle", tour = 1,
                  label = "Présidentielle 2022 T1"),
  leg2022  = list(annee = 2022, type = "legislatives",   tour = 1,
                  label = "Législatives 2022 T1"),
  eur2024  = list(annee = 2024, type = "europeennes",    tour = 1,
                  label = "Européennes 2024"),
  leg2024  = list(annee = 2024, type = "legislatives",   tour = 1,
                  label = "Législatives 2024 T1")
)

# ── 5. Options R globales ─────────────────────────────────────────────────────
options(
  scipen       = 10,      # éviter notation scientifique
  digits       = 4,
  OutDec       = ".",     # séparateur décimal en point (LaTeX)
  stringsAsFactors = FALSE
)

# Parallélisation (furrr)
future::plan(future::multisession, workers = max(1L, parallel::detectCores() - 1L))

message("✓ Setup OK — Projet : ", PROJ_ROOT)
message("  Packages chargés : ", length(required_packages))
message("  Dossiers créés   : OK")
