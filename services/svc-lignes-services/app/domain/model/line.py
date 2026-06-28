from dataclasses import dataclass


@dataclass(frozen=True)
class Line:
    line_id: str
    customer_id: str
    offer_id: str
    msisdn: str
    sim_type: str
    sim_identifier: str
    imsi: str
    supi: str
    status: str
    hlr_status: str
    failure_reason: str | None = None
