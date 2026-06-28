import uuid

from services.shared.errors import ApiError

from app.domain.model.line import Line


class ActivateLine:
    def __init__(self, line_repository, hlr_adapter):
        self.line_repository = line_repository
        self.hlr_adapter = hlr_adapter

    def execute(self, payload, trace_id=None):
        customer_id = payload.get("customerId")
        offer_id = payload.get("offerId")
        sim_type = (payload.get("simType") or "").upper()
        msisdn = payload.get("msisdn") or self._generate_msisdn()

        if not customer_id:
            raise ApiError(400, "validation_error", "customerId is required", {"field": "customerId"})
        if not offer_id:
            raise ApiError(400, "validation_error", "offerId is required", {"field": "offerId"})
        if sim_type not in {"SIM", "ESIM"}:
            raise ApiError(400, "validation_error", "simType must be SIM or ESIM", {"field": "simType"})
        if self.line_repository.find_by_msisdn(msisdn):
            raise ApiError(409, "msisdn_unavailable", "MSISDN is already assigned", {"msisdn": msisdn})

        line_id = str(uuid.uuid4())
        imsi = self._generate_imsi()
        line = Line(
            line_id=line_id,
            customer_id=customer_id,
            offer_id=offer_id,
            msisdn=msisdn,
            sim_type=sim_type,
            sim_identifier=self._generate_sim_identifier(sim_type),
            imsi=imsi,
            supi=f"imsi-{imsi}",
            status="PENDING",
            hlr_status="PENDING",
        )
        self.line_repository.create(line)

        try:
            provisioned = self.hlr_adapter.provision(line, trace_id=trace_id)
        except Exception as exc:
            self.line_repository.mark_failed(line_id, str(exc))
            raise ApiError(503, "hlr_provisioning_failed", "HLR/free5GC provisioning failed", {"reason": str(exc)})

        if not provisioned:
            self.line_repository.mark_failed(line_id, "adapter returned false")
            raise ApiError(503, "hlr_provisioning_failed", "HLR/free5GC provisioning failed")

        self.line_repository.mark_active(line_id)
        return self.line_repository.find_by_id(line_id)

    def _generate_msisdn(self):
        return "1438" + str(uuid.uuid4().int)[0:7]

    def _generate_imsi(self):
        return "20893" + str(uuid.uuid4().int)[0:10]

    def _generate_sim_identifier(self, sim_type):
        prefix = "EID" if sim_type == "ESIM" else "ICCID"
        return f"{prefix}-{uuid.uuid4().hex[:18].upper()}"
