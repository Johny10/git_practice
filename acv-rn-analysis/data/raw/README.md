# Sources de données brutes

Ce fichier documente toutes les sources de données utilisées dans le projet,
avec URLs, dates de téléchargement, et instructions de téléchargement manuel
si le téléchargement automatique a échoué.

---

## Statut de téléchargement

| Fichier                          | Source           | Statut         | Date DL    | Notes                          |
|----------------------------------|------------------|----------------|------------|--------------------------------|
| Liste villes ACV                 | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Présidentielle 2012 T1           | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Législatives 2012 T1             | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Européennes 2014                 | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Présidentielle 2017 T1           | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Législatives 2017 T1             | data.gouv.fr     | ⏳ À faire      | —          | Étape 1                        |
| Européennes 2019                 | data.gouv.fr     | ⏳ À faire      | —          | Étape 1 — scrutin post-ACV clé |
| Présidentielle 2022 T1           | data.gouv.fr     | ⏳ À faire      | —          | Extension robustesse           |
| Législatives 2022 T1             | data.gouv.fr     | ⏳ À faire      | —          | Extension robustesse           |
| Européennes 2024                 | data.gouv.fr     | ⏳ À faire      | —          | Extension robustesse           |
| Législatives 2024 T1             | data.gouv.fr     | ⏳ À faire      | —          | Extension robustesse           |
| Populations légales (multi-ann.) | INSEE            | ⏳ À faire      | —          | Étape 1                        |
| Filosofi revenu médian           | INSEE            | ⏳ À faire      | —          | Étape 1                        |
| Emploi-population active         | INSEE            | ⏳ À faire      | —          | Étape 1                        |
| COG communes (référentiel)       | INSEE            | ⏳ À faire      | —          | Harmonisation codes INSEE      |

---

## Sources détaillées

### 1. Liste Action Cœur de Ville

**URL principale** :  
https://www.data.gouv.fr/fr/datasets/action-coeur-de-ville/

**URL alternative (Caisse des Dépôts)** :  
https://opendata.caissedesdepots.fr/explore/dataset/villes_action_coeurdeville/

**Format attendu** : CSV ou XLSX avec colonnes [nom_commune, code_insee, dept, region, ...]  
**Variables à extraire** : code INSEE, nom, département, indicatrice binôme  
**Fichier cible** : `data/raw/acv/acv_liste_officielle.csv`

**Instructions manuelles si échec automatique** :
1. Aller sur https://www.data.gouv.fr/fr/datasets/action-coeur-de-ville/
2. Télécharger le fichier CSV de la liste des villes lauréates
3. Placer dans `data/raw/acv/`

---

### 2. Résultats électoraux — Ministère de l'Intérieur

**URL portail** : https://www.data.gouv.fr/fr/datasets/elections/

**Scrutins à télécharger** :

| Scrutin                  | URL directe (si connue)                                                                        | Fichier cible                          |
|--------------------------|-----------------------------------------------------------------------------------------------|----------------------------------------|
| Présidentielle 2012 T1   | https://www.data.gouv.fr/fr/datasets/election-presidentielle-2012-resultats-par-commune/      | `elections/pres2012_t1_communes.csv`   |
| Législatives 2012 T1     | https://www.data.gouv.fr/fr/datasets/elections-legislatives-2012-resultats-par-commune/       | `elections/leg2012_t1_communes.csv`    |
| Européennes 2014         | https://www.data.gouv.fr/fr/datasets/elections-europeennes-2014-resultats-par-communes/       | `elections/eur2014_communes.csv`       |
| Présidentielle 2017 T1   | https://www.data.gouv.fr/fr/datasets/election-presidentielle-des-23-avril-et-7-mai-2017/      | `elections/pres2017_t1_communes.csv`   |
| Législatives 2017 T1     | https://www.data.gouv.fr/fr/datasets/elections-legislatives-des-11-et-18-juin-2017/          | `elections/leg2017_t1_communes.csv`    |
| Européennes 2019         | https://www.data.gouv.fr/fr/datasets/elections-europeennes-du-26-mai-2019/                   | `elections/eur2019_communes.csv`       |
| Présidentielle 2022 T1   | https://www.data.gouv.fr/fr/datasets/election-presidentielle-des-10-et-24-avril-2022/        | `elections/pres2022_t1_communes.csv`   |
| Législatives 2022 T1     | https://www.data.gouv.fr/fr/datasets/elections-legislatives-des-12-et-19-juin-2022/          | `elections/leg2022_t1_communes.csv`    |
| Européennes 2024         | https://www.data.gouv.fr/fr/datasets/elections-europeennes-du-9-juin-2024/                   | `elections/eur2024_communes.csv`       |
| Législatives 2024 T1     | https://www.data.gouv.fr/fr/datasets/elections-legislatives-des-30-juin-et-7-juillet-2024/   | `elections/leg2024_t1_communes.csv`    |

**Variables à extraire** : code_commune (INSEE), suffrages exprimés, voix_RN/FN,  
nom_candidat_RN (pour vérification), libellé_liste_RN (européennes)

**Note importante** : Le format des fichiers du Ministère de l'Intérieur varie 
selon les scrutins. Pour les européennes, les résultats sont par liste et non 
par candidat. Identifier la liste RN/FN dans chaque fichier.

---

### 3. Données INSEE communales

#### 3a. Populations légales

**URL** : https://www.insee.fr/fr/statistiques/6683031  
**Millésimes nécessaires** : 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019  
**Variable** : population municipale par commune  
**Fichier cible** : `data/raw/insee/populations_legales_[annee].csv`

#### 3b. Filosofi — revenus médians par commune

**URL** : https://www.insee.fr/fr/statistiques (rubrique "Revenus, pouvoir d'achat")  
**Produit** : Filosofi (Fichier localisé social et fiscal)  
**Millésimes nécessaires** : 2012, 2015, 2017 (disponibilité à vérifier)  
**Variables** : revenu médian par UC, part ménages pauvres  
**Attention** : Filosofi n'est disponible que pour communes > 1 000 habitants  
environ (ou parfois seuil plus haut). Vérifier disponibilité pour toutes 
les communes du panel.  
**Fichier cible** : `data/raw/insee/filosofi_[annee].csv`

#### 3c. Emploi et population active

**URL** : https://www.insee.fr/fr/statistiques (Base permanente des emplois)  
**Variables** : taux de chômage, part cadres, part ouvriers, part employés  
**Source principale** : Recensement population INSEE (RP) — disponible 
par millésime (2012, 2014, 2016, 2018, 2020)  
**Fichier cible** : `data/raw/insee/rp_[annee]_commune.csv`

---

### 4. Code officiel géographique (COG)

**URL** : https://www.insee.fr/fr/information/6800675  
**Usage** : Harmonisation des codes INSEE après fusions de communes  
**Format** : Fichier CSV avec historique des communes (création, fusion, scission)  
**Fichier cible** : `data/raw/geo/cog_communes.csv`

**Package R alternatif** : `COGugaison` — traçabilité automatique des codes INSEE  
après fusions. Vérifier disponibilité CRAN.

---

### 5. Observatoire des Territoires (optionnel)

**URL** : https://www.observatoire-des-territoires.gouv.fr/  
**Usage** : Indicateurs socio-économiques complémentaires par commune  
**Fichier cible** : `data/raw/insee/obs_territoires_[indicateur].csv`

---

## Fichiers nécessitant téléchargement manuel

En cas d'échec du téléchargement automatique, les fichiers suivants doivent 
être téléchargés manuellement et placés dans les dossiers indiqués :

```
data/raw/
├── acv/
│   └── acv_liste_officielle.csv        ← depuis data.gouv.fr/ACV
├── elections/
│   ├── pres2012_t1_communes.csv        ← Ministère de l'Intérieur
│   ├── leg2012_t1_communes.csv
│   ├── eur2014_communes.csv
│   ├── pres2017_t1_communes.csv
│   ├── leg2017_t1_communes.csv
│   ├── eur2019_communes.csv            ← PRIORITÉ ABSOLUE
│   ├── pres2022_t1_communes.csv
│   ├── leg2022_t1_communes.csv
│   ├── eur2024_communes.csv
│   └── leg2024_t1_communes.csv
├── insee/
│   ├── populations_legales_[annee].csv
│   ├── filosofi_[annee].csv
│   └── rp_[annee]_commune.csv
└── geo/
    └── cog_communes.csv
```

---

*Dernière mise à jour : 2026-04-22*
