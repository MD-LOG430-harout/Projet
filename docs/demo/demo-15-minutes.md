# CanTelcoX Phase 2 — déroulé de soutenance 15 minutes

Aligné sur les six étapes de l'Annexe D.1. Remplace
[demo-10-minutes.md](demo-10-minutes.md), qui reste valable comme version courte
si le temps est réduit.

Règle principale : utiliser le HLR simulé pour le parcours nominal. Ne pas
présenter le provisionnement free5GC réel comme réussi ; la WebConsole fournie
renvoie une représentation incompatible et l'adaptateur compense correctement
avec `SUBSCRIBER_CONFLICT`.

## Avant l'arrivée du correcteur

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-reset.ps1 -Force
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Replay
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Dlq
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Portability
```

Le premier passage construit l'image `cantelcox-test:phase2` si elle manque.

Onglets à ouvrir : Swagger 8081, Jaeger 16686, Grafana 3000, Prometheus 9090,
PortabilityHub `http://localhost:8282/actuator/health`.

## Minutage

| # | Étape Annexe D.1 | Durée | Contenu |
|---|---|---|---|
| 1 | Contexte & objectifs | 1 min 30 | Slide 1 : Phase 1 → Phase 2 |
| 2 | Architecture événementielle | 2 min 30 | Slide 2 : broker, Outbox, saga chorégraphiée |
| 3 | Démo saga nominale | 4 min | `-Step Acceptance` + trace Jaeger de bout en bout |
| 4 | Démo compensation & résilience | 3 min | `-Step Compensation`, `-Step Replay`, `-Step Dlq` |
| 5 | Mesures & gains | 2 min | Grafana + comparatif synchrone ↔ événementiel |
| 6 | Questions | 2 min | — |

Total 15 min. Si le créneau est de 12 min : retirer `-Step Dlq` de l'étape 4
(garder le rejeu) et raccourcir l'étape 2 à 1 min 30.

## Étape 1 — Contexte & objectifs (1 min 30)

Slide 1 uniquement.

> En Phase 1, CanTelcoX coordonnait ses services par appels REST synchrones. La
> Phase 2 garde les six services et les mêmes cas d'utilisation, mais change le
> mode de collaboration : la requête publique est acceptée vite en `202`, le
> service écrit sa ligne métier et son événement Outbox dans la même transaction
> MySQL, puis Kafka porte les étapes de la saga.

## Étape 2 — Architecture événementielle (2 min 30)

Slide 2. Trois mécanismes à nommer explicitement :

- **Broker** : Kafka en KRaft, 11 topics métier + 11 topics `.dlq`, clé = `aggregateId`.
- **Outbox transactionnelle** : `outbox_events` écrite dans la transaction métier,
  relais séparé avec `FOR UPDATE SKIP LOCKED`, publication au moins une fois.
- **Saga chorégraphiée** : pas d'orchestrateur ; `saga_state` est l'état agrégé
  côté commande, les compensations sont des faits métier et non des transactions
  inverses (ADR-007).

## Étape 3 — Démo saga nominale (4 min)

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Acceptance
```

Montrer : `HTTP 202`, l'en-tête `Location`, `orderId`, `sagaId`, le statut initial
`EN_COURS`, le rejeu avec la même `Idempotency-Key` qui renvoie le même `orderId`,
puis `CONFIRMEE`.

```text
CommandePassee -> PaiementAutorise -> LigneActivee -> CommandeConfirmee
```

**Puis la trace, qui est la preuve demandée par l'Annexe D.2.** Ouvrir Jaeger,
service `svc-commandes-activations`, opération `POST /v1/orders`, et déplier la
trace la plus récente : une **trace unique** contient les spans HTTP, les spans
`publish <topic>` et les spans `consume <topic>` des quatre services
consommateurs. Le contexte W3C est injecté dans l'en-tête Kafka `traceparent` et
réextrait à la consommation.

> Le `202` est une acceptation, pas un achèvement. Il n'y a pas d'orchestrateur :
> la facturation consomme `CommandePassee`, les lignes consomment
> `PaiementAutorise`, et le service commande consomme les faits résultants
> jusqu'à un état terminal.

## Étape 4 — Compensation & résilience (3 min)

**a) Compensation métier** (~1 min)

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Compensation
```

`CommandePassee -> PaiementRefuse -> CommandeAnnulee`, statut terminal `ANNULEE`,
puis restauration automatique de la configuration nominale.

> Un refus de paiement n'est pas un cas DLQ. C'est un fait métier consommé par le
> service commande, qui émet `CommandeAnnulee`.

**b) Idempotence par rejeu d'événement** (~1 min)

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Replay
```

Le step republie **à l'identique** un `LigneActivee` déjà traité et compare
l'état avant/après : `processed_events` reste à 1, la commande reste `CONFIRMEE`,
aucun événement n'est réémis. Le compteur `cantelcox_saga_transitions_total`
affiche alors `DUPLICATE` — la preuve que l'événement a bien été **reçu puis
refusé**, et non simplement jamais livré.

**c) Échec technique et DLQ** (~1 min)

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Dlq
```

Un événement JSON valide mais non conforme au schéma est publié sur
`paiement-autorise.v1`. Montrer les 3 tentatives, l'enregistrement déposé dans
`paiement-autorise.v1.dlq` avec `attempts`, `error` et `originalPayload`, et le
fait que l'offset a été commité **après** la publication DLQ : le consommateur
n'est pas bloqué. Rejeu contrôlé : `docs/runbooks/kafka-dlq-replay.md`.

## Étape 5 — Mesures & gains (2 min)

Grafana → dossier `CanTelcoX` → dashboard **`CanTelcoX Event-Driven`** :
lag consommateur par topic, arriéré Outbox, événements produits/consommés,
retries et DLQ, durée de saga P95, transitions de saga. Le dashboard
`CanTelcoX Golden Signals` reste disponible pour la vue HTTP.

Puis le comparatif de [mesures-et-gains.md](mesures-et-gains.md) :

| | Dépendance synchrone coupée | Dépendance événementielle coupée |
|---|---|---|
| Service arrêté | `svc-catalogue-offres` | `svc-lignes-services` |
| Réponses | 5 × **500** en 2,6–3,9 s | 5 × **202**, P95 116 ms |
| Après remise en service | requêtes perdues | sagas convergent seules |

> Le gain n'est pas la latence brute, c'est le découplage temporel : une panne en
> aval ne se propage plus au client. Ce qui reste synchrone reste fragile, et la
> démonstration le montre dans les deux sens.

Chiffres de la pile complète : acceptation P95 **116 ms** (cible < 250 ms
atteinte), convergence de saga P95 **1,5 s**, 20/20 `CONFIRMEE`, suite de tests
**46 passed / 9 skipped / 0 failed**.

Limites à énoncer soi-même : débit non rejoué sur ce poste, compteurs Prometheus
sous-comptés (2 workers gunicorn, un seul registre scrapé), un test d'intégration
Outbox instable en présence des relais en marche, free5GC réel non validé.

Si le temps le permet, `-Step Decoupling` rejoue ces mesures en direct (≈ 2 min).

## Étape 6 — Questions (2 min)

Réponses préparées :

- **« Et si un service tombe au milieu de la saga ? »** La commande reste
  acceptée et la saga reste `EN_COURS` ; au redémarrage elle converge seule
  (mesuré : 0 saga résiduelle). Le `deadline_at` de 60 s est persisté et
  `SagaTimeoutScanner` existe, mais **n'est pas câblé** côté commande — c'est une
  limite connue. Le scanner de timeout de portabilité, lui, tourne bien.
- **« Chorégraphie ou orchestration ? »** ADR-005 : chorégraphie, pas
  d'orchestrateur ; `saga_state` est un état agrégé, pas un coordinateur.
- **« Exactly-once ? »** Non : au moins une fois côté publication, plus des
  consommateurs idempotents (`processed_events` + gardes d'état terminal), ce qui
  donne un effet exactement-une-fois.
- **« Pourquoi pas de facturation événementielle en aval ? »** UC-08 est hors
  périmètre ; la facturation intervient en amont comme autorisation de paiement.

## Repli

Voir [demo-troubleshooting.md](demo-troubleshooting.md). Si Jaeger est vide,
montrer `trace_id`, `saga_id` et `correlation_id` dans la sortie audit de
`-Step Acceptance` et l'annoncer explicitement.
