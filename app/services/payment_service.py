import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.enums import BookingStatus, PaymentStatus
from app.models.models import Booking, Payment, User
from app.schemas.payment import PaymentRequest, PaymentResponse


class PaymentService:
    @staticmethod
    async def process_simulated_payment(
        db: AsyncSession, user: User, request: PaymentRequest
    ) -> PaymentResponse:
        logger.info(
            f"Processing payment request for booking {request.booking_id} by user {user.id}"
        )

        # 1. Fetch booking
        booking = await db.get(Booking, request.booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID '{request.booking_id}' not found.",
            )

        # 2. Authorization check: must be owner or admin
        if not user.is_admin and booking.user_id != user.id:
            logger.warning(
                f"Unauthorized payment attempt: User {user.id} tried to pay for booking {request.booking_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to pay for this booking.",
            )

        # 3. Status checks
        if booking.status == BookingStatus.CONFIRMED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking has already been paid and confirmed.",
            )

        if booking.status == BookingStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot process payment for a cancelled booking.",
            )

        # 4. Generate transaction reference and record payment
        tx_ref = f"txn_mock_{uuid.uuid4().hex[:12]}"
        simulated_status = request.simulate_status or PaymentStatus.SUCCESS

        payment = Payment(
            booking_id=booking.id,
            amount=booking.amount,
            status=simulated_status.value,
            payment_method=request.payment_method,
            transaction_ref=tx_ref,
        )
        db.add(payment)

        # 5. Atomically update booking status
        if simulated_status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED.value
        else:
            booking.status = BookingStatus.FAILED.value

        booking.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(payment)
        await db.refresh(booking)

        logger.info(
            f"Payment {payment.id} processed: Status={payment.status}, "
            f"Booking {booking.id} updated to {booking.status}"
        )

        return PaymentResponse(
            id=payment.id,
            booking_id=payment.booking_id,
            amount=float(payment.amount),
            status=PaymentStatus(payment.status),
            transaction_ref=payment.transaction_ref,
            payment_method=payment.payment_method,
            booking_status=BookingStatus(booking.status),
            created_at=payment.created_at,
        )
