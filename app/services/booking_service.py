import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.enums import BookingStatus
from app.models.models import Booking, CentreTest, DiagnosticCentre, DiagnosticTest, User
from app.schemas.booking import BookingCreate, BookingResponse


class BookingService:
    @staticmethod
    async def create_booking(
        db: AsyncSession, user: User, data: BookingCreate
    ) -> BookingResponse:
        logger.info(f"User {user.id} attempting to book test {data.test_id} at centre {data.centre_id}")

        # 1. Verify centre exists and is active
        centre = await db.get(DiagnosticCentre, data.centre_id)
        if not centre or not centre.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID '{data.centre_id}' is not available.",
            )

        # 2. Verify test exists and is active
        test = await db.get(DiagnosticTest, data.test_id)
        if not test or not test.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID '{data.test_id}' is not available.",
            )

        # 3. Verify centre-test availability and get price
        stmt = select(CentreTest).where(
            CentreTest.centre_id == data.centre_id,
            CentreTest.test_id == data.test_id,
            CentreTest.is_available.is_(True),
        )
        result = await db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The test '{test.name}' is not currently offered or available at '{centre.name}'.",
            )

        # 4. Create booking with snapshot amount and initial PENDING status
        booking = Booking(
            user_id=user.id,
            centre_id=data.centre_id,
            test_id=data.test_id,
            appointment_date_time=data.appointment_date_time,
            amount=float(mapping.price),
            status=BookingStatus.PENDING.value,
        )
        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        logger.info(f"Booking created: {booking.id} with status {booking.status}")

        return BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            centre_id=booking.centre_id,
            test_id=booking.test_id,
            appointment_date_time=booking.appointment_date_time,
            amount=float(booking.amount),
            status=BookingStatus(booking.status),
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            centre_name=centre.name,
            centre_location=centre.location,
            test_name=test.name,
        )

    @staticmethod
    async def get_booking_by_id(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User
    ) -> Booking:
        stmt = (
            select(Booking)
            .options(
                selectinload(Booking.centre),
                selectinload(Booking.test),
                selectinload(Booking.user),
            )
            .where(Booking.id == booking_id)
        )
        result = await db.execute(stmt)
        booking = result.scalar_one_or_none()

        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID '{booking_id}' not found.",
            )

        # Authorization check: only owner or admin can view
        if not current_user.is_admin and booking.user_id != current_user.id:
            logger.warning(
                f"Unauthorized access attempt: User {current_user.id} tried to view booking {booking_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this booking.",
            )

        return booking

    @staticmethod
    async def list_user_bookings(
        db: AsyncSession,
        current_user: User,
        status_filter: Optional[BookingStatus] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[BookingResponse], int]:
        stmt = (
            select(Booking)
            .options(selectinload(Booking.centre), selectinload(Booking.test))
        )

        if not current_user.is_admin:
            stmt = stmt.where(Booking.user_id == current_user.id)

        if status_filter:
            stmt = stmt.where(Booking.status == status_filter.value)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(Booking.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        bookings = list(result.scalars().all())

        response_items = [
            BookingResponse(
                id=b.id,
                user_id=b.user_id,
                centre_id=b.centre_id,
                test_id=b.test_id,
                appointment_date_time=b.appointment_date_time,
                amount=float(b.amount),
                status=BookingStatus(b.status),
                created_at=b.created_at,
                updated_at=b.updated_at,
                centre_name=b.centre.name if b.centre else None,
                centre_location=b.centre.location if b.centre else None,
                test_name=b.test.name if b.test else None,
            )
            for b in bookings
        ]
        return response_items, total

    @staticmethod
    async def cancel_booking(
        db: AsyncSession, booking_id: uuid.UUID, current_user: User
    ) -> BookingResponse:
        booking = await BookingService.get_booking_by_id(db, booking_id, current_user)

        if booking.status == BookingStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled.",
            )

        if booking.status == BookingStatus.FAILED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a booking that has already failed.",
            )

        booking.status = BookingStatus.CANCELLED.value
        await db.commit()
        await db.refresh(booking)

        logger.info(f"Booking {booking.id} cancelled by user {current_user.id}")

        return BookingResponse(
            id=booking.id,
            user_id=booking.user_id,
            centre_id=booking.centre_id,
            test_id=booking.test_id,
            appointment_date_time=booking.appointment_date_time,
            amount=float(booking.amount),
            status=BookingStatus(booking.status),
            created_at=booking.created_at,
            updated_at=booking.updated_at,
            centre_name=booking.centre.name if booking.centre else None,
            centre_location=booking.centre.location if booking.centre else None,
            test_name=booking.test.name if booking.test else None,
        )
