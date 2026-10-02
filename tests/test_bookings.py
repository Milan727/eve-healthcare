from datetime import datetime, timedelta, timezone
import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_booking_success(
    client: AsyncClient, patient_user, sample_centre, sample_test, sample_centre_test
):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    response = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["amount"] == 120.00
    assert data["centre_name"] == sample_centre.name
    assert data["test_name"] == sample_test.name
    assert "id" in data


@pytest.mark.asyncio
async def test_create_booking_past_date_fails(
    client: AsyncClient, patient_user, sample_centre, sample_test, sample_centre_test
):
    past_time = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    response = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": past_time,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_booking_unoffered_test(
    client: AsyncClient, patient_user, sample_centre, admin_user
):
    # Create another test not assigned to sample_centre
    new_test_resp = await client.post(
        "/api/v1/tests/",
        headers=admin_user["headers"],
        json={"name": "MRI Brain", "category": "Radiology"},
    )
    unoffered_test_id = new_test_resp.json()["id"]

    future_time = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    response = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": unoffered_test_id,
            "appointment_date_time": future_time,
        },
    )
    assert response.status_code == 400
    assert "not currently offered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_booking_authorization_isolation(
    client: AsyncClient,
    patient_user,
    other_user,
    sample_centre,
    sample_test,
    sample_centre_test,
):
    # Patient creates booking
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create_resp = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    booking_id = create_resp.json()["id"]

    # Other user tries to access patient's booking
    forbidden_resp = await client.get(
        f"/api/v1/bookings/{booking_id}",
        headers=other_user["headers"],
    )
    assert forbidden_resp.status_code == 403
    assert "permission" in forbidden_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cancel_booking(
    client: AsyncClient, patient_user, sample_centre, sample_test, sample_centre_test
):
    future_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    create_resp = await client.post(
        "/api/v1/bookings/",
        headers=patient_user["headers"],
        json={
            "centre_id": str(sample_centre.id),
            "test_id": str(sample_test.id),
            "appointment_date_time": future_time,
        },
    )
    booking_id = create_resp.json()["id"]

    # Cancel booking
    cancel_resp = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=patient_user["headers"],
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Try cancelling again -> 400
    retry_cancel = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        headers=patient_user["headers"],
    )
    assert retry_cancel.status_code == 400
    assert "already cancelled" in retry_cancel.json()["detail"].lower()
