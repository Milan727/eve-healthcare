import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_signup_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "newpatient@example.com",
            "password": "strongpassword123",
            "full_name": "Alice Wonderland",
            "phone": "9876543210",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newpatient@example.com"
    assert data["full_name"] == "Alice Wonderland"
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_user_signup_duplicate_email(client: AsyncClient, patient_user):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "patient@example.com",  # Already registered in fixture
            "password": "anotherpassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_user_signup_validation_error(client: AsyncClient):
    # Short password and invalid email
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "not-an-email",
            "password": "123",  # less than 6 chars
            "full_name": "",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_user_login_success(client: AsyncClient, patient_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_user_login_wrong_password(client: AsyncClient, patient_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "patient@example.com",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, patient_user):
    response = await client.get("/api/v1/auth/me", headers=patient_user["headers"])
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "patient@example.com"
    assert data["full_name"] == "John Doe"


@pytest.mark.asyncio
async def test_get_profile_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
