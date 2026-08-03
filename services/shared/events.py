from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4


EVENT_TOPICS = MappingProxyType(
    {
        "CommandePassee": "commande-passee.v1",
        "PaiementAutorise": "paiement-autorise.v1",
        "PaiementRefuse": "paiement-refuse.v1",
        "PaiementRembourse": "paiement-rembourse.v1",
        "LigneActivee": "ligne-activee.v1",
        "ActivationEchouee": "activation-echouee.v1",
        "CommandeConfirmee": "commande-confirmee.v1",
        "CommandeAnnulee": "commande-annulee.v1",
        "PortabiliteDemandee": "portabilite-demandee.v1",
        "NumeroPorte": "numero-porte.v1",
        "PortabiliteEchouee": "portabilite-echouee.v1",
    }
)

EVENT_PRODUCERS = MappingProxyType(
    {
        "CommandePassee": "svc-commandes-activations",
        "PaiementAutorise": "svc-usage-facturation",
        "PaiementRefuse": "svc-usage-facturation",
        "PaiementRembourse": "svc-usage-facturation",
        "LigneActivee": "svc-lignes-services",
        "ActivationEchouee": "svc-lignes-services",
        "CommandeConfirmee": "svc-commandes-activations",
        "CommandeAnnulee": "svc-commandes-activations",
        "PortabiliteDemandee": "svc-lignes-services",
        "NumeroPorte": "svc-lignes-services",
        "PortabiliteEchouee": "svc-lignes-services",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EventEnvelope:
    eventId: str
    eventType: str
    eventVersion: int
    occurredAt: str
    aggregateId: str
    aggregateType: str
    sagaId: str | None
    traceId: str
    correlationId: str
    causationId: str | None
    payload: Mapping[str, Any]

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        aggregate_id: str,
        aggregate_type: str,
        payload: Mapping[str, Any],
        trace_id: str,
        correlation_id: str,
        saga_id: str,
        causation_id: str | None = None,
        event_id: str | None = None,
        occurred_at: str | None = None,
    ) -> "EventEnvelope":
        if event_type not in EVENT_TOPICS:
            raise ValueError(f"Unsupported event type: {event_type}")
        if not aggregate_id or not aggregate_type or not trace_id or not correlation_id or not saga_id:
            raise ValueError("aggregate, trace, and correlation identifiers are required")
        candidate_event_id = event_id or str(uuid4())
        UUID(candidate_event_id)
        UUID(saga_id)
        if causation_id:
            UUID(causation_id)
        envelope = cls(
            eventId=candidate_event_id,
            eventType=event_type,
            eventVersion=1,
            occurredAt=occurred_at or _utc_now(),
            aggregateId=aggregate_id,
            aggregateType=aggregate_type,
            sagaId=saga_id,
            traceId=trace_id,
            correlationId=correlation_id,
            causationId=causation_id,
            payload=MappingProxyType(dict(payload)),
        )
        from services.shared.schema_validation import validate_event

        validate_event(envelope.to_dict())
        return envelope

    @property
    def topic(self) -> str:
        return EVENT_TOPICS[self.eventType]

    @property
    def kafka_key(self) -> str:
        return self.aggregateId

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventId": self.eventId,
            "eventType": self.eventType,
            "eventVersion": self.eventVersion,
            "occurredAt": self.occurredAt,
            "aggregateId": self.aggregateId,
            "aggregateType": self.aggregateType,
            "sagaId": self.sagaId,
            "traceId": self.traceId,
            "correlationId": self.correlationId,
            "causationId": self.causationId,
            "payload": dict(self.payload),
        }
