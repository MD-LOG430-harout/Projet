# Architecture Diagrams

PlantUML diagrams for the Arc42 / 4+1 architecture views and Annexe B persistence evidence.

Use the VS Code PlantUML extension to preview or export:

Context and DDD:

- `context-business-cantelcox.puml`
- `context-system-cantelcox.puml`
- `context-map-ddd-cantelcox.puml`

Building blocks:

- `building-blocks-level1-cantelcox.puml`
- `building-blocks-level2-commandes-activations.puml`

Deployment:

- `deployment-docker-compose-cantelcox.puml`

Persistence diagrams:

- `persistence-er-global.puml`
- `persistence-er-clients-identite.puml`
- `persistence-er-conformite-audit.puml`
- `persistence-er-catalogue-offres.puml`
- `persistence-er-lignes-services.puml`
- `persistence-er-commandes-activations.puml`
- `persistence-er-usage-facturation.puml`

Sequence diagrams:

- `sequence-e2e-phase1-gateway-flow.puml`
- `sequence-idempotency-order.puml`
- `sequence-exactly-once-payment.puml`
- `sequence-uc01-registration.puml`
- `sequence-uc02-auth-mfa.puml`
- `sequence-uc03-activation.puml`
- `sequence-uc05-order.puml`
- `sequence-uc06-payment.puml`

These diagrams reflect the SQL scripts under `infra/mysql/init/*.sql`.

Cross-service identifiers such as `customer_id`, `offer_id`, `line_id`, and `trace_id` are logical references, not physical foreign keys between service-owned schemas.
