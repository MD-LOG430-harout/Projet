# Soutenance CanTelcoX Phase 2 — démo complète et questions par rôle

Ce document est le fil conducteur officiel de l'équipe. La présentation dure
12 à 15 minutes, puis chaque membre répond aux questions liées à son rôle.

## Mise en situation

L'enseignant joue le rôle du CTO de CanTelcoX. Nous sommes l'équipe
d'architecture mandatée pour lui recommander une évolution technique crédible.
Nous ne lui présentons donc pas « un projet scolaire » ni une liste de
technologies : nous lui présentons un problème d'entreprise, une solution, les
preuves qu'elle fonctionne, ses coûts et risques, puis une recommandation.

Notre posture :

- appeler l'enseignant « Monsieur le CTO » ou simplement « vous »;
- parler de valeur, de risque et de décisions avant de parler d'outils;
- expliquer pourquoi chaque mécanisme est utile à CanTelcoX;
- ne jamais prétendre que le prototype est déjà prêt pour la production;
- conclure par une recommandation claire et conditionnelle.

## Message central

CanTelcoX conserve les six services et les cas d'utilisation de la Phase 1,
mais remplace les longues chaînes REST internes par une collaboration
événementielle. Une commande est acceptée avec `202 Accepted`, enregistrée avec
son événement dans une Transactional Outbox, puis une saga chorégraphiée progresse
par Kafka jusqu'à `CONFIRMEE` ou `ANNULEE`.

## Proposition faite au CTO

> Nous recommandons d'adopter progressivement cette architecture événementielle
> pour les processus télécom longs, en conservant REST pour les interactions
> immédiates. Le prototype valide la faisabilité, la cohérence et
> l'observabilité de la solution. Avant une mise en production, nous recommandons
> un Kafka hautement disponible, des tests de charge supplémentaires, une
> optimisation de la latence d'acceptation et la validation complète de
> l'intégration free5GC.

## Répartition et chronométrage

| Temps | Responsable | Contenu | Écran |
|---|---|---|---|
| 0:00–1:15 | Rôle 1 | Problème, objectifs et stratégie | Diapositive 1 |
| 1:15–3:00 | Rôle 2 | Contextes DDD, agrégats et invariants | Carte des contextes |
| 3:00–4:45 | Rôle 3 | Saga, Kafka, Outbox et idempotence | Diagramme de séquence |
| 4:45–5:45 | Rôle 4 | Déploiement et architecture hexagonale | Diagramme de déploiement |
| 5:45–6:45 | Rôle 5 | Qualité, décisions, résultats et limites | Diapositive 4 |
| 6:45–10:15 | Rôle 3, assisté du rôle 2 | Démo nominale | Terminal |
| 10:15–12:15 | Rôle 3, assisté du rôle 5 | Démo de compensation | Terminal |
| 12:15–13:15 | Rôle 4 | Observabilité | Jaeger et Grafana |
| 13:15–14:00 | Rôle 1 | Conclusion | Diapositive 4 |
| 14:00–15:00 | Équipe | Marge de sécurité | — |

Une seule personne contrôle le clavier pendant toute la démo. Chaque membre
connaît néanmoins les commandes de secours.

## Préparation avant l'arrivée de l'enseignant

Depuis la racine du dépôt :

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-reset.ps1 -Force
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

Ouvrir à l'avance :

- le PowerPoint de quatre diapositives;
- un terminal PowerShell agrandi;
- Swagger : <http://localhost:8081>;
- Jaeger : <http://localhost:16686>;
- Grafana : <http://localhost:3000>;
- Prometheus : <http://localhost:9090>.

Ne pas montrer le fichier `.env`, les secrets, ni des données personnelles.
Pour le parcours nominal, conserver `HLR_ENABLED=false` : le mock rend la démo
reproductible. Ne pas présenter free5GC réel comme un succès validé.

## Script mot à mot

### Rôle 1 — architecte solution

> Monsieur le CTO, votre plateforme CanTelcoX doit exécuter des parcours comme
> la commande, le paiement et l'activation d'une ligne. Aujourd'hui, une longue
> chaîne REST dépend de la disponibilité et de la latence de tous les services
> appelés. Un seul service lent ou indisponible peut immobiliser tout le
> parcours et rendre son état difficile à suivre.
>
> Notre recommandation est une évolution progressive, pas une réécriture. Nous
> conservons vos six services et vos API publiques, puis nous rendons les
> processus longs asynchrones avec Kafka, une Transactional Outbox, des
> consommateurs idempotents et une saga chorégraphiée. La valeur recherchée est
> un meilleur découplage, une reprise contrôlée après incident et une
> traçabilité de bout en bout. Le coût assumé est une complexité opérationnelle
> plus élevée, que nous encadrons avec des contrats, des métriques et des
> runbooks.

Transition :

> Pour montrer que ce découpage respecte le métier, je passe la parole au
> responsable DDD.

### Rôle 2 — responsable DDD

> Pour limiter le coût du changement et permettre aux équipes d'évoluer
> indépendamment, chaque contexte possède une capacité et ses données : clients-identité gère
> l'inscription, l'authentification et le MFA; catalogue-offres gère les offres;
> commandes-activations possède le cycle de vie visible de la commande;
> lignes-services possède l'activation, le MSISDN et la portabilité;
> usage-facturation possède les paiements et la facturation; conformité-audit
> possède le journal immuable.
>
> L'agrégat central du parcours est `Commande`. Il commence à `EN_COURS` et
> termine soit à `CONFIRMEE`, soit à `ANNULEE`. Un état terminal ne recule pas,
> un événement dupliqué ne produit pas deux effets, une ligne ne devient active
> qu'après le provisionnement, et l'audit reste append-only. Les systèmes
> externes sont protégés par des adapters et des couches anticorruption qui
> traduisent leurs modèles en faits internes. Pour CanTelcoX, cela réduit le
> risque qu'un changement chez un fournisseur contamine tout le système.

Transition :

> Ces frontières sont reliées par le flux événementiel que nous allons maintenant
> expliquer.

### Rôle 3 — architecture dynamique et événementielle

> `POST /v1/orders` valide ce qui doit l'être immédiatement, puis écrit la
> commande `EN_COURS`, l'état de saga et `CommandePassee` dans l'Outbox, dans une
> même transaction MySQL. L'API retourne `202`, car la commande est acceptée,
> mais pas encore terminée.
>
> Le poller Outbox publie ensuite dans Kafka. Facturation consomme
> `CommandePassee` et publie `PaiementAutorise` ou `PaiementRefuse`. Lignes
> consomme l'autorisation et publie `LigneActivee` ou `ActivationEchouee`.
> Commandes consomme le résultat et termine à `CommandeConfirmee` ou
> `CommandeAnnulee`. Il n'y a pas de transaction distribuée ni d'orchestrateur
> central : chaque service fait une transaction locale. La livraison est
> at-least-once; `processed_events` et les gardes d'état rendent les effets
> idempotents. Autrement dit, une panne temporaire ne nous oblige pas à perdre
> une commande, et une nouvelle livraison ne doit pas facturer le client deux
> fois.

Transition :

> Voyons maintenant comment ces éléments sont empaquetés et isolés dans le code.

### Rôle 4 — déploiement et architecture hexagonale

> Docker Compose déploie les six services, NGINX, MySQL, Redis, Kafka en mode
> KRaft, PortabilityHub et la chaîne Prometheus, Grafana, OpenTelemetry et
> Jaeger. Chaque service possède son schéma et ne modifie pas les données d'un
> autre contexte.
>
> Dans le code, REST, Kafka, MySQL, HLR/HSS et PortabilityHub sont des adapters.
> Les décisions métier et transitions d'état restent dans les couches
> application et domaine. Cette frontière hexagonale permet de remplacer, par
> exemple, le mock HLR par l'adapter free5GC sans réécrire le cœur métier. Le
> déploiement Compose démontre la solution de façon reproductible; nous ne le
> présentons pas comme la topologie de production finale.

Transition :

> Cette solution apporte des gains, mais nous les présentons avec leurs mesures
> et leurs limites réelles.

### Rôle 5 — qualité, ADR et risques

> La décision la plus structurante est la collaboration événementielle avec
> Kafka, Outbox, saga chorégraphiée et consommateurs idempotents. Les risques de
> perte sont réduits par l'Outbox, les doublons par `processed_events`, et les
> échecs techniques par retry et DLQ.
>
> La validation enregistrée compte 97 tests réussis, aucun échec et 12 tests
> ignorés. Le P95 de la saga nominale est de 2,0 secondes, celui de la
> compensation de 2,9543 secondes, le lag Kafka après drainage est nul et aucune
> ligne Outbox ne reste en attente. Nous sommes transparents : le P95
> d'acceptation de 810 ms manque la cible de 250 ms, le débit de 489,91 requêtes
> par seconde manque la cible de 1000, et le succès réel free5GC n'a pas été
> validé.

> Notre recommandation au CTO est donc conditionnelle : poursuivre cette
> architecture, mais ne pas passer en production avant d'avoir corrigé les
> objectifs de performance manqués, déployé Kafka avec réplication et validé le
> véritable chemin free5GC.

## Démo en direct

### 1. Vérification rapide

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
```

Dire :

> Avant de vous demander d'approuver l'architecture, nous vérifions que tous ses
> composants sont opérationnels. Toutes les requêtes publiques passent par la
> Gateway, comme elles le feraient pour un consommateur de la plateforme.

### 2. Saga nominale

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

Pointer successivement :

1. `HTTP 202` et l'en-tête `Location`;
2. l'état initial `EN_COURS`;
3. le même `orderId` après replay avec la même `Idempotency-Key`;
4. l'état final `CONFIRMEE`;
5. les lignes `outbox_events`, `processed_events`, `saga_state` et d'audit.

Dire :

> Le replay prouve l'idempotence de l'API. La chaîne
> `CommandePassee → PaiementAutorise → LigneActivee → CommandeConfirmee` prouve
> ensuite la progression asynchrone. L'Outbox protège contre la perte entre la
> transaction métier et Kafka; le consommateur protège contre les doublons.
> Pour CanTelcoX, cela signifie qu'une réponse rapide au client ne sacrifie ni le
> suivi de la commande ni la sécurité des effets métier.

### 3. Compensation

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
```

Dire :

> Nous forçons maintenant un refus de paiement. C'est un échec métier et non un
> cas de DLQ. `PaiementRefuse` entraîne `CommandeAnnulee`, et l'état terminal est
> `ANNULEE`. Le script restaure ensuite automatiquement la configuration
> nominale. Nous montrons ce chemin parce qu'un CTO doit évaluer le comportement
> en échec, pas seulement le scénario heureux.

Si le temps le permet, ajouter :

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

> PortabilityHub reste externe et synchrone pour l'initiation. Ses callbacks
> HTTP sont normalisés par l'ACL : `port_completed` devient `NumeroPorte`, alors
> que `rejected` ou `cancelled` devient `PortabiliteEchouee`.

### 4. Observabilité

Dans Jaeger, chercher `svc-commandes-activations`. Dans Grafana, ouvrir
`CanTelcoX Golden Signals`.

Dire :

> Le même parcours est corrélé par `trace_id`, `correlation_id` et `saga_id`.
> Grafana expose trafic, erreurs, latence et saturation. Si la trace visuelle
> n'est pas encore disponible, les identifiants corrélés imprimés dans l'audit
> constituent notre preuve de secours.

### Conclusion — rôle 1

> Monsieur le CTO, nous avons montré une évolution réalisable de CanTelcoX : acceptation
> REST, transaction locale avec Outbox, propagation Kafka, saga nominale,
> compensation, idempotence, audit et observabilité. Notre architecture atteint
> plusieurs objectifs de résilience et de traçabilité sans exiger une réécriture
> des services existants. Nous vous recommandons d'autoriser la prochaine étape
> sous trois conditions : rendre Kafka hautement disponible, atteindre les cibles
> de performance et valider free5GC de bout en bout. Cette décision permet de
> conserver les gains du prototype tout en maîtrisant le risque de production.

## Ce que le CTO doit retenir

| Préoccupation du CTO | Réponse de l'équipe |
|---|---|
| Pourquoi changer? | Les chaînes synchrones sont fragiles pour les longs parcours télécom. |
| Quelle valeur? | Reprise après incident, découplage, traçabilité et évolution indépendante. |
| Faut-il tout réécrire? | Non, les six services et les API publiques sont conservés. |
| Comment éviter la perte? | Transactional Outbox et reprise de publication. |
| Comment éviter les doubles effets? | Idempotency-Key, `processed_events` et gardes d'état. |
| Comment gérer les échecs? | Compensation métier; retry et DLQ pour les pannes techniques. |
| Comment exploiter la solution? | Traces, métriques, audit, dashboards et runbooks. |
| Est-elle prête pour la production? | Pas encore; trois conditions de passage restent à satisfaire. |

## Questions probables par rôle

### Rôle 1

**Pourquoi l'événementiel plutôt qu'une chaîne REST?**  
Une chaîne synchrone dépend de tous les services en même temps. L'événementiel
découple leur disponibilité et convient aux processus télécom longs, avec comme
coût davantage d'infrastructure et de cohérence éventuelle.

**Pourquoi des microservices plutôt qu'un monolithe modulaire?**  
Les capacités ont des données, intégrations et contraintes distinctes. Le projet
de Phase 1 possédait déjà ces frontières, et la Phase 2 doit précisément traiter
leur collaboration distribuée.

**Qu'est-ce qui est hors du système?**  
Les utilisateurs, HLR/HSS/free5GC, PortabilityHub et la passerelle de paiement
simulée. Ils sont accessibles par adapters, jamais comme parties du domaine.

### Rôle 2

**Pourquoi ces bounded contexts?**  
Ils suivent la propriété métier : identité, catalogue, commandes, lignes,
facturation et audit. Aucun service ne modifie directement l'état métier d'un
autre.

**Pourquoi pas une seule transaction?**  
Les données sont distribuées et des systèmes externes participent. La saga
utilise des transactions locales et des compensations métier sans verrou global.

**Quel est le rôle d'une ACL?**  
Elle empêche les modèles et statuts externes de contaminer le domaine interne;
elle les traduit en résultats comme `LigneActivee` ou `PortabiliteEchouee`.

### Rôle 3

**La livraison est-elle exactly-once?**  
Non. Kafka et l'Outbox fournissent une livraison at-least-once. L'effet métier
devient pratiquement unique grâce à `processed_events` et aux gardes d'agrégat.

**Quand l'offset Kafka est-il commité?**  
Après le succès de la transaction locale qui enregistre l'événement traité, les
changements métier et le nouvel événement Outbox éventuel.

**Différence entre compensation et DLQ?**  
Une compensation répond à un résultat métier prévu, par exemple un paiement
refusé. La DLQ conserve un message après l'épuisement des retries causés par un
échec technique.

**Pourquoi chorégraphie et non orchestration?**  
Chaque service réagit aux faits qu'il connaît et aucun coordinateur central ne
commande toutes les étapes. Cela réduit le couplage central, mais exige de bons
contrats et une excellente observabilité.

### Rôle 4

**Où se trouve la frontière hexagonale?**  
Routes REST, consommateurs Kafka, repositories MySQL et clients HTTP sont aux
bords. Les handlers applicatifs, modèles et invariants forment le cœur.

**Kafka est-il hautement disponible?**  
Non. Le laboratoire utilise un broker et un facteur de réplication de 1. C'est
reproductible, mais insuffisant pour la production.

**Pourquoi Docker Compose?**  
Il rend toute la topologie reproductible sur la machine du cours. En production,
il faudrait une plateforme et des services de données hautement disponibles.

### Rôle 5

**Quelle décision est la plus structurante?**  
Le passage à une collaboration événementielle, car il entraîne Kafka, Outbox,
saga, idempotence, compensation, audit et observabilité.

**Pouvez-vous dire que tous les NFR sont atteints?**  
Non. Les temps de saga, le drainage Kafka et l'Outbox ont réussi; l'acceptation
P95 et le débit n'ont pas atteint leurs cibles. Nous ne revendiquons que les
résultats mesurés.

**Quel est le plus grand risque restant?**  
Les performances sous charge et la compatibilité free5GC réelle. Le parcours
nominal utilise donc le mock HLR reproductible et les limites sont documentées.

## Réponses d'urgence en une phrase

- **Outbox :** état métier et événement sont écrits atomiquement dans MySQL.
- **Idempotence :** même message reçu deux fois, un seul effet métier.
- **Saga :** suite de transactions locales avec compensations métier.
- **202 :** accepté pour traitement, pas encore terminé.
- **Cohérence :** éventuelle entre services, forte dans chaque transaction locale.
- **Kafka key :** `aggregateId` conserve l'ordre utile pour un même agrégat.
- **Audit :** append-only et corrélé par trace, saga et corrélation.
- **Retry :** nouvelle tentative d'un échec technique transitoire.
- **DLQ :** conservation après épuisement des tentatives.
- **Limite majeure :** un seul broker Kafka n'offre pas la haute disponibilité.

## Plan de secours

- Saga nominale en échec : relancer `-Step Preflight`, puis seulement
  `-Step Acceptance`.
- Compensation en échec : présenter les preuves enregistrées et vérifier que
  `PAYMENT_GATEWAY_FORCE_REFUSAL=false` est restauré.
- Jaeger vide : montrer `trace_id`, `correlation_id` et `saga_id` dans l'audit.
- Grafana vide : montrer `up` dans Prometheus et les preuves de performance.
- PortabilityHub indisponible : montrer son health check et les tests enregistrés.
- Ne jamais improviser un succès free5GC réel : expliquer honnêtement la limite.

## Règles de présentation

1. Expliquer d'abord ce que la preuve va démontrer, puis exécuter la commande.
2. Ne pas lire tout le terminal; pointer uniquement le statut, l'identifiant et
   les tables qui prouvent le mécanisme.
3. Dire « nous » pour le projet et « mon rôle » pour la responsabilité défendue.
4. Si une réponse est inconnue, la rattacher à une limite documentée au lieu de
   deviner.
5. Répéter la démo complète au moins deux fois avec un chronomètre.
6. Ne pas dire « pour le cours, nous devions utiliser Kafka »; dire « Kafka
   répond au besoin de découplage et de reprise, avec les compromis suivants ».
7. Ne pas énumérer les dossiers du dépôt; relier chaque preuve technique à une
   décision que le CTO doit prendre.
