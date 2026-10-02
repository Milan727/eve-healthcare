from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.auth import Token, UserLogin, UserSignup


class AuthService:
    @staticmethod
    async def signup(db: AsyncSession, data: UserSignup) -> User:
        logger.info(f"Attempting to register user: {data.email}")
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logger.warning(f"Registration failed: Email {data.email} already exists")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email address already exists.",
            )

        new_user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            is_admin=False,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"User created successfully: {new_user.id} ({new_user.email})")
        return new_user

    @staticmethod
    async def authenticate(db: AsyncSession, data: UserLogin) -> User:
        logger.info(f"Login attempt for: {data.email}")
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not verify_password(data.password, user.hashed_password):
            logger.warning(f"Failed authentication for: {data.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    @staticmethod
    def generate_token(user: User) -> Token:
        access_token = create_access_token(subject=str(user.id))
        return Token(access_token=access_token, token_type="bearer")
