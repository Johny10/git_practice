################################################################################
# main.R
# Script maître — exécute l'analyse complète end-to-end
# Usage : source("code/main.R")  depuis le dossier racine du projet
################################################################################

set.seed(42)

# ── Initialisation ─────────────────────────────────────────────────────────
cat("╔══════════════════════════════════════════════════════════════════╗\n")
cat("║  ACV → Vote RN : Analyse empirique end-to-end                   ║\n")
cat("║  Méthode : Callaway-Sant'Anna (2021) + Matching + HonestDiD     ║\n")
cat("╚══════════════════════════════════════════════════════════════════╝\n\n")

t0 <- proc.time()

source("code/00_setup.R")

# ── Étape 1 : Acquisition des données ──────────────────────────────────────
cat("\n[ÉTAPE 1] Acquisition des données\n")
source("code/01_download_data.R")

# ── Étape 2 : Nettoyage et harmonisation ───────────────────────────────────
cat("\n[ÉTAPE 2] Nettoyage et harmonisation\n")
source("code/02_clean_acv.R")
source("code/03_clean_elections.R")
source("code/04_clean_insee.R")
source("code/05_build_panel.R")

# ── Étape 3 : Statistiques descriptives ────────────────────────────────────
cat("\n[ÉTAPE 3] Statistiques descriptives\n")
source("code/06_descriptive.R")

# ── Étape 4 : Matching ──────────────────────────────────────────────────────
cat("\n[ÉTAPE 4] Propensity score matching\n")
source("code/07_matching.R")

# ── Étape 5 : Estimation principale ────────────────────────────────────────
cat("\n[ÉTAPE 5] Callaway-Sant'Anna DiD\n")
source("code/08_did_main.R")

# ── Étape 6 : Robustesse ────────────────────────────────────────────────────
cat("\n[ÉTAPE 6] Robustesse\n")
source("code/09_robustness.R")

# ── Étape 7 : Mécanisme (optionnel) ─────────────────────────────────────────
if (file.exists("code/10_mechanism.R")) {
  cat("\n[ÉTAPE 7] Mécanisme\n")
  source("code/10_mechanism.R")
}

# ── Étapes 8 : Tables et figures ────────────────────────────────────────────
cat("\n[ÉTAPE 8] Tables et figures pour publication\n")
source("code/11_tables.R")
source("code/12_figures.R")

# ── Bilan ──────────────────────────────────────────────────────────────────
elapsed <- (proc.time() - t0)["elapsed"]
cat(sprintf("\n✓ Analyse complète terminée en %.1f secondes (%.1f min)\n",
            elapsed, elapsed / 60))
cat("  Tables  : ", PATHS$tables, "\n")
cat("  Figures : ", PATHS$figures, "\n")
cat("  Paper   : ", PATHS$paper, "\n")
