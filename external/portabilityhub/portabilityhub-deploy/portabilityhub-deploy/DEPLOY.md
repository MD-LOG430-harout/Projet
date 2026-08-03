# Portability Hub — Deploy on another machine

## Requirements

- Docker Engine 24+
- Docker Compose v2 (`docker compose`)
- Free ports: **8282**, **8291**, **8292**, **5433**

## Quick start

```bash
tar xzf portabilityhub-deploy.tar.gz
# or: unzip portabilityhub-deploy.zip
cd portabilityhub-deploy
docker compose up -d --build
```

Wait ~1–2 minutes for the first build, then open:

| Service | URL |
|---------|-----|
| Simulateur | http://localhost:8282/simulator/ |
| Hub API | http://localhost:8282/portability/... |
| Health | http://localhost:8282/actuator/health |
| BSS1 webhooks | http://localhost:8291/webhooks/portability |
| BSS2 webhooks | http://localhost:8292/webhooks/portability |

## Remote access (other PCs on the network)

If clients connect from another machine, edit `docker-compose.yml` and replace `localhost` with this server's IP or hostname:

```yaml
SIMULATOR_PUBLIC_BASE_URL: http://YOUR-SERVER:8282
HUB_PUBLIC_BASE_URL: http://YOUR-SERVER:8282
BSS1_GATEWAY_PUBLIC_URL: http://YOUR-SERVER:8291
BSS2_GATEWAY_PUBLIC_URL: http://YOUR-SERVER:8292
```

Then restart:

```bash
docker compose up -d --build
```

## Postman

Import from this folder:

- `docs/postman/portability-hub.postman_collection.json`
- `docs/postman/portability-hub.local.postman_environment.json`

Set `hubBaseUrl` to `http://YOUR-SERVER:8282` if not running locally.

## Useful commands

```bash
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v    # also deletes database volume
```

## What's included

```
portabilityhub-deploy/
├── docker-compose.yml
├── Dockerfile              # Hub backend
├── pom.xml
├── src/                    # Hub + simulateur
├── gateway/                # Hub Gateway (:8282)
├── bss-gateway/            # BSS Gateways (:8291, :8292)
└── docs/postman/           # Postman collection
```

JWT is disabled in this prototype (`WEBHOOK_JWT_ENABLED=false`).
