class SimulatedPaymentGateway:
    def __init__(self, force_failure=False):
        self.force_failure = force_failure

    def charge(self, payment_request, trace_id=None):
        if self.force_failure:
            raise RuntimeError("simulated payment gateway unavailable")
        return {
            "gatewayTransactionId": f"sim-{payment_request['invoiceId']}",
            "status": "ACCEPTED",
        }
