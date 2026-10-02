import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db
from app.core.security import create_access_token, hash_password
from app.database import Base
from app.main import app
from app.models.models import CentreTest, DiagnosticCentre, DiagnosticTest, User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def patient_user(db_session: AsyncSession):
    user = User(
        email="patient@example.com",
        hashed_password=hash_password("password123"),
        full_name="John Doe",
        phone="1234567890",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return {"user": user, "token": token, "headers": headers}


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession):
    user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
        full_name="Jane Smith",
        phone="0987654321",
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return {"user": user, "token": token, "headers": headers}


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    user = User(
        email="admin@evehealthcare.com",
        hashed_password=hash_password("adminpassword123"),
        full_name="System Admin",
        phone="5555555555",
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return {"user": user, "token": token, "headers": headers}


@pytest_asyncio.fixture
async def sample_centre(db_session: AsyncSession):
    centre = DiagnosticCentre(
        name="Apollo Diagnostic Centre",
        location="5th Avenue, New York, NY",
        contact_number="+1-212-555-0199",
        is_active=True,
    )
    db_session.add(centre)
    await db_session.commit()
    await db_session.refresh(centre)
    return centre


@pytest_asyncio.fixture
async def sample_test(db_session: AsyncSession):
    test = DiagnosticTest(
        name="Complete Blood Count (CBC)",
        description="Measures cells making up your blood",
        category="Hematology",
        is_active=True,
    )
    db_session.add(test)
    await db_session.commit()
    await db_session.refresh(test)
    return test


@pytest_asyncio.fixture
async def sample_centre_test(
    db_session: AsyncSession, sample_centre: DiagnosticCentre, sample_test: DiagnosticTest
):
    mapping = CentreTest(
        centre_id=sample_centre.id,
        test_id=sample_test.id,
        price=120.00,
        is_available=True,
    )
    db_session.add(mapping)
    await db_session.commit()
    await db_session.refresh(mapping)
    return mapping
