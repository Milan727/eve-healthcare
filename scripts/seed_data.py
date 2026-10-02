import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.logging import logger, setup_logging
from app.core.security import hash_password
from app.database import AsyncSessionLocal, init_db
from app.models.models import CentreTest, DiagnosticCentre, DiagnosticTest, User


async def seed():
    setup_logging()
    await init_db()

    async with AsyncSessionLocal() as session:
        # 1. Create Admin & Patient Users
        admin_email = "admin@evehealthcare.com"
        patient_email = "patient@evehealthcare.com"

        admin = (
            await session.execute(select(User).where(User.email == admin_email))
        ).scalar_one_or_none()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=hash_password("AdminPass123!"),
                full_name="System Administrator",
                phone="+1-800-555-0100",
                is_admin=True,
            )
            session.add(admin)
            logger.info("Admin user created: admin@evehealthcare.com / AdminPass123!")

        patient = (
            await session.execute(select(User).where(User.email == patient_email))
        ).scalar_one_or_none()
        if not patient:
            patient = User(
                email=patient_email,
                hashed_password=hash_password("PatientPass123!"),
                full_name="John Doe",
                phone="+1-555-019-2834",
                is_admin=False,
            )
            session.add(patient)
            logger.info("Sample patient created: patient@evehealthcare.com / PatientPass123!")

        # 2. Create Diagnostic Centres
        centres_data = [
            {
                "name": "Apollo Diagnostics Central",
                "location": "120 Park Ave, New York, NY",
                "contact_number": "+1-212-555-0111",
            },
            {
                "name": "Mayo Diagnostic Clinic",
                "location": "200 First St SW, Rochester, MN",
                "contact_number": "+1-507-555-0122",
            },
            {
                "name": "CityHealth Diagnostic Centre",
                "location": "450 Sutter St, San Francisco, CA",
                "contact_number": "+1-415-555-0133",
            },
        ]

        centre_entities = {}
        for c in centres_data:
            existing = (
                await session.execute(
                    select(DiagnosticCentre).where(DiagnosticCentre.name == c["name"])
                )
            ).scalar_one_or_none()
            if not existing:
                existing = DiagnosticCentre(**c, is_active=True)
                session.add(existing)
                await session.flush()
                logger.info(f"Created centre: {c['name']}")
            centre_entities[c["name"]] = existing

        # 3. Create Diagnostic Tests
        tests_data = [
            {
                "name": "Complete Blood Count (CBC)",
                "category": "Hematology",
                "description": "Evaluates overall health and detects a variety of disorders including anemia and leukemia.",
            },
            {
                "name": "Lipid Profile Panel",
                "category": "Biochemistry",
                "description": "Measures total cholesterol, LDL, HDL, and triglycerides to assess cardiovascular risk.",
            },
            {
                "name": "Digital Chest X-Ray (PA View)",
                "category": "Radiology",
                "description": "High-resolution digital radiographic image of the lungs, heart, and chest wall.",
            },
            {
                "name": "HbA1c Glycated Hemoglobin",
                "category": "Endocrinology",
                "description": "Average blood glucose level over the past two to three months for diabetes monitoring.",
            },
            {
                "name": "Thyroid Stimulating Hormone (TSH)",
                "category": "Endocrinology",
                "description": "Screening test for thyroid disorders including hypothyroidism and hyperthyroidism.",
            },
        ]

        test_entities = {}
        for t in tests_data:
            existing = (
                await session.execute(
                    select(DiagnosticTest).where(DiagnosticTest.name == t["name"])
                )
            ).scalar_one_or_none()
            if not existing:
                existing = DiagnosticTest(**t, is_active=True)
                session.add(existing)
                await session.flush()
                logger.info(f"Created test: {t['name']}")
            test_entities[t["name"]] = existing

        # 4. Map tests to centres with centre-specific prices
        mappings = [
            ("Apollo Diagnostics Central", "Complete Blood Count (CBC)", 45.00),
            ("Apollo Diagnostics Central", "Lipid Profile Panel", 65.00),
            ("Apollo Diagnostics Central", "Digital Chest X-Ray (PA View)", 125.00),
            ("Mayo Diagnostic Clinic", "Complete Blood Count (CBC)", 50.00),
            ("Mayo Diagnostic Clinic", "HbA1c Glycated Hemoglobin", 40.00),
            ("Mayo Diagnostic Clinic", "Thyroid Stimulating Hormone (TSH)", 55.00),
            ("CityHealth Diagnostic Centre", "Lipid Profile Panel", 60.00),
            ("CityHealth Diagnostic Centre", "Digital Chest X-Ray (PA View)", 115.00),
            ("CityHealth Diagnostic Centre", "HbA1c Glycated Hemoglobin", 38.00),
        ]

        for centre_name, test_name, price in mappings:
            c = centre_entities[centre_name]
            t = test_entities[test_name]
            existing_mapping = (
                await session.execute(
                    select(CentreTest).where(
                        CentreTest.centre_id == c.id, CentreTest.test_id == t.id
                    )
                )
            ).scalar_one_or_none()
            if not existing_mapping:
                mapping = CentreTest(
                    centre_id=c.id,
                    test_id=t.id,
                    price=price,
                    is_available=True,
                )
                session.add(mapping)
                logger.info(f"Mapped {test_name} to {centre_name} at ${price}")

        await session.commit()
        logger.info("Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
