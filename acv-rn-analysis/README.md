# Action Cœur de Ville et vote Rassemblement National

## Résumé du projet

Ce projet analyse empiriquement l'effet du programme **Action Cœur de Ville (ACV)** 
sur le vote Rassemblement National (RN/FN) dans les villes moyennes françaises.

**Hypothèse centrale** : L'investissement public visible, attribuable et géographiquement 
ciblé dans les villes moyennes en déclin réduit le soutien électoral au RN.

Ce travail est le pendant gain-side de Fetzer (2019, AER) — austérité UK → UKIP — 
et de Cremaschi et al. (2025, AJPS) — fermeture de services publics → extrême droite.

**Cible de publication** : Electoral Studies, EJPR, ou AJPS.

---

## Programme ACV

| Caractéristique       | Détail                                            |
|-----------------------|---------------------------------------------------|
| Annonce               | Décembre 2017                                     |
| Sélection             | Mars 2018                                         |
| Villes lauréates      | 222 villes / binômes (234 communes)               |
| Taille cible          | Majoritairement 20 000 – 100 000 habitants        |
| Budget total          | 5 milliards € sur 5 ans (2018–2022)               |
| Financement           | État + Caisse des Dépôts + Action Logement + Anah |
| Volets                | Habitat, commerce, mobilité, espace public, services |

---

## Design empirique

| Élément                  | Choix                                                                 |
|--------------------------|-----------------------------------------------------------------------|
| Unité d'analyse          | Commune (code INSEE)                                                  |
| Groupe traité            | 222 villes ACV (234 communes si binômes split)                        |
| Groupe contrôle          | Villes 20 000–100 000 hab., métropole hors Paris petite couronne      |
| Fenêtre principale       | 2012–2019                                                             |
| Extension                | 2012–2024 (robustesse)                                                |
| Variable dépendante      | Part RN/FN (suffrages exprimés, T1)                                   |
| Méthode principale       | Callaway-Sant'Anna (2021) staggered DiD + propensity score matching   |
| Robustesse               | HonestDiD (Rambachan-Roth 2023), placebo, Borusyak-Jaravel-Spiess    |

**Scrutins couverts** :
- Pré-traitement : présidentielle 2012 T1, législatives 2012 T1, européennes 2014, municipales 2014, présidentielle 2017 T1, législatives 2017 T1
- Post-traitement principal : européennes 2019
- Extension : présidentielle 2022 T1, législatives 2022 T1, européennes 2024, législatives 2024 T1

---

## Structure du projet

```
acv-rn-analysis/
├── README.md               ← ce fichier
├── DECISIONS.md            ← journal des décisions méthodologiques
├── renv.lock               ← verrouillage des versions R (généré par renv)
├── renv/                   ← environnement R isolé
│
├── code/
│   ├── 00_setup.R          ← installation packages, chemins globaux
│   ├── 01_download_data.R  ← téléchargement automatique des sources
│   ├── 02_clean_acv.R      ← nettoyage liste ACV + codes INSEE
│   ├── 03_clean_elections.R← nettoyage résultats électoraux par commune
│   ├── 04_clean_insee.R    ← variables socio-démo INSEE
│   ├── 05_build_panel.R    ← construction panel commune × scrutin
│   ├── 06_descriptive.R    ← Table 1, Figure 1, Carte 1
│   ├── 07_matching.R       ← propensity score matching (MatchIt)
│   ├── 08_did_main.R       ← Callaway-Sant'Anna, event study
│   ├── 09_robustness.R     ← HonestDiD, placebo, sous-échantillons
│   ├── 10_mechanism.R      ← médiation (si données disponibles)
│   ├── 11_tables.R         ← export tables LaTeX
│   ├── 12_figures.R        ← export figures PDF
│   └── main.R              ← script maître (source tous les scripts)
│
├── data/
│   ├── raw/
│   │   ├── README.md       ← documentation sources, URLs, dates DL
│   │   ├── acv/            ← liste villes ACV
│   │   ├── elections/      ← résultats bruts par scrutin
│   │   ├── insee/          ← données socio-démo INSEE
│   │   └── geo/            ← codes géographiques, COG
│   └── processed/
│       ├── acv_communes.rds        ← liste ACV harmonisée codes INSEE
│       ├── elections_panel.rds     ← résultats électoraux panel long
│       ├── insee_panel.rds         ← variables socio-démo panel
│       └── panel_final.rds         ← panel complet prêt pour analyse
│
├── output/
│   ├── tables/
│   │   ├── table1_balance.tex
│   │   ├── table2_main_results.tex
│   │   ├── table3_robustness.tex
│   │   └── tableA1_matching_balance.tex
│   └── figures/
│       ├── fig1_raw_trends.pdf
│       ├── fig2_event_study.pdf
│       ├── fig3_honestdid.pdf
│       ├── fig4_placebo.pdf
│       └── map1_acv_location.pdf
│
└── paper/
    ├── data_section.tex
    ├── strategy_section.tex
    ├── results_section.tex
    └── robustness_section.tex
```

---

## Comment reproduire l'analyse

### Prérequis

- R ≥ 4.3.0
- `renv` installé : `install.packages("renv")`
- Connexion internet pour le téléchargement des données (étape 1)

### Exécution

```r
# Dans R, depuis le dossier acv-rn-analysis/
renv::restore()          # restaure les packages
source("code/main.R")    # exécute l'analyse complète
```

### Téléchargement manuel (si automatique échoue)

Voir `data/raw/README.md` pour la liste des fichiers à télécharger manuellement 
et les URLs correspondantes.

---

## Sources de données

| Source                  | URL                                                               | Usage                     |
|-------------------------|-------------------------------------------------------------------|---------------------------|
| Liste ACV               | https://www.data.gouv.fr/fr/datasets/action-coeur-de-ville/       | Groupe traité             |
| Résultats électoraux    | https://www.data.gouv.fr/fr/datasets/elections/                   | Variable dépendante       |
| Populations légales     | https://www.insee.fr/fr/statistiques/6683031                      | Matching                  |
| Filosofi revenu médian  | https://www.insee.fr/fr/statistiques (Filosofi)                   | Matching                  |
| Emploi-Population       | Base locale INSEE par commune                                      | Matching                  |
| COG communes            | https://www.insee.fr/fr/information/6800675                        | Harmonisation codes INSEE |

---

## Auteur et date

Projet initialisé le 2026-04-22.  
Contact : [à compléter]

---

## Références principales

- Callaway, B. & Sant'Anna, P. (2021). Difference-in-differences with multiple time periods. *Journal of Econometrics*, 225(2), 200–230.
- Cremaschi, S., Rettl, P., Cappelluti, M., & De Vries, C. (2025). Geographies of Discontent. *AJPS*.
- Fetzer, T. (2019). Did Austerity Cause Brexit? *American Economic Review*, 109(11), 3849–3886.
- Rambachan, A. & Roth, J. (2023). A More Credible Approach to Parallel Trends. *Review of Economic Studies*, 90(5), 2555–2591.
- Bolet, D., Green, F., & González-Eguino, M. (2024). How to Get Coal Country to Vote for Climate Policy. *APSR*.
- Albanese, G., Barone, G., & de Blasio, G. (2022). *European Economic Review*.
