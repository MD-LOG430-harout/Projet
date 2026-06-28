from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Offer:
    offer_id: str
    name: str
    monthly_price: Decimal
    data_gb: int
    status: str
