import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.models import User
from app.schemas.common import PaginatedResponse
from app.schemas.test import TestCreate, TestResponse
from app.services.centre_service import CentreService

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.post(
    "/",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new diagnostic test",
    description="Registers a new diagnostic test type in the system (Admin only).",
)
async def create_test(
    test_data: TestCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await CentreService.create_test(db, test_data)


@router.get(
    "/",
    response_model=PaginatedResponse[TestResponse],
    summary="List diagnostic tests",
    description="Retrieves a paginated list of available diagnostic tests.",
)
async def list_tests(
    search: Optional[str] = Query(None, description="Search tests by name"),
    category: Optional[str] = Query(None, description="Filter tests by category"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
):
    tests, total = await CentreService.list_tests(
        db, search=search, category=category, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[TestResponse.model_validate(t) for t in tests],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{test_id}",
    response_model=TestResponse,
    summary="Get test details",
    description="Retrieves details of a specific diagnostic test by ID.",
)
async def get_test(
    test_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    test = await CentreService.get_test(db, test_id)
    return TestResponse.model_validate(test)
