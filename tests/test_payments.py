from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_simulated_payment_success(
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

    # 2. Simulate payment with SUCCESS
    pay_resp = await client.post(
        "/payments/",
        headers=patient_user["headers"],
        json={
            "booking_id": booking_id,
            "payment_method": "CREDIT_CARD",
            "simulate_status": "SUCCESS",
        },
    )
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["status"] == "SUCCESS"
    assert pay_data["booking_status"] == "CONFIRMED"
    assert pay_data["amount"] == 120.00
    assert "transaction_ref" in pay_data

    # 3. Verify booking status is now CONFIRMED
    get_booking_resp = await client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=patient_user["headers"],
    )
    assert get_booking_resp.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_simulated_payment_failed(
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

    # 2. Simulate payment with FAILED
    pay_resp = await client.post(
        "/payments/",
        headers=patient_user["headers"],
        json={
            "booking_id": booking_id,
            "simulate_status": "FAILED",
        },
    )
    assert pay_resp.status_code == 200
    pay_data = pay_resp.json()
    assert pay_data["status"] == "FAILED"
    assert pay_data["booking_status"] == "FAILED"

    # 3. Verify booking is now FAILED
    get_booking_resp = await client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=patient_user["headers"],
    )
    assert get_booking_resp.json()["status"] == "FAILED"


@pytest.mark.asyncio
async def test_cannot_pay_already_confirmed_booking(
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

    # First payment succeeds
    await client.post(
        "/payments/",
        headers=patient_user["headers"],
        json={"booking_id": booking_id, "simulate_status": "SUCCESS"},
    )

    # Second payment attempt must be rejected
    second_pay_resp = await client.post(
        "/payments/",
        headers=patient_user["headers"],
        json={"booking_id": booking_id, "simulate_status": "SUCCESS"},
    )
    assert second_pay_resp.status_code == 400
    assert "already been paid" in second_pay_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unauthorized_payment_rejected(
    client: AsyncClient, patient_user, other_user, sample_centre, sample_test, sample_centre_test
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

    # Other user tries to pay
    unauth_pay = await client.post(
        "/payments/",
        headers=other_user["headers"],
        json={"booking_id": booking_id, "simulate_status": "SUCCESS"},
    )
    assert unauth_pay.status_code == 403
