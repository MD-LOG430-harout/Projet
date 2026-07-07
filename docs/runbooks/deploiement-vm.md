# Runbook de deploiement VM - CanTelcoX Phase 1

Ce runbook couvre le deploiement reproductible de la pile CanTelcoX Phase 1 avec Docker Compose. Il correspond a l'annexe CI/CD, conteneurisation et exploitation du rapport LOG430.

La cible de deploiement Phase 1 est une VM Linux avec Docker Engine et Docker Compose. Aucun cloud manage, Kubernetes, registre prive ou service mesh n'est requis pour la remise.

## Reponse directe aux attentes 8.1, 8.2 et 8.3

### 8.1 - Conteneurisation

Le depot fournit un `docker-compose.yml` qui lance la stack Phase 1:

- six services Flask CanTelcoX;
- MySQL avec scripts d'initialisation et seed sous `infra/mysql/init`;
- Redis comme cache catalogue;
- NGINX comme API Gateway;
- Prometheus;
- Grafana;
- Swagger UI;
- Locust en profil optionnel `load-test`.

Chaque service applicatif possede un Dockerfile multi-stage sous `services/svc-*/Dockerfile`. Les six services Flask exposent `/health`, et Compose verifie ces endpoints par `healthcheck`. Le gateway expose aussi `/health` et possede son healthcheck Compose.

Commande de lancement sur environnement frais:

```bash
cp .env.example .env
docker compose up -d --build
bash scripts/wait-compose-health.sh 300
```

### 8.2 - CI

L'environnement CI choisi est GitHub Actions, avec runner `ubuntu-latest`, defini dans `.github/workflows/phase1-ci.yml`.

Le pipeline execute:

1. installation Python 3.12 et dependances;
2. lint rapide: `compileall` et `ruff` limite aux erreurs critiques;
3. validation des contrats: collection Postman JSON et `docker compose config`;
4. tests unitaires des six services;
5. build des images Docker multi-stage;
6. lancement Compose;
7. tests d'integration MySQL/adapters;
8. test E2E via l'API Gateway;
9. artefacts: rapports JUnit, configuration Compose resolue, `docker compose ps`, logs Docker.

Le job a un `timeout-minutes: 10` pour rester conforme a l'objectif de pipeline court et fail-fast. Pour la remise, cette CI est documentee meme si le correcteur ne l'execute pas.

### 8.3 - Job CD en VM

Dans le cadre de Phase 1, "en VM" est traite comme un environnement Docker propre similaire a une VM fraiche. Le deploiement principal est donc un script Compose reproductible:

```bash
bash scripts/deploy-vm.sh deploy
```

Ce script:

1. cree `.env` depuis `.env.example` si absent;
2. valide `docker compose config`;
3. construit les images;
4. lance la stack avec `docker compose up -d`;
5. attend les healthchecks;
6. fournit aussi `rollback`, `status` et `logs`.

Rollback:

```bash
bash scripts/deploy-vm.sh rollback
```

Equivalent Windows PowerShell local, si Bash/WSL n'est pas disponible:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action deploy
```

Rollback Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action rollback
```

Un job CD GitHub Actions manuel est aussi fourni dans `.github/workflows/deploy-vm.yml`. Il montre comment declencher un deploiement SSH vers une VM avec les secrets `VM_HOST`, `VM_USER` et `VM_SSH_KEY`. Le deploiement automatique a chaque merge sur `main` n'est pas active par defaut afin de ne pas deployer vers une VM inconnue ou non fournie; si une VM permanente et ses secrets etaient disponibles, le meme job pourrait etre branche sur `push` vers `main`.

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

Equivalent Windows PowerShell local, si Bash/WSL n'est pas disponible:

```powershell
Copy-Item .env.example .env
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/wait-compose-health.ps1 -TimeoutSeconds 300
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

Equivalent PowerShell local:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action deploy -DeployRef main
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action deploy -AppDir C:\cantelcox -DeployRef v1.0.0
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action deploy -HealthTimeoutSeconds 420
```

Le script execute:

1. creation de `.env` depuis `.env.example` si absent;
2. sauvegarde du commit courant dans `.deploy/previous_revision`;
3. `git fetch --all --prune` puis `git checkout $DEPLOY_REF`;
4. `docker compose config`;
5. `docker compose build`;
6. `docker compose up -d`;
7. attente des healthchecks avec `scripts/wait-compose-health.sh`.

## Job CD GitHub Actions vers la VM

La workflow `.github/workflows/deploy-vm.yml` prepare un job CD manuel vers une VM. Elle ne contient aucun detail reel de VM dans le depot; les valeurs sont fournies par secrets GitHub.

Secrets GitHub requis dans l'environnement `vm`:

| Secret | Description |
|---|---|
| `VM_HOST` | Adresse IP ou DNS de la VM |
| `VM_USER` | Utilisateur SSH sur la VM |
| `VM_SSH_KEY` | Cle privee SSH autorisee sur la VM |

Declenchement:

1. Aller dans GitHub Actions.
2. Ouvrir `Deploy VM`.
3. Cliquer `Run workflow`.
4. Choisir `action=deploy`, `deploy_ref=main`, `app_dir=/opt/cantelcox`.

La commande executee sur la VM est equivalente a:

```bash
APP_DIR=/opt/cantelcox DEPLOY_REF=main bash scripts/deploy-vm.sh deploy
```

Si le dossier `/opt/cantelcox` ne contient pas encore le depot, la workflow clone le depot GitHub avant de lancer le script.

## Rollback simple

Si un deploiement echoue ou si la demo doit revenir a l'etat precedent:

```bash
bash scripts/deploy-vm.sh rollback
```

Le rollback recharge le commit stocke dans `.deploy/previous_revision`, reconstruit les images, relance Compose et attend les healthchecks.

Le meme rollback peut etre declenche par la workflow `Deploy VM` avec `action=rollback`.

## Commandes d'exploitation

Etat des conteneurs:

```bash
bash scripts/deploy-vm.sh status
```

Journaux recents:

```bash
bash scripts/deploy-vm.sh logs
```

Equivalents Windows PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action status
powershell -ExecutionPolicy Bypass -File scripts\deploy-vm.ps1 -Action logs
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

Sur Windows PowerShell:

```powershell
docker compose down -v
docker compose up -d --build
powershell -ExecutionPolicy Bypass -File scripts/wait-compose-health.ps1 -TimeoutSeconds 300
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
- Capture de la workflow `Deploy VM` executee avec `action=deploy`.
- Capture de `bash scripts/deploy-vm.sh deploy` et, si possible, de `rollback`.
