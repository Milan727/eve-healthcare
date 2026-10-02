from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import User
from app.schemas.auth import Token, UserLogin, UserResponse, UserSignup
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new patient/user with email, password, and profile details.",
)
async def signup(
    signup_data: UserSignup,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.signup(db, signup_data)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticates user credentials and returns a JWT Bearer access token.",
)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.authenticate(db, login_data)
    return AuthService.generate_token(user)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Returns the profile information of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user
