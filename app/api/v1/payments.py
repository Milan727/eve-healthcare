from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import User
from app.schemas.payment import (
    PaymentRequest,
    PaymentResponse,
    WebhookPayload,
    WebhookResponse,
)
from app.services.payment_service import PaymentService
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/",
    response_model=PaymentResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate payment for a booking",
    description=(
        "Simulates a direct payment attempt for a booking. "
        "Outcome can be specified as SUCCESS or FAILED. "
        "Atomically updates booking state to CONFIRMED or FAILED."
    ),
)
async def process_payment(
    payment_data: PaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await PaymentService.process_simulated_payment(db, current_user, payment_data)


@router.post(
    "/webhook/",
    response_model=WebhookResponse,
    status_code=status.HTTP_200_OK,
    summary="Payment provider webhook endpoint",
    description=(
        "Asynchronous webhook from payment gateway notifying payment status update. "
        "Fully IDEMPOTENT: repeated deliveries of the same event_id will not result "
        "in duplicate payments or corrupted booking states."
    ),
)
async def payment_webhook(
    webhook_data: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    return await WebhookService.process_webhook(db, webhook_data)
