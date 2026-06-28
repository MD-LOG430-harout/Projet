from services.shared.errors import ApiError


class ListInvoices:
    def __init__(self, repository, customer_client, audit_client=None):
        self.repository = repository
        self.customer_client = customer_client
        self.audit_client = audit_client

    def execute(self, customer_id, trace_id=None):
        if not customer_id:
            raise ApiError(400, "validation_error", "customerId is required", {"field": "customerId"})
        self.customer_client.get_customer(customer_id, trace_id=trace_id)
        invoices = [_invoice_public(row) for row in self.repository.list_invoices_by_customer(customer_id)]
        self._audit("INVOICE_CONSULTED", customer_id, customer_id, "SUCCESS", trace_id, {"scope": "customer"})
        return {"customerId": customer_id, "invoices": invoices}

    def _audit(self, event_type, actor_id, resource_id, result, trace_id, metadata=None):
        if self.audit_client:
            self.audit_client.record(_audit_event(event_type, actor_id, actor_id, resource_id, result, metadata), trace_id=trace_id)


class GetInvoice:
    def __init__(self, repository, audit_client=None):
        self.repository = repository
        self.audit_client = audit_client

    def execute(self, invoice_id, trace_id=None):
        invoice = self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ApiError(404, "invoice_not_found", "Invoice not found", {"invoiceId": invoice_id})
        self._audit("INVOICE_CONSULTED", invoice["customer_id"], invoice_id, "SUCCESS", trace_id, {"scope": "invoice"})
        return _invoice_public(invoice)

    def _audit(self, event_type, actor_id, resource_id, result, trace_id, metadata=None):
        if self.audit_client:
            self.audit_client.record(_audit_event(event_type, actor_id, actor_id, resource_id, result, metadata), trace_id=trace_id)


def _invoice_public(row):
    return {
        "invoiceId": row["invoice_id"],
        "customerId": row["customer_id"],
        "billingPeriod": row["billing_period"],
        "amountDue": float(row["amount_due"]),
        "currency": row["currency"],
        "status": row["status"],
        "dueDate": row["due_date"].isoformat() if hasattr(row["due_date"], "isoformat") else row["due_date"],
        "createdAt": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
    }


def _audit_event(event_type, actor_id, customer_id, resource_id, result, metadata=None):
    return {
        "eventType": event_type,
        "actorId": actor_id,
        "customerId": customer_id,
        "resourceId": resource_id,
        "sourceService": "svc-usage-facturation",
        "result": result,
        "metadata": metadata or {},
    }
