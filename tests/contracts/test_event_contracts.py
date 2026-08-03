import json
from pathlib import Path
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from services.shared.events import EVENT_PRODUCERS, EVENT_TOPICS, EventEnvelope


ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = ROOT / "contracts" / "events"
NOW = "2026-08-02T12:00:00Z"

PAYLOADS = {
    "CommandePassee": {"idCommande": "cmd-1", "idClient": "cli-1", "idOffre": "offre-1", "montant": 55.0, "devise": "CAD"},
    "PaiementAutorise": {"idPaiement": "pay-1", "idCommande": "cmd-1", "montant": 55.0, "devise": "CAD", "authorizationId": "auth-1", "authorizedAt": NOW},
    "PaiementRefuse": {"idPaiement": "pay-1", "idCommande": "cmd-1", "reasonCode": "INSUFFICIENT_FUNDS", "reasonMessage": "refused", "refusedAt": NOW},
    "PaiementRembourse": {"idPaiement": "pay-1", "idCommande": "cmd-1", "refundId": "refund-1", "montant": 55.0, "refundedAt": NOW},
    "LigneActivee": {"idLigne": "line-1", "idCommande": "cmd-1", "msisdn": "14385551234", "activationMode": "NEW", "hlrReference": "hlr-1", "activatedAt": NOW},
    "ActivationEchouee": {"idLigne": "line-1", "idCommande": "cmd-1", "reasonCode": "HLR_FAILURE", "reasonMessage": "failed", "attempts": 3, "failedAt": NOW},
    "CommandeConfirmee": {"idCommande": "cmd-1", "idClient": "cli-1", "idLigne": "line-1", "confirmedAt": NOW},
    "CommandeAnnulee": {"idCommande": "cmd-1", "reasonCode": "PAYMENT_REFUSED", "reasonMessage": "refused", "cancelledAt": NOW, "compensationRequired": False},
    "PortabiliteDemandee": {"idCommande": "cmd-1", "idLigne": "line-1", "portId": "port-1", "msisdn": "14385551234", "currentOperator": "BSS2", "requestedAt": NOW},
    "NumeroPorte": {"idCommande": "cmd-1", "idLigne": "line-1", "portId": "port-1", "msisdn": "14385551234", "portedAt": NOW, "previousOperator": "BSS2"},
    "PortabiliteEchouee": {"idCommande": "cmd-1", "idLigne": "line-1", "portId": "port-1", "msisdn": "14385551234", "reasonCode": "HUB_REJECTED", "reasonMessage": "rejected", "failedAt": NOW, "hubStatus": "rejected"},
}


def _document(event_type):
    first = event_type == "CommandePassee"
    aggregate_type = "Commande" if event_type.startswith("Commande") else "Paiement" if event_type.startswith("Paiement") else "Ligne" if event_type in {"LigneActivee", "ActivationEchouee"} else "Portabilite"
    return EventEnvelope.create(
        event_type=event_type,
        aggregate_id="cmd-1" if aggregate_type == "Commande" else "aggregate-1",
        aggregate_type=aggregate_type,
        payload=PAYLOADS[event_type],
        trace_id="0123456789abcdef0123456789abcdef",
        correlation_id="cmd-1",
        saga_id=str(uuid4()),
        causation_id=None if first else str(uuid4()),
        occurred_at=NOW,
    ).to_dict()


def test_exactly_eleven_ascii_event_contracts_and_unique_topics():
    assert set(EVENT_TOPICS) == set(PAYLOADS)
    assert set(EVENT_PRODUCERS) == set(PAYLOADS)
    assert len(EVENT_TOPICS) == 11
    assert len(set(EVENT_TOPICS.values())) == 11
    assert all(name.isascii() and topic.isascii() for name, topic in EVENT_TOPICS.items())


def test_all_schemas_use_the_same_required_envelope_fields():
    expected = {
        "eventId", "eventType", "eventVersion", "occurredAt", "aggregateId",
        "aggregateType", "sagaId", "traceId", "correlationId", "causationId", "payload",
    }
    for event_type in PAYLOADS:
        schema = json.loads((CONTRACTS / event_type / "v1.json").read_text(encoding="utf-8"))
        assert set(schema["required"]) == expected


@pytest.mark.parametrize("event_type", sorted(PAYLOADS))
def test_sample_event_validates_against_its_v1_schema(event_type):
    path = CONTRACTS / event_type / "v1.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(_document(event_type))


def test_schema_rejects_wrong_event_type():
    schema = json.loads((CONTRACTS / "CommandePassee" / "v1.json").read_text(encoding="utf-8"))
    document = _document("CommandePassee")
    document["eventType"] = "CommandePassée"
    with pytest.raises(Exception):
        Draft202012Validator(schema).validate(document)
