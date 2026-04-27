# Journal des décisions méthodologiques

Ce fichier documente toutes les décisions prises au cours du projet, avec justification.
Il est mis à jour au fur et à mesure de l'avancement.

---

## Format

Chaque entrée suit le schéma :
- **Date** : date de la décision
- **Étape** : numéro de l'étape concernée
- **Décision** : ce qui a été décidé
- **Justification** : pourquoi
- **Alternative considérée** : ce qui a été écarté et pourquoi

---

## D-001 — Unité d'analyse : commune plutôt que bureau de vote

- **Date** : 2026-04-22
- **Étape** : Design général
- **Décision** : L'unité d'analyse principale est la commune (code INSEE).
- **Justification** : Les données socio-économiques INSEE (Filosofi, emploi) sont 
  disponibles au niveau communal mais pas au niveau bureau de vote. La liste ACV 
  est également définie au niveau commune. Le niveau bureau de vote est réservé 
  à une extension si temps et données disponibles.
- **Alternative** : Bureau de vote — utile car ACV cible le centre-ville alors 
  que le vote agrège toute la commune (limite de la mesure). Retenu comme extension 
  future avec géocodage Géoplateforme IGN.

---

## D-002 — Groupe contrôle : villes moyennes 20 000–100 000 hab.

- **Date** : 2026-04-22
- **Étape** : Design général
- **Décision** : Le groupe contrôle comprend toutes les communes de 20 000 à 
  100 000 habitants en France métropolitaine, hors Paris petite couronne (75, 92, 93, 94), 
  hors communes ACV, hors communes d'outre-mer.
- **Justification** : ACV cible les villes moyennes. Utiliser des communes hors 
  de cette strate de taille créerait une incomparabilité structurelle. Le seuil 
  20 000–100 000 hab. correspond à la définition administrative des villes moyennes 
  françaises (ANCT). La petite couronne parisienne est exclue car soumise à des 
  dynamiques urbaines incomparables (pression immobilière, desserte transports, 
  économie métropolitaine).
- **Alternative** : Inclure toutes les villes hors Paris — écarté (biais de 
  composition trop fort). Utiliser uniquement les communes ayant candidaté mais 
  non retenues — écarté (pas de données publiques sur les candidatures rejetées).

---

## D-003 — Fenêtre temporelle principale : 2012–2019

- **Date** : 2026-04-22
- **Étape** : Design général
- **Décision** : La fenêtre principale d'estimation va de 2012 (présidentielle T1) 
  à 2019 (européennes). L'extension à 2022–2024 est réservée aux robustness checks.
- **Justification** : 
  (1) Les européennes 2019 constituent le seul scrutin national post-ACV 
  (sélection mars 2018) avant deux confondeurs majeurs : le plan France Relance 
  (100 Md€, 2020–2022) et les effets durables de la crise Covid-19.
  (2) Cette fenêtre permet d'avoir 3 points pré-traitement (2012, 2014, 2017) 
  suffisants pour tester les parallel trends.
  (3) Les Gilets Jaunes (nov. 2018 – mars 2019) constituent un choc concomitant 
  non négligeable ; leur effet est discuté comme limitation.
- **Alternative** : Fenêtre 2012–2022 — retenue comme extension avec contrôle 
  France Relance, mais identifiée comme moins propre causalement.

---

## D-004 — Variable dépendante : part suffrages exprimés T1

- **Date** : 2026-04-22
- **Étape** : Design général
- **Décision** : La variable dépendante est la part de suffrages exprimés (et non 
  inscrits) obtenue par le RN/FN au premier tour de chaque scrutin national.
- **Justification** : 
  (1) Les suffrages exprimés sont moins sensibles aux variations de participation 
  (abstention différentielle ACV vs non-ACV biaiserait les résultats en parts des inscrits).
  (2) Le T1 reflète la préférence sincère des électeurs (T2 est stratégique).
  (3) La part plutôt que le nombre de voix neutralise les effets de taille démographique.
- **Alternative** : Part des inscrits — retenue comme check de robustesse. 
  Nombre absolu de voix — écarté (non comparable entre communes de tailles différentes).

---

## D-005 — Méthode d'estimation : Callaway-Sant'Anna (2021)

- **Date** : 2026-04-22
- **Étape** : Étape 5
- **Décision** : Méthode principale = Callaway & Sant'Anna (2021), package `did` en R.
- **Justification** : 
  (1) Le traitement ACV est simultané (toutes les villes sélectionnées en mars 2018) 
  → pas de staggered adoption stricto sensu, mais CS(2021) reste la référence 
  robuste pour DiD avec covariates et tests de pre-trends.
  (2) CS(2021) est robuste aux effets hétérogènes du traitement (problème Goodman-Bacon).
  (3) Il permet d'intégrer le propensity score matching directement (argument `xformla`).
  (4) Il produit nativement les event study plots et les tests de pre-trends.
- **Alternative** : TWFE classique — retenu comme robustness check (susceptible 
  de biais si effets hétérogènes). Sun & Abraham (2021) et Borusyak-Jaravel-Spiess 
  (2024) — retenus comme robustness checks alternatifs.

---

## D-006 — Matching : nearest neighbor 1:3, caliper 0.25 SD

- **Date** : 2026-04-22
- **Étape** : Étape 4
- **Décision** : Propensity score matching nearest neighbor 1:3 avec caliper 0.25 SD, 
  sans remise, via `MatchIt` en R.
- **Justification** : 
  (1) 1:3 (trois contrôles pour chaque traité) maximise la précision sans sacrifier 
  excessivement la balance.
  (2) Le caliper 0.25 SD est la règle empirique standard (Austin 2011) pour éviter 
  les mauvais appariements.
  (3) Sans remise pour garantir l'indépendance des observations dans l'estimation DiD.
- **Alternative** : 1:5 — testé en robustesse. Matching optimal (optmatch) — 
  testé en robustesse. Full matching — peut créer des poids extrêmes, écarté 
  comme méthode principale.

---

## D-007 — Gestion des binômes ACV

- **Date** : 2026-04-22
- **Étape** : Étape 2
- **Décision** : Les binômes ACV (deux communes désignées ensemble) sont traités 
  comme des unités distinctes : chaque commune du binôme reçoit l'indicatrice 
  traitement = 1. Soit N = 234 communes traitées.
- **Justification** : Les résultats électoraux et les données INSEE sont disponibles 
  au niveau commune, pas au niveau binôme. Agréger les binômes imposerait des 
  choix arbitraires de pondération.
- **Alternative** : Traiter le binôme comme une seule unité (N = 222) — retenu 
  comme robustness check avec agrégation par pondération démographique.

---

## D-008 — Exclusion outre-mer et Paris petite couronne

- **Date** : 2026-04-22
- **Étape** : Design général
- **Décision** : Exclure (a) toutes communes d'outre-mer (codes INSEE > 97000) 
  et (b) communes des départements 75, 92, 93, 94 (Paris + petite couronne).
- **Justification** : 
  (a) L'outre-mer a des structures électorales et socio-économiques fondamentalement 
  différentes (multipartisme local, clientélisme, vote aux présidentielles différent).
  (b) La petite couronne est une zone urbaine dense incomparable aux villes moyennes.
- **Alternative** : Inclure l'outre-mer avec effets fixes régionaux — écarté 
  car la comparabilité est trop faible même après contrôle.

---

## D-009 — Seed aléatoire fixe

- **Date** : 2026-04-22
- **Étape** : Tous scripts
- **Décision** : Seed = `42` dans tous les scripts R utilisant l'aléatoire 
  (`set.seed(42)`). Documenté en tête de chaque script.
- **Justification** : Reproductibilité stricte.

---

## D-010 — Harmonisation codes INSEE : gestion des fusions de communes

- **Date** : 2026-04-22 (à compléter lors de l'étape 2)
- **Étape** : Étape 2
- **Décision** : [À compléter lors de l'exécution de l'étape 2]
- **Justification** : Les fusions de communes (2015–2024) créent des discontinuités 
  dans les codes INSEE. Le package `COGugaison` en R sera utilisé pour 
  harmoniser tous les codes sur la COG 2024 (ou 2019 si données pré-2020 
  trop fragmentées).
- **Contrainte** : Toute commune ACV concernée par une fusion sera documentée 
  individuellement.

---

## D-011 — Honnêteté sur les résultats

- **Date** : 2026-04-22
- **Étape** : Tous
- **Décision** : Si l'ATT estimé est nul, faible, ou statistiquement non 
  significatif, ce résultat est rapporté sans modification de spécification 
  ad hoc. Les sous-échantillons théoriquement motivés (communes 20–50k vs 
  50–100k) sont pré-enregistrés ici avant estimation.
- **Justification** : Règle éthique de non-p-hacking. Un résultat nul bien 
  identifié a de la valeur scientifique.

---

## À documenter lors de l'avancement du projet

- [ ] D-012 : Décisions sur les communes manquantes dans les données électorales
- [ ] D-013 : Seuil de disponibilité des données Filosofi (certaines années manquent pour petites communes)
- [ ] D-014 : Traitement des communes dont la taille croise le seuil 20k/100k entre 2012 et 2019
- [ ] D-015 : Décision sur l'inclusion/exclusion des communes avec données électorales manquantes > 1 scrutin
- [ ] D-016 : Choix de la spécification exacte pour les tests HonestDiD (M̄ à tester)
