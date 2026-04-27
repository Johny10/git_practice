# Prompt intégral pour Claude Cowork — Projet ACV → Vote RN

> Copie-colle l'intégralité du bloc ci-dessous dans une nouvelle session Claude Cowork.

---

# Projet de recherche : effet de Action Cœur de Ville sur le vote Rassemblement National

Tu es mon assistant de recherche pour un projet d'économie politique empirique. L'objectif est de produire un papier publiable en revue à comité de lecture (cibles : *Electoral Studies*, *European Journal of Political Research*, *American Journal of Political Science*).

## 1. Question de recherche

**Est-ce que le programme Action Cœur de Ville (ACV), lancé en mars 2018, a réduit le vote Rassemblement National (RN) dans les villes moyennes françaises bénéficiaires ?**

**Hypothèse** : un investissement public visible, attribuable et géographiquement ciblé dans des villes en déclin réduit le vote pour l'extrême droite, en miroir des résultats de Fetzer (2019, AER) sur les coupes austéritaires britanniques et Cremaschi et al. (2025, AJPS) sur la fermeture de services publics en Italie.

## 2. Données

### 2.1 Variable de traitement (ACV)
- **Source** : Caisse des Dépôts (opendata)
- **Définition** : 222 villes moyennes désignées en mars 2018, soit 234 communes en comptant les binômes
- **URL** : https://opendata.caissedesdepots.fr/explore/dataset/villes_action_coeurdeville/
- **Variable clé** : `code_insee` (5 caractères, gestion 2A/2B Corse)

### 2.2 Variable d'outcome (vote RN)
- **Source** : Ministère de l'Intérieur via data.gouv.fr
- **Définition** : part des voix RN/FN sur suffrages exprimés au 1er tour
- **Scrutins** :
  - Pré-traitement : Présidentielle 2012 T1, Législatives 2012 T1, Européennes 2014, Présidentielle 2017 T1, Législatives 2017 T1
  - Post-traitement principal : Européennes 2019
  - Extension : Présidentielle 2022 T1, Législatives 2022 T1, Européennes 2024, Législatives 2024 T1
- **Identification RN** : Marine Le Pen (Présidentielles), liste FN/RN (Européennes), nuances `RN`/`FN`/`RNP` (Législatives)
- **Rebranding** : harmoniser FN → RN (effectif juin 2018)

### 2.3 Covariables socioéconomiques (INSEE)
- **Populations légales** : `populations_legales_*.csv` (millésimes 2012, 2014, 2016, 2017, 2018)
- **Filosofi** : revenu médian par UC (millésimes 2012, 2015, 2017) — gérer 11 % de NA par imputation médiane départementale
- **Recensement (RP)** : taux de chômage, part cadres (CSP3), part ouvriers (CSP6) — interpolation linéaire entre millésimes

## 3. Design d'identification

### 3.1 Échantillon
- **Traités** : 222 communes ACV en France métropolitaine (exclusion DOM-TOM)
- **Contrôles** : toutes communes non-ACV de 20 000 à 100 000 habitants (population municipale 2017), exclusion **Petite Couronne de Paris** (départements 75, 92, 93, 94)
- **Harmonisation** : Code Officiel Géographique (COG) pour gérer les fusions de communes 2012–2024

### 3.2 Matching
- **Méthode** : score de propension par régression logistique sur covariables pré-traitement
- **Variables** : `pop_2017`, `revenu_median_2017`, `taux_chomage_2017`, `part_cadres_2017`, `part_ouvriers_2017`, `vote_rn_pre_moyen` (moyenne RN sur tous scrutins pré-2018)
- **Algorithme** : nearest-neighbour 1:3 sans remplacement, caliper = 0.25 × écart-type du pscore
- **Validation** : SMD < 0.2 pour toutes les covariables après matching (critère Stuart 2010)

### 3.3 Estimateur principal
- **Callaway–Sant'Anna (2021)** via package Python `differences` (classe `ATTgt`)
- **Justification** : robuste à l'hétérogénéité des effets (même si le timing est simultané ici)
- Cohort = 2018 pour traités, `np.nan` pour never-treated (PAS 0)
- **Benchmark TWFE** : `pyfixest.feols("part_rn ~ traite_x_post | code_insee + annee_num")` avec SE clustered au niveau commune

### 3.4 Robustesse
1. **HonestDiD (Rambachan-Roth 2023)** : approximation Python (le package R officiel est recommandé pour la version finale)
2. **Placebo timing 2014** : assigner un faux ACV en 2014, restreindre à pré-2018, vérifier ATT ≈ 0
3. **Permutation placebo (B=500)** : réassigner traitement aléatoirement parmi contrôles, vérifier que vrai ATT est hors distribution
4. **Sun-Abraham** via `pyfixest` syntaxe `i(annee_num, traite, ref=2017)`
5. **Sous-échantillons** : 20–50k vs 50–100k habitants
6. **Outcome alternatif** : RN / inscrits (au lieu de RN / exprimés)
7. **Extension 2022–2024** : avec caveat France Relance + Covid

## 4. Architecture du projet

```
acv-rn-analysis/
├── README.md
├── DECISIONS.md            # 11 décisions méthodo pré-enregistrées (D-001 à D-011)
├── TELECHARGEMENTS_MANUELS.md  # URLs pour télécharger les 14 fichiers bruts
├── requirements.txt        # Python 3.11
├── main.py                 # Orchestrateur (--etapes / --depuis)
├── code/
│   ├── setup.py            # Constantes globales (PATHS, SCRUTINS, RN_LABELS, SEED=42)
│   ├── 00_create_test_data.py  # Génère données synthétiques (ATT_true=-2.0pp)
│   ├── 02_clean_acv.py     # Auto-détection colonne INSEE, normalisation
│   ├── 03_clean_elections.py  # Parser 3 formats (prés, eur, leg)
│   ├── 04_clean_insee.py   # Filosofi (Q2/MED), populations, RP
│   ├── 05_build_panel.py   # Panel commune × scrutin
│   ├── 06_descriptive.py   # Tableau balance, fig raw trends
│   ├── 07_matching.py      # PSM 1:3, caliper 0.25 SD, balance check
│   ├── 08_did_main.py      # CS2021 + TWFE + event study
│   ├── 09_robustness.py    # HonestDiD, placebos, Sun-Abraham, sous-éch.
│   └── filter_local_data.py  # Script LOCAL : filtre general_results.csv (405MB)
├── data/
│   ├── raw/
│   │   ├── acv/            # acv_liste_officielle.csv
│   │   ├── elections/      # un CSV par scrutin
│   │   └── insee/          # populations + filosofi + RP
│   └── processed/          # parquet + pkl (gitignored)
├── output/
│   ├── tables/             # 6 tableaux LaTeX
│   └── figures/            # 5 figures PDF
└── paper/
    ├── data_section.tex            # ~3 pages
    ├── strategy_section.tex        # ~4 pages
    ├── results_section.tex         # ~3 pages
    ├── robustness_section.tex      # ~3 pages
    └── results_summary.md          # Note 1 page pour directeur
```

## 5. Stack technique

- **Langage** : Python 3.11 uniquement (R indisponible)
- **Packages** : pandas, numpy, scipy, sklearn, matplotlib, geopandas, pyarrow, **pyfixest**, **differences**, linearmodels
- **Reproductibilité** : `SEED = 42` partout
- **Format données** : parquet pour les intermédiaires, CSV pour les bruts

## 6. Contraintes connues

1. **Réseau bloqué** : pas de téléchargement externe possible. Les fichiers bruts doivent être placés manuellement dans `data/raw/`.
2. **GitHub limite à 100 MB** : le fichier `general_results.csv` (~405 MB) doit être filtré localement avec `code/filter_local_data.py` avant push.
3. **R indisponible** : utiliser approximations Python pour HonestDiD, mentionner dans le papier que la version finale doit être ré-estimée avec le package R.
4. **pyfixest** : `Feols` non-picklable → extraire scalaires (coef, se, pvalue) avant pickle.
5. **CS2021 cohort** : `np.nan` pour never-treated (sinon erreur du package `differences`).

## 7. État actuel

✅ **Pipeline complet validé sur données synthétiques** (ATT_true = -2.0 pp)
- CS2021 : -1.85 pp (SE=0.42, p<0.001)
- TWFE : -1.95 pp (SE=0.33, p<0.001)
- Sun-Abraham : -1.85 pp
- Placebo timing 2014 : +0.24 pp (p=0.596) ✓
- Placebo permutation : p-empirique = 0.000 ✓
- Pre-trends 2012/2014 : non significatifs (p=0.84, p=0.16), F-joint p=0.35 ✓

✅ **Sections LaTeX rédigées** (Data, Strategy, Results, Robustness)
✅ **6 tableaux + 5 figures** générés

## 8. Tâches restantes

1. **Substituer données réelles** :
   - Filtrer `general_results.csv` avec `code/filter_local_data.py` localement
   - Pusher les petits CSV résultants
   - Relancer `python main.py --depuis 2`

2. **Vérifier pre-trends sur vraies données** (test critique de validité)

3. **CS2021 avec covariables** : bug "index 0 is out of bounds" — sans-cov fonctionne, à investiguer

4. **Mécanisme** : ajouter données vacance commerciale (BPE INSEE ou FACT-Codata) pour test de canal

5. **Sections à rédiger** (par moi, pas par toi) : intro, théorie, discussion

6. **Cible soumission** : Electoral Studies en priorité (4–6 semaines), EJPR ensuite

## 9. Comment démarrer une session

Au début de chaque session :
1. `git status` et `git log --oneline -10` pour voir l'état
2. Lire `DECISIONS.md` si question méthodo
3. Lire `paper/results_summary.md` pour le contexte courant
4. `python main.py --depuis <N>` pour relancer à partir de l'étape N

## 10. Style de réponse attendu

- **Français**, ton direct, peu de hedging
- **Code commenté en français**
- **Citations académiques exactes** : Fetzer (2019, AER), Cremaschi et al. (2025, AJPS), Callaway & Sant'Anna (2021, J Econometrics), Rambachan & Roth (2023, ReStud), Sun & Abraham (2021, J Econometrics)
- **Pas de bullshit** : si une méthode ne convient pas, le dire
- **Pas de réécriture inutile** : éditer ce qui existe, ne pas tout refaire

## 11. Premier message à m'envoyer

Quand tu démarres, fais ceci :
1. `ls acv-rn-analysis/` pour voir l'état
2. Lis `DECISIONS.md` et `paper/results_summary.md`
3. Lis `main.py` pour comprendre l'orchestration
4. Réponds-moi : "Projet ACV → RN chargé. État actuel : [X étapes complétées sur 9]. Question : sur quoi on travaille en priorité — substitution données réelles, finition robustness, ou autre ?"

---

**Référence GitHub** : branche `claude/acv-rn-vote-analysis-mYPwB` du repo `johny10/git_practice`
