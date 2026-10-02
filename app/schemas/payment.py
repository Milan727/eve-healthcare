import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.enums import BookingStatus, PaymentStatus


class PaymentRequest(BaseModel):
    booking_id: uuid.UUID
    payment_method: str = Field("CARD", max_length=50, description="Payment method used (e.g. CARD, UPI, NETBANKING)")
    simulate_status: Optional[PaymentStatus] = Field(
        PaymentStatus.SUCCESS,
        description="Target outcome to simulate: SUCCESS or FAILED. Defaults to SUCCESS.",
    )


class PaymentResponse(BaseModel):
    id: uuid.UUID
    booking_id: uuid.UUID
    amount: float
    status: PaymentStatus
    transaction_ref: str
    payment_method: str
    booking_status: BookingStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookPayload(BaseModel):
    event_id: str = Field(..., min_length=1, max_length=100, description="Unique idempotency identifier from payment gateway")
    booking_id: uuid.UUID
    status: PaymentStatus = Field(..., description="Payment outcome: SUCCESS or FAILED")
    amount: Optional[float] = Field(None, gt=0, description="Amount paid")
    payment_method: Optional[str] = Field("GATEWAY_WEBHOOK", max_length=50)


class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: str
    booking_id: Optional[uuid.UUID] = None
    booking_status: Optional[BookingStatus] = None
