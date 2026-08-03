# Role 4 Demo Guide - Deploiement et implementation hexagonale

Use this during the oral defense. Your job is to defend deployment, development
view, ports/adapters, and the boundary between domain and infrastructure.

## My Role

I am responsible for:

- Section 7: Deployment view and development view
- 4+1: physical view and development view
- ports and adapters
- domain versus infrastructure boundaries
- Docker Compose topology and inter-service communication

My key idea:

> I defend how the architecture is packaged, deployed, and kept maintainable in
> code.

## My 60-90 Second Script

> The Phase 2 stack is deployed with Docker Compose. It contains the six
> CanTelcoX services, NGINX as API Gateway, MySQL, Redis, Kafka in KRaft mode,
> Prometheus, Grafana, OpenTelemetry Collector, Jaeger, and the supplied
> PortabilityHub components.
>
> The implementation follows a hexagonal style where possible. REST controllers,
> Kafka consumers, webhook handlers, persistence repositories, Outbox publishers,
> HLR/HSS adapters, and PortabilityHub adapters are infrastructure adapters.
> Business logic lives in application handlers and domain models, not directly
> inside framework routes.
>
> Services communicate synchronously only where appropriate: public REST, login,
> customer and catalogue validation, status queries, and supplied synchronous
> external APIs. Saga progress is asynchronous through Kafka and local Outbox
> tables.
>
> Deployment-wise, each service has its own container and database ownership.
> Kafka, MySQL, and observability components are explicit in Compose, with
> health checks and startup dependencies for a reproducible lab demonstration.

## If Time Is Short

> The system runs in Docker Compose with the six services, API Gateway, MySQL,
> Kafka, Redis, PortabilityHub, Prometheus, Grafana, OpenTelemetry, and Jaeger.
> The implementation keeps a hexagonal boundary: REST, Kafka, MySQL, HLR/HSS, and
> PortabilityHub are adapters, while domain decisions stay in application and
> domain code.

## Deployment Components

| Component | Role |
|---|---|
| `api-gateway` | NGINX entry point for `/v1` APIs |
| six services | business capabilities |
| `mysql` | owned service schemas, Outbox, processed events, audit |
| `kafka` | internal event transport |
| `redis` | catalogue/cache support |
| `portabilityhub-*` | supplied external portability system |
| `otel-collector` | trace collection |
| `jaeger` | trace visualization |
| `prometheus` | metrics scraping |
| `grafana` | dashboards |

## Hexagonal Boundaries

Inbound adapters:

- REST routes
- Kafka consumers
- PortabilityHub webhook endpoint

Outbound adapters:

- MySQL repositories
- Kafka producer / Outbox publisher
- HLR/HSS HTTP adapter
- PortabilityHub HTTP adapter
- payment gateway simulation

Core:

- domain models
- application commands/handlers
- state transitions
- invariants

## Commands To Show

Preflight:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Preflight
```

Observability links:

```powershell
powershell -ExecutionPolicy Bypass -File docs\demo\demo-commands.ps1 -Step Links -OpenDashboards
```

Docker status:

```powershell
docker compose -p cantelcox-phase2full ps
```

## If The Teacher Asks

Question: Where is the domain/infrastructure boundary?

Answer:

> Routes, Kafka, MySQL, and HTTP clients are adapters. They translate external
> inputs into application commands or domain events. The business decisions,
> like order terminal transitions or duplicate guards, belong in application and
> domain code.

Question: Why Docker Compose?

Answer:

> For the lab, Docker Compose gives a reproducible local environment with all
> services, Kafka, MySQL, PortabilityHub, and observability tools. It is enough
> for the course VM, but not a production high-availability topology.

Question: Is Kafka highly available here?

Answer:

> No. The lab uses a single Kafka broker with replication factor 1. That is
> reproducible for the course environment, but it is not fault tolerant.

Question: What is synchronous versus asynchronous?

Answer:

> Public API requests, authentication, validation, status queries, and supplied
> external REST APIs are synchronous. Saga propagation and audit events are
> asynchronous through Kafka.

Question: How do adapters protect the domain?

Answer:

> HLR/HSS and PortabilityHub expose external representations. The adapters map
> those representations into internal domain outcomes, so external details do
> not leak into the core model.

## Anchor Sentence

> My role is to show that the system is deployable and that infrastructure
> concerns stay at the edges through ports and adapters.
