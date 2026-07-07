# Runbook de deploiement VM - CanTelcoX Phase 1

Ce runbook couvre le deploiement reproductible de la pile CanTelcoX Phase 1 avec Docker Compose. Il correspond a l'annexe CI/CD, conteneurisation et exploitation du rapport LOG430.

## Prerequis VM

- Docker Engine avec le plugin Docker Compose v2.
- Git.
- Ports disponibles: `8080`, `8081`, `9090`, `3000`, `3306`, `6379`.
- Acces au depot Git ou au dossier remis.

Verification rapide:

```bash
docker --version
docker compose version
git --version
```

## Premier demarrage reproductible

Depuis la racine du depot:

```bash
cp .env.example .env
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
docker compose ps
```

Resultat attendu:

- `mysql`, `redis`, les six services Flask et `api-gateway` sont `healthy`.
- `mysql-bootstrap` est termine avec code `0`.
- Swagger UI est disponible sur `http://localhost:8081`.
- Prometheus est disponible sur `http://localhost:9090`.
- Grafana est disponible sur `http://localhost:3000`.
- L'API Gateway repond sur `http://localhost:8080/health`.

Validation:

```bash
curl -i http://localhost:8080/health
python -m pytest -p no:cacheprovider tests/e2e
```

## Deploiement en une commande

Le script CD local utilise Git et Docker Compose. Il enregistre le commit courant avant de deploiement pour permettre un rollback simple.

```bash
bash scripts/deploy-vm.sh deploy
```

Variables utiles:

```bash
DEPLOY_REF=main bash scripts/deploy-vm.sh deploy
APP_DIR=/opt/cantelcox DEPLOY_REF=v1.0.0 bash scripts/deploy-vm.sh deploy
HEALTH_TIMEOUT_SECONDS=420 bash scripts/deploy-vm.sh deploy
```

Le script execute:

1. creation de `.env` depuis `.env.example` si absent;
2. sauvegarde du commit courant dans `.deploy/previous_revision`;
3. `git fetch --all --prune` puis `git checkout $DEPLOY_REF`;
4. `docker compose config`;
5. `docker compose build`;
6. `docker compose up -d`;
7. attente des healthchecks avec `scripts/wait-compose-health.sh`.

## Rollback simple

Si un deploiement echoue ou si la demo doit revenir a l'etat precedent:

```bash
bash scripts/deploy-vm.sh rollback
```

Le rollback recharge le commit stocke dans `.deploy/previous_revision`, reconstruit les images, relance Compose et attend les healthchecks.

## Commandes d'exploitation

Etat des conteneurs:

```bash
bash scripts/deploy-vm.sh status
```

Journaux recents:

```bash
bash scripts/deploy-vm.sh logs
```

Arret sans perte de volumes:

```bash
docker compose down
```

Reinitialisation complete de demo:

```bash
docker compose down -v
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
```

## CI attendue

La workflow `.github/workflows/phase1-ci.yml` est limitee a 10 minutes et execute:

1. installation des dependances Python epinglees;
2. lint rapide avec `compileall` et `ruff` cible sur les erreurs critiques;
3. validation JSON Postman et `docker compose config`;
4. tests unitaires des six services;
5. build des images Docker multi-stage;
6. demarrage de la pile Compose;
7. tests d'integration MySQL/adapters;
8. test E2E officiel via l'API Gateway;
9. publication des artefacts JUnit, config Compose et logs Docker.

Badge README:

```markdown
[![Phase 1 CI](https://github.com/<org>/<repo>/actions/workflows/phase1-ci.yml/badge.svg)](https://github.com/<org>/<repo>/actions/workflows/phase1-ci.yml)
```

Remplacer `<org>/<repo>` par le chemin GitHub final si le depot est publie.

## Evidence a capturer pour le rapport

- Capture de `docker compose ps` apres `wait-compose-health.sh`.
- Capture de `http://localhost:8080/health`.
- Capture Swagger UI.
- Capture Grafana Golden Signals.
- Capture du run GitHub Actions avec artefacts.
- Capture de `bash scripts/deploy-vm.sh deploy` et, si possible, de `rollback`.
