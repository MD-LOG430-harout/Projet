from dataclasses import dataclass


@dataclass(frozen=True)
class Customer:
    customer_id: str
    email: str
    display_name: str
    legal_name: str
    address_line1: str
    city: str
    province: str
    postal_code: str
    identity_document_type: str
    identity_document_hash: str
    customer_type: str
    status: str
    identity_status: str
    risk_level: str
