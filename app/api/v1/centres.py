import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.models import User
from app.schemas.centre import (
    CentreCreate,
    CentreDetailResponse,
    CentreResponse,
    CentreTestAssign,
    CentreTestResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.centre_service import CentreService

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


@router.post(
    "/",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new diagnostic centre",
    description="Registers a new diagnostic centre in the system (Admin only).",
)
async def create_centre(
    centre_data: CentreCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return await CentreService.create_centre(db, centre_data)


@router.get(
    "/",
    response_model=PaginatedResponse[CentreResponse],
    summary="List diagnostic centres",
    description="Retrieves a paginated list of diagnostic centres with optional search and location filters.",
)
async def list_centres(
    search: Optional[str] = Query(None, description="Search centres by name"),
    location: Optional[str] = Query(None, description="Filter centres by location / city"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),
):
    centres, total = await CentreService.list_centres(
        db, search=search, location=location, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[CentreResponse.model_validate(c) for c in centres],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{centre_id}",
    response_model=CentreDetailResponse,
    summary="Get centre details with available tests and prices",
    description="Retrieves centre details including all diagnostic tests offered and their respective prices.",
)
async def get_centre(
    centre_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await CentreService.get_centre_details_with_tests(db, centre_id)


@router.post(
    "/{centre_id}/tests",
    response_model=CentreTestResponse,
    status_code=status.HTTP_200_OK,
    summary="Assign or update a test at a centre with price",
    description="Configures pricing and availability of a diagnostic test at a centre (Admin only).",
)
async def assign_test_to_centre(
    centre_id: uuid.UUID,
    assign_data: CentreTestAssign,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    mapping = await CentreService.assign_test_to_centre(db, centre_id, assign_data)
    test = await CentreService.get_test(db, mapping.test_id)
    return CentreTestResponse(
        test_id=test.id,
        test_name=test.name,
        category=test.category,
        description=test.description,
        price=float(mapping.price),
        is_available=mapping.is_available,
    )
