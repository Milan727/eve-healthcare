import json
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.enums import BookingStatus, PaymentStatus, WebhookEventStatus
from app.models.models import Booking, Payment, WebhookEvent
from app.schemas.payment import WebhookPayload, WebhookResponse


class WebhookService:
    @staticmethod
    async def process_webhook(
        db: AsyncSession, payload: WebhookPayload
    ) -> WebhookResponse:
        logger.info(
            f"Webhook received: event_id={payload.event_id}, booking_id={payload.booking_id}, status={payload.status}"
        )

        # 1. Idempotency Check: Check if event_id has already been processed
        stmt = select(WebhookEvent).where(WebhookEvent.event_id == payload.event_id)
        result = await db.execute(stmt)
        existing_event = result.scalar_one_or_none()

        if existing_event:
            logger.info(
                f"Idempotency hit: Duplicate event {payload.event_id} received. Ignoring processing."
            )
            booking = None
            if existing_event.booking_id:
                booking = await db.get(Booking, existing_event.booking_id)

            return WebhookResponse(
                status="DUPLICATE_IGNORED",
                message="Duplicate webhook event received; safely ignored to ensure idempotency.",
                event_id=payload.event_id,
                booking_id=payload.booking_id,
                booking_status=BookingStatus(booking.status) if booking else None,
            )

        # 2. Fetch related booking
        booking = await db.get(Booking, payload.booking_id)
        if not booking:
            logger.error(
                f"Webhook error: Booking {payload.booking_id} not found for event {payload.event_id}"
            )
            # Record failed event for audit trail
            failed_event = WebhookEvent(
                event_id=payload.event_id,
                booking_id=payload.booking_id,
                event_type="payment.updated",
                payload=json.dumps(payload.model_dump(mode="json")),
                status=WebhookEventStatus.FAILED.value,
            )
            db.add(failed_event)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID '{payload.booking_id}' not found.",
            )

        # 3. Handle state machine transitions safely
        if booking.status == BookingStatus.CANCELLED.value:
            logger.warning(
                f"Webhook warning: Booking {booking.id} was already CANCELLED. Not changing state."
            )
            event = WebhookEvent(
                event_id=payload.event_id,
                booking_id=booking.id,
                event_type="payment.updated",
                payload=json.dumps(payload.model_dump(mode="json")),
                status="IGNORED_CANCELLED",
            )
            db.add(event)
            await db.commit()
            return WebhookResponse(
                status="IGNORED_CANCELLED",
                message="Booking was previously cancelled; status remains CANCELLED.",
                event_id=payload.event_id,
                booking_id=booking.id,
                booking_status=BookingStatus.CANCELLED,
            )

        try:
            # 4. Create Payment Record
            payment_amount = payload.amount if payload.amount is not None else float(booking.amount)
            payment = Payment(
                booking_id=booking.id,
                amount=payment_amount,
                status=payload.status.value,
                payment_method=payload.payment_method or "GATEWAY_WEBHOOK",
                transaction_ref=f"wh_txn_{payload.event_id}",
            )
            db.add(payment)

            # 5. Update Booking Status
            if payload.status == PaymentStatus.SUCCESS:
                booking.status = BookingStatus.CONFIRMED.value
            else:
                booking.status = BookingStatus.FAILED.value

            booking.updated_at = datetime.now(timezone.utc)

            # 6. Record Webhook Event for idempotency
            webhook_event = WebhookEvent(
                event_id=payload.event_id,
                booking_id=booking.id,
                event_type="payment.updated",
                payload=json.dumps(payload.model_dump(mode="json")),
                status=WebhookEventStatus.PROCESSED.value,
            )
            db.add(webhook_event)

            # Commit all operations atomically
            await db.commit()
            await db.refresh(booking)

            logger.info(
                f"Webhook processed successfully for booking {booking.id}: Status is now {booking.status}"
            )

            return WebhookResponse(
                status="PROCESSED",
                message=f"Webhook event processed successfully. Booking is now {booking.status}.",
                event_id=payload.event_id,
                booking_id=booking.id,
                booking_status=BookingStatus(booking.status),
            )

        except IntegrityError:
            # Handles concurrent duplicate webhooks arriving at the exact same millisecond
            await db.rollback()
            logger.info(
                f"Concurrent webhook collision on event_id {payload.event_id}. Rolling back safely."
            )
            # Re-fetch current booking status
            fresh_booking = await db.get(Booking, payload.booking_id)
            return WebhookResponse(
                status="DUPLICATE_IGNORED",
                message="Concurrent duplicate webhook event detected and safely resolved.",
                event_id=payload.event_id,
                booking_id=payload.booking_id,
                booking_status=BookingStatus(fresh_booking.status) if fresh_booking else None,
            )
