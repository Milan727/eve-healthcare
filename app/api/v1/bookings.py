import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.enums import BookingStatus
from app.models.models import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.schemas.common import PaginatedResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a diagnostic test",
    description="Creates a new diagnostic test booking for the authenticated user in PENDING state.",
)
async def create_booking(
    booking_data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.create_booking(db, current_user, booking_data)


@router.get(
    "/",
    response_model=PaginatedResponse[BookingResponse],
    summary="List bookings",
    description="Lists all bookings for the authenticated user (Admins can view all bookings).",
)
async def list_bookings(
    status_filter: Optional[BookingStatus] = Query(
        None, alias="status", description="Filter bookings by status (PENDING, CONFIRMED, FAILED, CANCELLED)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = await BookingService.list_user_bookings(
        db, current_user, status_filter=status_filter, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking details",
    description="Retrieves details of a specific booking. Users can only access their own bookings.",
)
async def get_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = await BookingService.get_booking_by_id(db, booking_id, current_user)
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


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
    description="Cancels an existing PENDING or CONFIRMED booking. Cannot cancel already failed/cancelled bookings.",
)
async def cancel_booking(
    booking_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await BookingService.cancel_booking(db, booking_id, current_user)
