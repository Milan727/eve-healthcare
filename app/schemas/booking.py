import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, field_validator

from app.models.enums import BookingStatus


class BookingCreate(BaseModel):
    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_date_time: datetime

    @field_validator("appointment_date_time")
    @classmethod
    def validate_future_date(cls, v: datetime) -> datetime:
        # Standardize timezone comparison
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            # Assume UTC if naive
            v = v.replace(tzinfo=timezone.utc)
        if v <= now:
            raise ValueError("Appointment date and time must be set in the future.")
        return v


class BookingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    centre_id: uuid.UUID
    test_id: uuid.UUID
    appointment_date_time: datetime
    amount: float
    status: BookingStatus
    created_at: datetime
    updated_at: datetime

    # Additional contextual fields for client convenience
    centre_name: Optional[str] = None
    centre_location: Optional[str] = None
    test_name: Optional[str] = None

    model_config = {"from_attributes": True}


class BookingCancel(BaseModel):
    reason: Optional[str] = Field(None, max_length=255)
