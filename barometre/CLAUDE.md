# Baromètre France - agenda médiatique vs préoccupations du public

## Objectif
Pour la France, suivre dans le temps :
1. quels **enjeux** occupent l'écosystème informationnel (offre),
2. quels enjeux préoccupent le public (demande),
3. l'écart et le décalage temporel entre les deux (qui précède qui).

Phase 2 : passer des enjeux aux **récits / cadrages** au sein de chaque enjeu.

Contrainte de rigueur : chaque série affichée doit indiquer sa source, sa couverture et ses angles morts. Ne jamais présenter une série comme "tout l'écosystème".

## Grille de catégories (décision structurante)
Utiliser la liste d'enjeux d'Ipsos What Worries the World comme grille commune, parce que c'est la série publique mensuelle. Chaque enjeu = une requête mots-clés en français, versionnée dans `config/issues.yaml`.
Garder une table de correspondance vers les grands thèmes du Comparative Agendas Project (CAP), pour pouvoir comparer avec des données académiques.

## Sources

### Médias en ligne (offre) - Phase 1
- **GDELT DOC 2.0 API** : `sourcecountry:FR` et/ou `sourcelang:french`, mode `timelinevolraw` par enjeu. Attention : `timelinevol` = part de la couverture surveillée, pas un nombre d'articles.
- Option plus rigoureuse : GDELT GKG via BigQuery (`bq` / `gcloud`), filtrage par thèmes GKG et domaines français.
- **Media Cloud** (compte gratuit, clé API) : collection France, comptages par requête et par jour. Sert de contrôle croisé de GDELT.

### Télévision (offre) - historique seulement
- INA, "Classement thématique des sujets de journaux télévisés (janvier 2000 - décembre 2020)" sur data.gouv.fr. S'arrête en 2020 : sert à **valider** les séries web sur 2015-2020, pas au suivi courant.
- Angle mort assumé après 2020 : la TV et la radio ne sont pas couvertes en continu.

### Public (demande) - Phase 1
- **Ipsos What Worries the World**, série France, mensuelle. Pas d'API : extraire les pourcentages des PDF/pages mensuelles dans `data/ipsos_fr.csv` (colonnes : mois, enjeu, pct). Noter la taille d'échantillon France si elle est publiée (à vérifier, ne pas supposer).
- **Google Trends FR** : signal d'attention rapide. L'API officielle est en alpha sur candidature ; les bibliothèques non officielles sont fragiles. Isoler ce module pour pouvoir le remplacer.

### Réseaux sociaux - Phase 3
- Accès ouverts à tester : YouTube Data API (titres de vidéos en français par enjeu), Bluesky (flux public), Reddit API.
- Meta Content Library et l'accès chercheurs DSA (art. 40) : nécessitent une affiliation académique ou associative. Hors périmètre tant qu'on n'a pas cette affiliation.
- Angles morts assumés : WhatsApp, Telegram privé, une grande partie de TikTok, X (API coûteuse).

## Analyses
1. Séries mensuelles normalisées par enjeu : part de la couverture médiatique vs % de citations Ipsos.
2. Écart offre-demande par enjeu et par mois (quels enjeux sont sur- ou sous-médiatisés par rapport aux préoccupations).
3. Corrélations croisées décalées (lags de 0 à 6 mois) médias -> public et public -> médias. Présenter comme une association temporelle, **pas** comme une preuve causale d'agenda-setting.

## Validation (obligatoire avant tout tableau de bord)
- Pour chaque requête d'enjeu : échantillonner 50 articles, coder à la main pertinent / non pertinent, et noter la précision. Réviser la requête si précision < 0,8.
- Comparer les séries GDELT et Media Cloud : si elles divergent fortement, le signaler au lieu d'en choisir une.
- Sur 2015-2020 : corréler les séries web avec la série TV de l'INA.

## Phase 2 - récits
Au sein de chaque enjeu, échantillonner N articles par mois et classer leur cadrage avec un modèle de langage, en partant du Policy Frames Codebook (Boydstun et al.). Valider sur un sous-échantillon codé à la main (accord inter-codeur) avant d'agréger. Côté public, il n'existe pas de série équivalente : le dire explicitement dans l'interface.

## Livrable
- Pipeline Python (`collect/`, `process/`, `analysis/`), données en CSV/Parquet versionnées.
- Tableau de bord (Streamlit ou page HTML statique) avec : courbes par enjeu, écart offre-demande, panneau "couverture et angles morts" pour chaque source.
- Collecte relançable (cron hebdomadaire).

## Ordre de travail pour Claude Code
1. Vérifier l'accès à chaque API (GDELT, Media Cloud) et lister ce qui marche réellement.
2. Écrire `config/issues.yaml` (requêtes FR) et me le montrer **avant** de collecter.
3. Collecter 2020-aujourd'hui pour GDELT et Media Cloud.
4. Construire `data/ipsos_fr.csv` et me demander de vérifier un mois au hasard.
5. Lancer la validation des requêtes, puis seulement après, les analyses et le tableau de bord.
