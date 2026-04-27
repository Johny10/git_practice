# Téléchargements manuels requis

L'accès automatique aux serveurs data.gouv.fr et INSEE est bloqué dans
l'environnement d'exécution. **Tu dois télécharger les fichiers ci-dessous
manuellement** et les placer dans les dossiers indiqués.

---

## PRIORITÉ ABSOLUE (sans ces fichiers, rien ne tourne)

### 1. Liste des villes Action Cœur de Ville

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/action-coeur-de-ville/ |
| **Alternative** | https://opendata.caissedesdepots.fr/explore/dataset/villes_action_coeurdeville/ |
| **Dossier cible** | `data/raw/acv/` |
| **Nom fichier** | `acv_liste_officielle.csv` (ou `.xlsx`) |
| **Ce qu'on cherche** | Une ligne par ville ACV avec au minimum : code INSEE 5 chiffres, nom commune |

> Sur la page data.gouv.fr, cherche le bouton "Télécharger" ou "Fichiers".
> Sur la page Caisse des Dépôts, clique "Exporter → CSV".

---

### 2. Résultats de la Présidentielle 2012 — T1 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/election-presidentielle-2012-resultats-par-commune/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `pres2012_t1_communes.csv` |
| **Format attendu** | 1 ligne par commune × candidat, colonnes : code INSEE, voix, suffrages exprimés, inscrits |

---

### 3. Résultats des Européennes 2014 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/elections-europeennes-2014-resultats-par-communes/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `eur2014_communes.csv` |

---

### 4. Résultats de la Présidentielle 2017 — T1 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/election-presidentielle-des-23-avril-et-7-mai-2017/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `pres2017_t1_communes.csv` |

---

### 5. ★ Résultats des Européennes 2019 — par commune ★ (scrutin post-ACV clé)

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/elections-europeennes-du-26-mai-2019/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `eur2019_communes.csv` |
| **Note** | C'est la variable dépendante post-traitement principale. Priorité absolue. |

---

## PRIORITÉ HAUTE (pour les variables de matching)

### 6. INSEE — Populations légales communales

| | |
|---|---|
| **URL** | https://www.insee.fr/fr/statistiques/6683031 |
| **Millésimes à télécharger** | 2012, 2014, 2016, 2017, 2018 |
| **Dossier cible** | `data/raw/insee/` |
| **Noms fichiers** | `populations_legales_2012.csv`, `populations_legales_2014.csv`, etc. |
| **Variable clé** | Population municipale par commune (colonne PMUN ou similaire) |
| **Note** | Sur la page, chaque millésime a son propre fichier ZIP. Dézipper et placer le CSV. |

---

### 7. INSEE — Filosofi : revenus médians par commune

| | |
|---|---|
| **URL** | https://www.insee.fr/fr/statistiques/6036907 (Filosofi 2019) |
| **Années idéales** | 2012, 2015, 2017 |
| **Dossier cible** | `data/raw/insee/` |
| **Noms fichiers** | `filosofi_2012.csv`, `filosofi_2015.csv`, `filosofi_2017.csv` |
| **Variable clé** | Revenu médian par unité de consommation (colonne Q2 ou MED dans Filosofi) |
| **Attention** | Filosofi ne couvre pas les communes < ~1 000 hab. C'est normal. |

> Navigation sur insee.fr :  
> Statistiques → Revenus – Pouvoir d'achat → Revenus et pauvreté des ménages → Filosofi  
> Puis "Télécharger" → CSV par commune.

---

### 8. INSEE — Recensement de population (emploi, CSP)

| | |
|---|---|
| **URL** | https://www.insee.fr/fr/statistiques/6543200 (RP 2019, base commune) |
| **Millésimes** | RP 2012, RP 2017 (ou 2018) |
| **Dossier cible** | `data/raw/insee/` |
| **Noms fichiers** | `rp2012_commune.csv`, `rp2017_commune.csv` |
| **Variables clés** | Taux de chômage, part cadres (CS3), part ouvriers (CS6) |

> Sur le site INSEE, cherche "Recensement de population — Fichiers détail communes".
> Sélectionner la base "Activité des résidents" par commune.

---

## PRIORITÉ BASSE (extensions robustesse)

### 9. Législatives 2012 T1 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/elections-legislatives-2012-resultats-par-commune/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `leg2012_t1_communes.csv` |

---

### 10. Législatives 2017 T1 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/elections-legislatives-des-11-et-18-juin-2017/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `leg2017_t1_communes.csv` |

---

### 11. Présidentielle 2022 T1 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/election-presidentielle-des-10-et-24-avril-2022/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `pres2022_t1_communes.csv` |

---

### 12. Européennes 2024 — par commune

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/elections-europeennes-du-9-juin-2024/ |
| **Dossier cible** | `data/raw/elections/` |
| **Nom fichier** | `eur2024_communes.csv` |

---

### 13. Code Officiel Géographique (COG) communes

| | |
|---|---|
| **URL** | https://www.insee.fr/fr/information/6800675 |
| **Dossier cible** | `data/raw/geo/` |
| **Nom fichier** | `cog_communes_2024.csv` |
| **Usage** | Harmonisation des codes INSEE après fusions de communes (2015–2024) |

---

### 14. Shapefile communes France (pour Carte 1)

| | |
|---|---|
| **URL** | https://www.data.gouv.fr/fr/datasets/contours-des-communes-de-france-simplifie-avec-regions-et-departements-doutre-mer/ |
| **Alternative** | https://geoservices.ign.fr/adminexpress (ADMIN-EXPRESS COG) |
| **Dossier cible** | `data/raw/geo/` |
| **Format** | `.shp` ou `.geojson` (communes de France métropolitaine) |
| **Usage** | Génération de la Carte 1 (localisation des villes ACV) |

---

## Checklist de vérification

Avant de lancer `python main.py`, vérifier que ces fichiers existent :

```
data/raw/
├── acv/
│   └── acv_liste_officielle.csv          ✓ / ✗
├── elections/
│   ├── pres2012_t1_communes.csv          ✓ / ✗
│   ├── eur2014_communes.csv              ✓ / ✗
│   ├── pres2017_t1_communes.csv          ✓ / ✗
│   ├── eur2019_communes.csv              ✓ / ✗  ← PRIORITÉ ABSOLUE
│   ├── pres2022_t1_communes.csv          ✓ / ✗  (robustesse)
│   └── eur2024_communes.csv              ✓ / ✗  (robustesse)
├── insee/
│   ├── populations_legales_2017.csv      ✓ / ✗
│   ├── filosofi_2017.csv                 ✓ / ✗
│   └── rp2017_commune.csv                ✓ / ✗
└── geo/
    └── cog_communes_2024.csv             ✓ / ✗  (optionnel)
```

---

## Minimum vital pour une première estimation

Si tu es pressé, ces **4 fichiers seuls** permettent une estimation DiD partielle :

1. `data/raw/acv/acv_liste_officielle.csv`
2. `data/raw/elections/pres2017_t1_communes.csv`
3. `data/raw/elections/eur2019_communes.csv`
4. `data/raw/elections/pres2012_t1_communes.csv` (pour pre-trends)

Les variables de matching (Filosofi, RP) s'ajoutent ensuite pour la spécification complète.

---

## Conseil pratique pour data.gouv.fr

Sur chaque page data.gouv.fr, les résultats électoraux officiels du
Ministère de l'Intérieur sont généralement dans un fichier nommé :
- `Presidentielle_AAAA_T1_Resultats_communes.csv`
- `Europeennes_AAAA_Resultats_communes_csv.zip` (à dézipper)

Le format varie légèrement selon les années (colonnes différentes).
Le script `03_clean_elections.py` est conçu pour détecter automatiquement
les colonnes pertinentes dans les différents formats.
