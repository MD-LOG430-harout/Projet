# Schémas JSON — Événements Portabilité v1.3

Schémas **JSON Schema draft 2020-12** alignés sur [`../asyncapi/portability-hub.asyncapi.yaml`](../asyncapi/portability-hub.asyncapi.yaml) et [`../portability-hub-evenements.md`](../portability-hub-evenements.md).

## Composants partagés

| Fichier | Description |
|---------|-------------|
| [`EventNotification.envelope.json`](EventNotification.envelope.json) | Enveloppe TMF Event v4 (champs communs) |
| [`EventSourceRef.json`](EventSourceRef.json) | Source de l'événement |
| [`PortabilityOrderEventRef.json`](PortabilityOrderEventRef.json) | Snapshot ordre de portabilité |
| [`OutValidationResult.json`](OutValidationResult.json) | Résultat validation OUT |

## Événements (7 topics Kafka)

| Topic | Schéma | eventType |
|-------|--------|-----------|
| `portability.port-in-requested` | [`PortInRequestedEvent.json`](PortInRequestedEvent.json) | `PortInRequestedEvent` |
| `portability.out-validation-needed` | [`PortabilityOrderOutValidationNeededEvent.json`](PortabilityOrderOutValidationNeededEvent.json) | `PortabilityOrderOutValidationNeededEvent` |
| `portability.out-validated` | [`PortabilityOrderOutValidatedEvent.json`](PortabilityOrderOutValidatedEvent.json) | `PortabilityOrderOutValidatedEvent` |
| `portability.order-approved` | [`PortabilityOrderStateChangeEvent.order-approved.json`](PortabilityOrderStateChangeEvent.order-approved.json) | `PortabilityOrderStateChangeEvent` |
| `portability.order-rejected` | [`PortabilityOrderStateChangeEvent.order-rejected.json`](PortabilityOrderStateChangeEvent.order-rejected.json) | `PortabilityOrderStateChangeEvent` |
| `portability.port-completed` | [`PortabilityOrderStateChangeEvent.port-completed.json`](PortabilityOrderStateChangeEvent.port-completed.json) | `PortabilityOrderStateChangeEvent` |
| `portability.order-cancelled` | [`PortabilityOrderStateChangeEvent.order-cancelled.json`](PortabilityOrderStateChangeEvent.order-cancelled.json) | `PortabilityOrderStateChangeEvent` |

Chaque fichier d'événement inclut une section `examples` avec un payload complet.

## Références `$ref`

Les schémas d'événements référencent les composants partagés par chemin relatif (même répertoire). Valider depuis ce dossier :

```bash
# Exemple avec ajv-cli (si installé)
npx ajv validate -s PortInRequestedEvent.json -d examples/port-in-requested.json
```

## Identifiants clés

| Champ | Rôle |
|-------|------|
| `id` | Ressource Event TMF (`evt-hub-…`) — unique par notification |
| `eventId` | Occurrence métier (`PORT-EVT-…`) — unique par publication |
| `correlationId` | Fil du parcours — `orderId` après création Hub |
| `event.portabilityOrder.id` | Identifiant de l'ordre de portabilité |
