import uuid

from services.shared.errors import ApiError
from services.shared.security import hash_secret

from app.domain.model.customer import Customer


class RegisterCustomer:
    def __init__(self, customer_repository, audit_client=None):
        self.customer_repository = customer_repository
        self.audit_client = audit_client

    def execute(self, payload, trace_id=None):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        display_name = (payload.get("displayName") or "").strip()
        legal_name = (payload.get("legalName") or "").strip()
        address = payload.get("address") or {}
        address_line1 = (address.get("line1") or "").strip()
        city = (address.get("city") or "").strip()
        province = (address.get("province") or "").strip().upper()
        postal_code = (address.get("postalCode") or "").strip().upper().replace(" ", "")
        identity_document = payload.get("identityDocument") or {}
        identity_document_type = (identity_document.get("type") or "").strip()
        identity_document_number = (identity_document.get("number") or "").strip()
        customer_type = payload.get("customerType") or "individual"

        if not email or "@" not in email:
            raise ApiError(400, "validation_error", "A valid email is required", {"field": "email"})
        if len(password) < 8:
            raise ApiError(400, "validation_error", "Password must contain at least 8 characters", {"field": "password"})
        if not display_name:
            raise ApiError(400, "validation_error", "displayName is required", {"field": "displayName"})
        if not legal_name:
            raise ApiError(400, "validation_error", "legalName is required", {"field": "legalName"})
        if not address_line1:
            raise ApiError(400, "validation_error", "address.line1 is required", {"field": "address.line1"})
        if not city:
            raise ApiError(400, "validation_error", "address.city is required", {"field": "address.city"})
        if province not in {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}:
            raise ApiError(400, "validation_error", "A valid Canadian province or territory is required", {"field": "address.province"})
        if len(postal_code) != 6:
            raise ApiError(400, "validation_error", "A valid Canadian postal code is required", {"field": "address.postalCode"})
        if identity_document_type not in {"driver_license", "passport", "provincial_id"}:
            raise ApiError(400, "validation_error", "A valid simulated identity document type is required", {"field": "identityDocument.type"})
        if len(identity_document_number) < 6:
            raise ApiError(400, "validation_error", "A simulated identity document number is required", {"field": "identityDocument.number"})
        if self.customer_repository.find_by_email(email):
            raise ApiError(409, "customer_exists", "A customer already exists for this email")

        customer = Customer(
            customer_id=str(uuid.uuid4()),
            email=email,
            display_name=display_name,
            legal_name=legal_name,
            address_line1=address_line1,
            city=city,
            province=province,
            postal_code=postal_code,
            identity_document_type=identity_document_type,
            identity_document_hash=hash_secret(identity_document_number),
            customer_type=customer_type,
            status="ACTIVE",
            identity_status="VERIFIED",
            risk_level="LOW",
        )
        self.customer_repository.create(customer)
        self.customer_repository.set_password_hash(customer.customer_id, hash_secret(password))
        self._audit("CUSTOMER_REGISTERED", customer.customer_id, "SUCCESS", trace_id)
        return customer

    def _audit(self, event_type, customer_id, result, trace_id):
        if not self.audit_client:
            return
        event = {
            "eventType": event_type,
            "actorId": customer_id,
            "customerId": customer_id,
            "resourceId": customer_id,
            "sourceService": "svc-clients-identite",
            "result": result,
            "metadata": {"identityStatus": "VERIFIED", "riskLevel": "LOW", "identityDocumentStoredAs": "hash"},
        }
        self.audit_client.record(event, trace_id=trace_id)
