# Repository Guidelines

## Project Structure & Module Organization

This repository contains the CanTelcoX LOG430 service platform. Runtime services live under `services/`, with one folder per bounded context: `svc-clients-identite`, `svc-catalogue-offres`, `svc-commandes-activations`, `svc-lignes-services`, `svc-usage-facturation`, and `svc-conformite-audit`. Each service follows a hexagonal layout: `app/domain`, `app/application`, and `app/adapters`, plus local `tests/`.

Shared Python utilities are in `services/shared`. Cross-service tests are in `tests/unit`, `tests/integration`, `tests/e2e`, and `tests/load`. Event contracts are in `contracts/events`; API and architecture documentation are in `docs/`; Docker, MySQL, NGINX, Prometheus, Grafana, and OpenTelemetry configuration are in `infra/`. External supplied systems, including PortabilityHub, are under `external/`.

## Build, Test, and Development Commands

- `Copy-Item .env.example .env`: create local configuration on Windows PowerShell.
- `docker compose up -d --build`: build and start the full local stack.
- `powershell -ExecutionPolicy Bypass -File scripts\wait-compose-health.ps1 -TimeoutSeconds 300`: wait for services to become healthy.
- `python -m pytest -p no:cacheprovider tests/unit`: run repository unit tests.
- `python -m pytest -p no:cacheprovider tests/integration`: run integration tests.
- `python -m pytest -p no:cacheprovider tests/e2e`: validate gateway-level flows.
- `locust -f tests/load/locustfile.py --host=http://localhost:8080`: run load tests locally.

## Coding Style & Naming Conventions

Use Python 3.12, 4-space indentation, type hints where they clarify boundaries, and explicit dependency injection through application services or adapters. Keep business logic out of REST, Kafka, and persistence adapters. Follow existing `snake_case` module/function names and `PascalCase` domain classes. Use ASCII-only technical identifiers for event names, topics, schema files, and logs, for example `CommandePassee` and `commande-passee.v1`.

## Testing Guidelines

Use `pytest`. Place service-specific tests in `services/<service>/tests` and cross-service tests in `tests/<level>`. Name test files `test_*.py` and test functions `test_*`. For event-driven changes, cover success, duplicate delivery, failure or compensation paths, schema validation, and idempotent consumers.

## Commit & Pull Request Guidelines

Recent history uses short, lowercase, past-tense summaries such as `added demo` and `removed unused files`. Keep commits focused and describe the observable change. Pull requests should include a concise purpose, affected services/contracts, commands run, linked issue or course requirement when relevant, and screenshots or logs for API, observability, or UI/demo changes.

## Security & Configuration Tips

Do not commit real secrets, tokens, credentials, or personal data. Keep local values in `.env`; update `.env.example` only with safe placeholders. Avoid logging passwords, JWTs, raw identity data, or high-cardinality personal information in metrics labels.
