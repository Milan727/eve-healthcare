from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.payments import router as payments_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.database import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions
    setup_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    await init_db()
    yield
    # Shutdown actions
    logger.info("Shutting down application and disposing database connection pool...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade backend service for diagnostic test bookings and simulated payments.\n\n"
        "### Features:\n"
        "- **JWT-based Authentication** (`/api/v1/auth`)\n"
        "- **Diagnostic Centres & Tests Management** (`/api/v1/centres`, `/api/v1/tests`)\n"
        "- **Booking Lifecycle** with status validation (`/api/v1/bookings`)\n"
        "- **Simulated Payment Gateway** (`/payments` or `/api/v1/payments`)\n"
        "- **Idempotent Webhook Engine** (`/payments/webhook/` or `/api/v1/payments/webhook/`)\n"
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global validation exception formatting
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({"field": field, "message": err.get("msg")})
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content={"detail": "Validation error", "errors": errors},
    )


# Health check endpoint
@app.get("/health", tags=["Health"])
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Also mount payments router at root to explicitly fulfill exact PDF paths (/payments/ and /payments/webhook/)
app.include_router(payments_router)
