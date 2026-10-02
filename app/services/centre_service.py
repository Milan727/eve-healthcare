import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.models.models import CentreTest, DiagnosticCentre, DiagnosticTest
from app.schemas.centre import CentreCreate, CentreDetailResponse, CentreTestAssign, CentreTestResponse
from app.schemas.test import TestCreate


class CentreService:
    @staticmethod
    async def create_centre(db: AsyncSession, data: CentreCreate) -> DiagnosticCentre:
        centre = DiagnosticCentre(
            name=data.name,
            location=data.location,
            contact_number=data.contact_number,
        )
        db.add(centre)
        await db.commit()
        await db.refresh(centre)
        logger.info(f"Diagnostic centre created: {centre.id} - {centre.name}")
        return centre

    @staticmethod
    async def get_centre(db: AsyncSession, centre_id: uuid.UUID) -> DiagnosticCentre:
        stmt = (
            select(DiagnosticCentre)
            .options(
                selectinload(DiagnosticCentre.centre_tests).selectinload(CentreTest.test)
            )
            .where(DiagnosticCentre.id == centre_id)
        )
        result = await db.execute(stmt)
        centre = result.scalar_one_or_none()
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID '{centre_id}' not found.",
            )
        return centre

    @staticmethod
    async def list_centres(
        db: AsyncSession,
        search: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[DiagnosticCentre], int]:
        stmt = select(DiagnosticCentre).where(DiagnosticCentre.is_active.is_(True))
        if search:
            stmt = stmt.where(DiagnosticCentre.name.ilike(f"%{search}%"))
        if location:
            stmt = stmt.where(DiagnosticCentre.location.ilike(f"%{location}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(DiagnosticCentre.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        centres = list(result.scalars().all())
        return centres, total

    @staticmethod
    async def create_test(db: AsyncSession, data: TestCreate) -> DiagnosticTest:
        test = DiagnosticTest(
            name=data.name,
            description=data.description,
            category=data.category,
        )
        db.add(test)
        await db.commit()
        await db.refresh(test)
        logger.info(f"Diagnostic test created: {test.id} - {test.name}")
        return test

    @staticmethod
    async def get_test(db: AsyncSession, test_id: uuid.UUID) -> DiagnosticTest:
        stmt = select(DiagnosticTest).where(DiagnosticTest.id == test_id)
        result = await db.execute(stmt)
        test = result.scalar_one_or_none()
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID '{test_id}' not found.",
            )
        return test

    @staticmethod
    async def list_tests(
        db: AsyncSession,
        search: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[DiagnosticTest], int]:
        stmt = select(DiagnosticTest).where(DiagnosticTest.is_active.is_(True))
        if search:
            stmt = stmt.where(DiagnosticTest.name.ilike(f"%{search}%"))
        if category:
            stmt = stmt.where(DiagnosticTest.category.ilike(f"%{category}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = stmt.order_by(DiagnosticTest.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        tests = list(result.scalars().all())
        return tests, total

    @staticmethod
    async def assign_test_to_centre(
        db: AsyncSession, centre_id: uuid.UUID, data: CentreTestAssign
    ) -> CentreTest:
        # Validate centre exists
        centre = await db.get(DiagnosticCentre, centre_id)
        if not centre:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic centre with ID '{centre_id}' not found.",
            )

        # Validate test exists
        test = await db.get(DiagnosticTest, data.test_id)
        if not test:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Diagnostic test with ID '{data.test_id}' not found.",
            )

        # Check if already mapped
        stmt = select(CentreTest).where(
            CentreTest.centre_id == centre_id, CentreTest.test_id == data.test_id
        )
        result = await db.execute(stmt)
        mapping = result.scalar_one_or_none()

        if mapping:
            mapping.price = data.price
            mapping.is_available = data.is_available
        else:
            mapping = CentreTest(
                centre_id=centre_id,
                test_id=data.test_id,
                price=data.price,
                is_available=data.is_available,
            )
            db.add(mapping)

        await db.commit()
        await db.refresh(mapping)
        logger.info(
            f"Assigned test {data.test_id} to centre {centre_id} with price {data.price}"
        )
        return mapping

    @staticmethod
    async def get_centre_details_with_tests(
        db: AsyncSession, centre_id: uuid.UUID
    ) -> CentreDetailResponse:
        centre = await CentreService.get_centre(db, centre_id)
        test_items = []
        for ct in centre.centre_tests:
            if ct.test and ct.test.is_active:
                test_items.append(
                    CentreTestResponse(
                        test_id=ct.test.id,
                        test_name=ct.test.name,
                        category=ct.test.category,
                        description=ct.test.description,
                        price=float(ct.price),
                        is_available=ct.is_available,
                    )
                )

        return CentreDetailResponse(
            id=centre.id,
            name=centre.name,
            location=centre.location,
            contact_number=centre.contact_number,
            is_active=centre.is_active,
            created_at=centre.created_at,
            tests=test_items,
        )
