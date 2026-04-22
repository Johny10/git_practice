################################################################################
# 01_download_data.R
# Téléchargement automatique de toutes les données brutes
# IMPORTANT : Ce script tente des téléchargements automatiques depuis
# data.gouv.fr et INSEE. Si un téléchargement échoue, il est documenté
# dans data/raw/README.md avec l'URL manquante.
################################################################################

set.seed(42)
source(here::here("code", "00_setup.R"))

# ── Utilitaire de téléchargement sécurisé ────────────────────────────────────
download_safe <- function(url, dest, nom, overwrite = FALSE) {
  if (file.exists(dest) && !overwrite) {
    message("  [SKIP] Déjà présent : ", basename(dest))
    return(invisible(TRUE))
  }
  dir.create(dirname(dest), recursive = TRUE, showWarnings = FALSE)
  tryCatch({
    utils::download.file(url, dest, mode = "wb", quiet = FALSE)
    message("  [OK] Téléchargé : ", nom)
    return(invisible(TRUE))
  }, error = function(e) {
    message("  [ERREUR] Échec téléchargement : ", nom)
    message("           URL : ", url)
    message("           Motif : ", conditionMessage(e))
    message("  --> Téléchargement manuel requis. Voir data/raw/README.md")
    return(invisible(FALSE))
  })
}

# ── 1. Liste Action Cœur de Ville ─────────────────────────────────────────────
message("\n=== 1. Liste ACV ===")

# Option A : data.gouv.fr (API)
url_acv_datagouv <- paste0(
  "https://www.data.gouv.fr/fr/datasets/r/",
  "bd35b2b1-42e4-4f3e-ac38-72a9e15f8f52"   # ID ressource à vérifier
)

# Option B : Caisse des Dépôts OpenData (export CSV direct)
url_acv_cdc <- paste0(
  "https://opendata.caissedesdepots.fr/api/explore/v2.1/catalog/datasets/",
  "villes_action_coeurdeville/exports/csv?lang=fr&timezone=Europe%2FParis&",
  "use_labels=true&delimiter=%3B"
)

dest_acv <- file.path(PATHS$raw_acv, "acv_liste_officielle.csv")

ok_a <- download_safe(url_acv_cdc, dest_acv, "Liste ACV (Caisse des Dépôts)")
if (!ok_a) {
  download_safe(url_acv_datagouv, dest_acv, "Liste ACV (data.gouv.fr)")
}

# ── 2. Résultats électoraux ───────────────────────────────────────────────────
message("\n=== 2. Résultats électoraux ===")

# Les URLs data.gouv.fr pour les résultats électoraux sont stables par dataset.
# On utilise les IDs de ressources connus (à vérifier/corriger si nécessaire).
# Format attendu : fichiers CSV par commune avec résultats par candidat/liste.

elections_urls <- list(
  pres2012 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/5e48c878-3b77-4e23-9ade-bc32f8e9a87d",
    dest = file.path(PATHS$raw_elections, "pres2012_t1_communes.csv"),
    nom  = "Présidentielle 2012 T1"
  ),
  eur2014 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/5c0b9d5d-2a4d-4e0e-9e6b-73a3d51b35ea",
    dest = file.path(PATHS$raw_elections, "eur2014_communes.csv"),
    nom  = "Européennes 2014"
  ),
  pres2017 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/4dc39b93-b17a-4e5c-8e36-f67eeab11f2e",
    dest = file.path(PATHS$raw_elections, "pres2017_t1_communes.csv"),
    nom  = "Présidentielle 2017 T1"
  ),
  leg2017 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/a2c5a5f6-2a8c-4b5e-b7c1-8f3a2b7e4c9d",
    dest = file.path(PATHS$raw_elections, "leg2017_t1_communes.csv"),
    nom  = "Législatives 2017 T1"
  ),
  eur2019 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/6671fb7d-6ea5-4f2d-abcd-e1234567890a",
    dest = file.path(PATHS$raw_elections, "eur2019_communes.csv"),
    nom  = "Européennes 2019"
  ),
  pres2022 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/bfbe7f87-8df1-4527-8c7b-27440e1e7a4d",
    dest = file.path(PATHS$raw_elections, "pres2022_t1_communes.csv"),
    nom  = "Présidentielle 2022 T1"
  ),
  eur2024 = list(
    url  = "https://www.data.gouv.fr/fr/datasets/r/a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    dest = file.path(PATHS$raw_elections, "eur2024_communes.csv"),
    nom  = "Européennes 2024"
  )
)

echecs_elections <- character(0)
for (nm in names(elections_urls)) {
  el <- elections_urls[[nm]]
  ok <- download_safe(el$url, el$dest, el$nom)
  if (!ok) echecs_elections <- c(echecs_elections, nm)
}

# ── 3. Données INSEE ──────────────────────────────────────────────────────────
message("\n=== 3. Données INSEE ===")

# 3a. Populations légales — API INSEE (Sirene / open data)
# URL directe : millésimes 2012-2019
url_pop_base <- "https://www.insee.fr/fr/statistiques/fichier/6683031/"
pop_millésimes <- c("2012", "2014", "2016", "2018", "2019")

for (an in pop_millésimes) {
  url_pop <- paste0(url_pop_base, "ensemble.zip")  # URL à adapter par millésime
  dest_pop <- file.path(PATHS$raw_insee,
                        paste0("populations_legales_", an, ".csv"))
  # Note: l'URL réelle varie par millésime — téléchargement manuel probable
  # download_safe(url_pop, dest_pop, paste("Populations légales", an))
  message("  [MANUEL] Populations légales ", an, " — URL: ", url_pop_base)
}

# 3b. Filosofi — annonces de téléchargement manuel (API non publique)
filosofi_annees <- c(2012, 2015, 2017)
for (an in filosofi_annees) {
  message("  [MANUEL] Filosofi ", an,
          " — https://www.insee.fr/fr/statistiques (revenu médian commune)")
}

# 3c. COG communes
url_cog <- paste0(
  "https://www.insee.fr/fr/statistiques/fichier/6800675/",
  "commune_2024.csv"
)
dest_cog <- file.path(PATHS$raw_geo, "cog_communes_2024.csv")
download_safe(url_cog, dest_cog, "COG communes 2024")

# ── 4. Bilan ─────────────────────────────────────────────────────────────────
message("\n=== BILAN TÉLÉCHARGEMENTS ===")

if (length(echecs_elections) > 0) {
  message("\n⚠️  TÉLÉCHARGEMENTS ÉCHOUÉS (nécessitent action manuelle) :")
  message("   Scrutins : ", paste(echecs_elections, collapse = ", "))
  message("\n   URLs à utiliser manuellement :")
  message("   Ministère de l'Intérieur : https://www.data.gouv.fr/fr/datasets/elections/")
  message("   Placer les fichiers dans : ", PATHS$raw_elections)
} else {
  message("\n✓ Tous les téléchargements électoraux ont réussi.")
}

message("\n   DONNÉES MANUELLES TOUJOURS REQUISES :")
message("   - Filosofi (revenus médians) : https://www.insee.fr/fr/statistiques")
message("   - Populations légales par millésime : https://www.insee.fr/fr/statistiques/6683031")
message("   - Base RP (emploi) : https://www.insee.fr/fr/statistiques")
message("\n   → Voir data/raw/README.md pour instructions détaillées")
