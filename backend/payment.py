import os
import random
import string
from typing import Dict

from backend.schemas import PaymentResponse


def simulate_payment(provider: str, amount_inr: int) -> PaymentResponse:
    reference_id = None
    status = "failed"
    metadata: Dict[str, str] = {}

    if provider.lower() == "stripe":
        reference_id = "pi_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=24))
        status = "succeeded"
        metadata = {"provider": "stripe", "mode": os.environ.get("PAYMENT_MODE", "test")}
    elif provider.lower() == "razorpay":
        reference_id = "rp_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=24))
        status = "created"
        metadata = {"provider": "razorpay", "mode": os.environ.get("PAYMENT_MODE", "test")}
    else:
        reference_id = "local_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        status = "succeeded"
        metadata = {"provider": "local", "mode": "mock"}

    return PaymentResponse(
        provider=provider,
        amount_inr=amount_inr,
        currency="INR",
        reference_id=reference_id,
        status=status,
        metadata=metadata,
    )
