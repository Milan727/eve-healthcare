from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.models.models import Payment


@pytest.mark.asyncio
async def test_webhook_payment_success(
    client: AsyncClient, patient_user, sample_centre, sample_test, sample_centre_test
):
    # 1. Create a booking
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking_resp = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    booking_id = booking_resp.json()["id"]

    # 2. Receive webhook event from payment provider
    webhook_payload = {
        "event_id": "evt_test_001_success",
        "booking_id": booking_id,
        "status": "SUCCESS",
        "amount": 120.00,
    }
    wh_resp = await client.post("/payments/webhook/", json=webhook_payload)
    assert wh_resp.status_code == 200
    wh_data = wh_resp.json()
    assert wh_data["status"] == "PROCESSED"
    assert wh_data["booking_status"] == "CONFIRMED"

    # 3. Verify booking status is CONFIRMED
    get_resp = await client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=patient_user["headers"],
    )
    assert get_resp.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_webhook_strict_idempotency(
    client: AsyncClient,
    db_session,
    patient_user,
    sample_centre,
    sample_test,
    sample_centre_test,
):
    # 1. Create booking
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking_resp = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    booking_id = booking_resp.json()["id"]

    event_id = "evt_idempotent_unique_999"
    webhook_payload = {
        "event_id": event_id,
        "booking_id": booking_id,
        "status": "SUCCESS",
        "amount": 120.00,
    }

    # First delivery
    first_resp = await client.post("/payments/webhook/", json=webhook_payload)
    assert first_resp.status_code == 200
    assert first_resp.json()["status"] == "PROCESSED"

    # Count payments after first delivery
    count_stmt = select(func.count(Payment.id)).where(Payment.booking_id == uuid.UUID(booking_id))
    payment_count_1 = (await db_session.execute(count_stmt)).scalar()
    assert payment_count_1 == 1

    # Second delivery (identical event_id)
    second_resp = await client.post("/payments/webhook/", json=webhook_payload)
    assert second_resp.status_code == 200
    assert second_resp.json()["status"] == "DUPLICATE_IGNORED"
    assert "duplicate" in second_resp.json()["message"].lower()

    # Third delivery (identical event_id)
    third_resp = await client.post("/payments/webhook/", json=webhook_payload)
    assert third_resp.status_code == 200
    assert third_resp.json()["status"] == "DUPLICATE_IGNORED"

    # Count payments after duplicates: MUST STILL BE EXACTLY 1!
    payment_count_2 = (await db_session.execute(count_stmt)).scalar()
    assert payment_count_2 == 1


@pytest.mark.asyncio
async def test_webhook_does_not_corrupt_cancelled_booking(
    client: AsyncClient, patient_user, sample_centre, sample_test, sample_centre_test
):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking_resp = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    booking_id = booking_resp.json()["id"]

    # Cancel booking
    await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=patient_user["headers"],
    )

    # Deliver webhook
    wh_resp = await client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt_late_arrival_123",
            "booking_id": booking_id,
            "status": "SUCCESS",
            "amount": 120.00,
        },
    )
    assert wh_resp.status_code == 200
    assert wh_resp.json()["status"] == "IGNORED_CANCELLED"

    # Confirm booking remains CANCELLED
    get_resp = await client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=patient_user["headers"],
    )
    assert get_resp.json()["status"] == "CANCELLED"
