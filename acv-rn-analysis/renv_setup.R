################################################################################
# renv_setup.R
# Initialise l'environnement renv pour reproductibilité
# À exécuter UNE SEULE FOIS lors de la première installation
# Usage : Rscript renv_setup.R
################################################################################

if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv")

renv::init(bare = TRUE)

packages_a_installer <- c(
  "did", "DIDmultiplegt", "HonestDiD", "fixest", "did2s",
  "MatchIt", "WeightIt", "cobalt",
  "tidyverse", "data.table", "arrow", "haven", "readxl",
  "COGugaison",
  "sf", "ggplot2", "maps",
  "modelsummary", "gt", "kableExtra", "stargazer",
  "here", "glue", "lubridate", "janitor", "purrr", "furrr",
  "future"
)

renv::install(packages_a_installer)
renv::snapshot()

cat("✓ Environnement renv initialisé et verrouillé (renv.lock)\n")
