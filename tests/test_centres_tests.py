import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_create_centre(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/centres/",
        headers=admin_user["headers"],
        json={
            "name": "Metro Health Diagnostics",
            "location": "Downtown Central 42, Metro City",
            "contact_number": "+1-800-METRO",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Metro Health Diagnostics"
    assert data["location"] == "Downtown Central 42, Metro City"
    assert "id" in data


@pytest.mark.asyncio
async def test_patient_cannot_create_centre(client: AsyncClient, patient_user):
    response = await client.post(
        "/api/v1/centres/",
        headers=patient_user["headers"],
        json={
            "name": "Unauthorized Centre",
            "location": "Anywhere",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_create_test(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/v1/tests/",
        headers=admin_user["headers"],
        json={
            "name": "Lipid Profile",
            "description": "Measures total cholesterol, HDL, and LDL",
            "category": "Biochemistry",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Lipid Profile"
    assert data["category"] == "Biochemistry"


@pytest.mark.asyncio
async def test_assign_test_to_centre(
    client: AsyncClient, admin_user, sample_centre, sample_test
):
    response = await client.post(
        f"/api/v1/centres/{sample_centre.id}/tests",
        headers=admin_user["headers"],
        json={
            "test_id": str(sample_test.id),
            "price": 85.50,
            "is_available": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["test_id"] == str(sample_test.id)
    assert data["price"] == 85.50
    assert data["is_available"] is True


@pytest.mark.asyncio
async def test_get_centre_with_available_tests(
    client: AsyncClient, sample_centre, sample_test, sample_centre_test
):
    response = await client.get(f"/api/v1/centres/{sample_centre.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_centre.name
    assert len(data["tests"]) == 1
    assert data["tests"][0]["test_name"] == sample_test.name
    assert data["tests"][0]["price"] == 120.00


@pytest.mark.asyncio
async def test_list_centres_filter(client: AsyncClient, sample_centre):
    response = await client.get("/api/v1/centres/?location=New%20York")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert any(c["id"] == str(sample_centre.id) for c in data["items"])


@pytest.mark.asyncio
async def test_assign_test_invalid_centre(client: AsyncClient, admin_user, sample_test):
    random_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/centres/{random_id}/tests",
        headers=admin_user["headers"],
        json={
            "test_id": str(sample_test.id),
            "price": 50.00,
        },
    )
    assert response.status_code == 404
