# CanTelcoX - Projet LOG430 Phase 1

[![Phase 1 CI](https://github.com/MD-LOG430-harout/Projet/actions/workflows/phase1-ci.yml/badge.svg)](https://github.com/MD-LOG430-harout/Projet/actions/workflows/phase1-ci.yml)

CanTelcoX est un projet LOG430 d'architecture logicielle. Il modelise une plateforme BSS pour un operateur mobile canadien fictif, avec une architecture basee sur des services, une API Gateway, des APIs REST versionnees, de l'observabilite, de l'idempotence, de l'audit append-only et un deploiement Docker Compose reproductible.

La Phase 1 est evaluee sur le livrable remis et la presentation du travail. La soutenance orale est reportee a la Phase 2.

## Correction rapide

Pour corriger ou tester rapidement le projet a partir du zip, commencer ici:

1. Lire ce `README.md`.
2. Lire le runbook: [docs/runbooks/deploiement-vm.md](docs/runbooks/deploiement-vm.md).
3. Lancer la stack Docker Compose.
4. Verifier `http://localhost:8080/health`.
5. Ouvrir Swagger UI sur `http://localhost:8081`.
6. Importer la collection Postman: [docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json](docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json).
7. Consulter les diagrammes officiels epingles dans la section [Diagrammes d'architecture](#diagrammes-darchitecture).

### Commandes macOS / Linux / Git Bash

```bash
cp .env.example .env
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
curl -i http://localhost:8080/health
python -m pytest -p no:cacheprovider tests/e2e
python -m pytest -p no:cacheprovider tests/integration
```

### Commandes Windows PowerShell

```powershell
Copy-Item .env.example .env
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts\wait-compose-health.ps1 -TimeoutSeconds 300
Invoke-WebRequest -Uri http://localhost:8080/health
python -m pytest -p no:cacheprovider tests/e2e
python -m pytest -p no:cacheprovider tests/integration
```

Prerequis: Docker Compose v2, Python 3.12 pour executer les tests hors Docker, et les ports `8080`, `8081`, `9090`, `3000`, `3306` et `6379` disponibles.

## Perimetre implemente en Phase 1

Les cas d'utilisation retenus et implementes sont:

| UC | Statut Phase 1 |
|---|---|
| UC-01 - Inscription & verification d'identite | Implemente dans `svc-clients-identite`, avec verification simulee et audit |
| UC-02 - Authentification & MFA | Implemente dans `svc-clients-identite`, avec OTP de demonstration et session `dev-session-*` |
| UC-03 - Activation d'une ligne | Implemente via `svc-commandes-activations`, `svc-lignes-services`, `svc-catalogue-offres`, adapter HLR/free5GC ou mock, et audit |
| UC-05 - Prise de commande | Implemente avec validation client/offre, idempotence, persistance et audit |
| UC-06 - Paiement de facture | Implemente dans `svc-usage-facturation`, avec passerelle de paiement simulee et exactly-once pratique |

Les limites documentees sont:

- UC-04 consultation d'usage detaillee: hors perimetre d'implementation Phase 1.
- UC-07 detection de fraude complete: limitee aux controles de risque necessaires aux flux retenus.
- UC-08 cycle mensuel de facturation: hors perimetre d'implementation Phase 1.
- OAuth2/OIDC/JWT complet: non implemente; la Phase 1 utilise une session de demonstration `dev-session-*` validee par introspection via la Gateway.

## Services

| Service | Responsabilite |
|---|---|
| `svc-clients-identite` | clients, inscription, authentification, MFA, risque simple |
| `svc-catalogue-offres` | catalogue d'offres, cache Redis sur `GET /v1/offers` |
| `svc-commandes-activations` | commandes, activations, idempotence, orchestration |
| `svc-lignes-services` | lignes, MSISDN, SIM/eSIM, adapter HLR/free5GC ou mock |
| `svc-usage-facturation` | factures, paiements, exactly-once pratique |
| `svc-conformite-audit` | audit append-only et recherche par `TraceId` |
| `api-gateway` | NGINX, routage `/v1`, introspection auth, propagation des headers, load balancing |

## URLs utiles apres demarrage

| Element | URL |
|---|---|
| API Gateway | `http://localhost:8080` |
| Health Gateway | `http://localhost:8080/health` |
| Swagger UI | `http://localhost:8081` |
| Prometheus | `http://localhost:9090` |
| Grafana | `http://localhost:3000` |
| Locust optionnel | `http://localhost:8089` |

Identifiants Grafana de demonstration par defaut: `admin` / `admin`, sauf modification dans `.env`.

## API et demo Postman

Le contrat OpenAPI principal est ici:

- [docs/api/openapi.yaml](docs/api/openapi.yaml)

La collection Postman officielle est ici:

- [docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json](docs/api/postman/CanTelcoX-Phase1-Gateway.postman_collection.json)

Configurer Postman avec:

```text
baseUrl = http://localhost:8080
```

Parcours officiel recommande:

1. UC-01 - inscription client.
2. UC-02 - login puis verification MFA.
3. Consultation des offres.
4. UC-05 - creation de commande avec `Idempotency-Key`.
5. Replay de commande pour prouver l'idempotence.
6. UC-03 - activation de ligne avec `Idempotency-Key`.
7. Consultation de ligne.
8. UC-06 - consultation/paiement de facture.
9. Recherche des evenements d'audit par `TraceId`.

Toutes les requetes officielles doivent passer par l'API Gateway `http://localhost:8080`. Les appels directs aux services sont reserves a la comparaison direct vs Gateway.

## Diagrammes d'architecture

Les diagrammes PlantUML officiels de la Phase 1 sont regroupes dans [docs/architecture/diagrams](docs/architecture/diagrams). Ils sont epingles ici pour faciliter la correction.

### Contexte et DDD

- [Contexte metier - CanTelcoX](docs/architecture/diagrams/context-business-cantelcox.puml)
- [Contexte systeme - CanTelcoX](docs/architecture/diagrams/context-system-cantelcox.puml)
- [Carte des contextes DDD - CanTelcoX](docs/architecture/diagrams/context-map-ddd-cantelcox.puml)

### Blocs de construction

- [Niveau 1 - decomposition en services](docs/architecture/diagrams/building-blocks-level1-cantelcox.puml)
- [Niveau 2 - structure hexagonale de svc-commandes-activations](docs/architecture/diagrams/building-blocks-level2-commandes-activations.puml)

### Scenarios d'execution

- [Scenario E2E Phase 1 via Gateway](docs/architecture/diagrams/sequence-e2e-phase1-gateway-flow.puml)
- [UC-01 - inscription](docs/architecture/diagrams/sequence-uc01-registration.puml)
- [UC-02 - authentification et MFA](docs/architecture/diagrams/sequence-uc02-auth-mfa.puml)
- [UC-03 - activation](docs/architecture/diagrams/sequence-uc03-activation.puml)
- [UC-05 - commande](docs/architecture/diagrams/sequence-uc05-order.puml)
- [UC-06 - paiement de facture](docs/architecture/diagrams/sequence-uc06-payment.puml)
- [Idempotence de commande](docs/architecture/diagrams/sequence-idempotency-order.puml)
- [Exactly-once pratique du paiement](docs/architecture/diagrams/sequence-exactly-once-payment.puml)

### Deploiement

- [Topologie Docker Compose](docs/architecture/diagrams/deployment-docker-compose-cantelcox.puml)

### Persistance / Annexe B

- [Vue globale de persistance](docs/architecture/diagrams/persistence-er-global.puml)
- [Clients & Identite](docs/architecture/diagrams/persistence-er-clients-identite.puml)
- [Catalogue & Offres](docs/architecture/diagrams/persistence-er-catalogue-offres.puml)
- [Commandes & Activations](docs/architecture/diagrams/persistence-er-commandes-activations.puml)
- [Lignes & Services](docs/architecture/diagrams/persistence-er-lignes-services.puml)
- [Usage / Facturation](docs/architecture/diagrams/persistence-er-usage-facturation.puml)
- [Conformite & Audit](docs/architecture/diagrams/persistence-er-conformite-audit.puml)

## Decisions d'architecture

Les ADR sont disponibles dans [docs/adr](docs/adr):

- [ADR-001 - Service-Based Architecture and Bounded Contexts](docs/adr/ADR-001-service-style-and-boundaries.md)
- [ADR-002 - Persistence, Idempotency, Exactly-Once Safeguards, and Audit](docs/adr/ADR-002-persistence-idempotency-audit.md)
- [ADR-003 - API Versioning, Normalized Errors, and Observability](docs/adr/ADR-003-api-errors-versioning-observability.md)
- [ADR-004 - free5GC as the UC-03 Network Simulator Adapter Target](docs/adr/ADR-004-free5gc-network-adapter.md)

## Deploiement et exploitation

Le runbook principal est:

- [docs/runbooks/deploiement-vm.md](docs/runbooks/deploiement-vm.md)

Commandes principales:

```bash
cp .env.example .env
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
docker compose ps
```

Deploiement local en une commande:

```bash
bash scripts/deploy-vm.sh deploy
```

Rollback:

```bash
bash scripts/deploy-vm.sh rollback
```

Equivalent Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action deploy
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action rollback
```

## Tests

Tests unitaires des services:

```bash
python -m pytest -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

Preuve actuelle du rapport: `52 passed` pour les tests unitaires des six services.

Tests d'integration:

```bash
python -m pytest -p no:cacheprovider tests/integration
```

Tests E2E via Gateway:

```bash
python -m pytest -p no:cacheprovider tests/e2e
```

Couverture du domaine critique:

La commande suivante exige le plugin `pytest-cov`. Si `pytest` retourne `unrecognized arguments: --cov`, installer d'abord `pytest-cov` dans l'environnement Python local ou utiliser la preuve de couverture fournie dans le rapport.

```bash
python -m pip install pytest-cov
```

```bash
python -m pytest --cov=services/svc-clients-identite/app/application --cov=services/svc-clients-identite/app/domain --cov=services/svc-catalogue-offres/app/application --cov=services/svc-catalogue-offres/app/domain --cov=services/svc-lignes-services/app/application --cov=services/svc-lignes-services/app/domain --cov=services/svc-commandes-activations/app/application --cov=services/svc-commandes-activations/app/domain --cov=services/svc-usage-facturation/app/application --cov=services/svc-usage-facturation/app/domain --cov=services/svc-conformite-audit/app/application --cov=services/svc-conformite-audit/app/domain --cov-report=term-missing --cov-report=html:docs/evidence/coverage/htmlcov -p no:cacheprovider services/svc-clients-identite/tests services/svc-conformite-audit/tests services/svc-catalogue-offres/tests services/svc-lignes-services/tests services/svc-commandes-activations/tests services/svc-usage-facturation/tests
```

## Charge, cache et observabilite

Lancer Locust en mode interactif:

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8080
```

Lancer Locust via Docker Compose:

```bash
docker compose --profile load-test up locust
```

Les preuves de charge et de NFR sont conservees dans:

- [docs/evidence/load](docs/evidence/load)
- [docs/architecture/load-balancing-cache-evidence.md](docs/architecture/load-balancing-cache-evidence.md)

Les 4 Golden Signals sont observes avec Prometheus et Grafana:

- latence P95/P99;
- trafic / RPS;
- erreurs 4xx/5xx;
- saturation CPU/RAM ou processus selon le dashboard disponible.

Le cache Redis est applique au catalogue, principalement sur:

```text
GET /v1/offers
```

La reponse expose l'en-tete `X-Cache` avec `MISS`, `HIT` ou `BYPASS`.

## CI/CD

La CI GitHub Actions est definie dans:

- [.github/workflows/phase1-ci.yml](.github/workflows/phase1-ci.yml)

Elle execute notamment:

1. installation Python;
2. lint rapide avec `compileall` et `ruff`;
3. validation de la collection Postman et de `docker compose config`;
4. tests unitaires;
5. build Docker;
6. demarrage Compose;
7. tests d'integration;
8. tests E2E via Gateway;
9. capture des logs et publication des artefacts.

Le workflow CD manuel vers VM est defini dans:

- [.github/workflows/deploy-vm.yml](.github/workflows/deploy-vm.yml)

Il s'appuie sur:

- [scripts/deploy-vm.sh](scripts/deploy-vm.sh)
- [scripts/deploy-vm.ps1](scripts/deploy-vm.ps1)

## Structure principale du depot

```text
.
|-- docker-compose.yml
|-- .env.example
|-- docs/
|   |-- adr/
|   |-- api/
|   |-- architecture/
|   |-- evidence/
|   `-- runbooks/
|-- infra/
|   |-- grafana/
|   |-- mysql/
|   |-- nginx/
|   `-- prometheus/
|-- scripts/
|-- services/
|   |-- shared/
|   |-- svc-clients-identite/
|   |-- svc-catalogue-offres/
|   |-- svc-commandes-activations/
|   |-- svc-lignes-services/
|   |-- svc-usage-facturation/
|   `-- svc-conformite-audit/
`-- tests/
    |-- e2e/
    |-- integration/
    `-- load/
```

## Notes free5GC

Par defaut, `HLR_ENABLED=false` dans `.env.example`, donc UC-03 utilise un adapter HLR mocke reproductible. Pour utiliser le simulateur free5GC fourni, consulter:

- [docs/runbooks/free5gc-simulator.md](docs/runbooks/free5gc-simulator.md)
- [docs/adr/ADR-004-free5gc-network-adapter.md](docs/adr/ADR-004-free5gc-network-adapter.md)

Le simulateur free5GC est une integration optionnelle pour rapprocher UC-03 d'un flux telecom reel. Il n'est pas requis pour lancer la demo Phase 1 avec Docker Compose.
