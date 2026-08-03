import threading


class SimulatedPaymentGateway:
    def __init__(self, force_failure=False, force_refusal=False):
        self.force_failure = force_failure
        self.force_refusal = force_refusal
        self._authorizations = {}
        self._refunds = {}
        self._lock = threading.Lock()

    def charge(self, payment_request, trace_id=None):
        if self.force_failure:
            raise RuntimeError("simulated payment gateway unavailable")
        return {
            "gatewayTransactionId": f"sim-{payment_request['invoiceId']}",
            "status": "ACCEPTED",
        }

    def authorize(self, payment_request, traceparent=None):
        """Separate, idempotent saga authorization; UC-06 still uses charge()."""
        if self.force_failure:
            raise RuntimeError("simulated payment gateway unavailable")
        payment_id = payment_request["paymentId"]
        with self._lock:
            existing = self._authorizations.get(payment_id)
            if existing:
                return existing.copy()
            result = {
                "authorizationId": f"auth-{payment_id}",
                "status": "REFUSED" if self.force_refusal else "AUTHORIZED",
                "reasonCode": "DECLINED" if self.force_refusal else None,
            }
            self._authorizations[payment_id] = result
            return result.copy()

    def refund(self, payment_request, traceparent=None):
        if self.force_failure:
            raise RuntimeError("simulated payment gateway unavailable")
        payment_id = payment_request["paymentId"]
        with self._lock:
            authorization = self._authorizations.get(payment_id)
            if not authorization or authorization["status"] != "AUTHORIZED":
                raise RuntimeError("payment is not authorized")
            existing = self._refunds.get(payment_id)
            if existing:
                return existing.copy()
            result = {"refundId": f"refund-{payment_id}", "status": "REFUNDED"}
            self._refunds[payment_id] = result
            return result.copy()
