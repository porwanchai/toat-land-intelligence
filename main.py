import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config import settings
from app.database import get_db, engine
from app.middleware.rate_limiter import rate_limiter

# Import Routers
from app.routers import auth, zoning, plots, ai, calculator, setback, history, reports

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown lifespan events.
    Guarantees clean pooling closures.
    """
    logger.info("Initializing TOAT Land Intelligence & Spatial Analysis System API...")
    yield
    logger.info("Deactivating engine connection pools...")
    await engine.dispose()

# Create main app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Precision Geospatial Analysis and AI Zoning Feasibility evaluation system.",
    lifespan=lifespan
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register global Rate Limiter check on all routes dynamically
@app.middleware("http")
async def check_api_rate_limits(request: Request, call_next):
    # Skip rate limiting on simple health check and Swagger docs
    path = request.url.path
    if path not in ["/health", "/docs", "/openapi.json"]:
        await rate_limiter.check_rate_limit(request)
    response = await call_next(request)
    return response

# Include Sub-Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(zoning.router, prefix=settings.API_V1_PREFIX)
app.include_router(plots.router, prefix=settings.API_V1_PREFIX)
app.include_router(ai.router, prefix=settings.API_V1_PREFIX)
app.include_router(calculator.router, prefix=settings.API_V1_PREFIX)
app.include_router(setback.router, prefix=settings.API_V1_PREFIX)
app.include_router(history.router, prefix=settings.API_V1_PREFIX)
app.include_router(reports.router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["Status Checks"])
async def system_health_status(db: AsyncSession = Depends(get_db)):
    """
    Performs comprehensive diagnostic health check checks on database.
    """
    try:
        # Diagnostic test query
        await db.execute(text("SELECT 1;"))
        return {
            "status": "healthy",
            "database": "connected",
            "project_name": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION
        }
    except Exception as e:
        logger.error(f"Diagnostic health check failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": f"connection_failed: {str(e)}"
            }
        )

@app.get("/", tags=["Status Checks"])
async def root_redirect():
    """
    Root endpoint detailing project metadata.
    """
    return {
        "message": f"Welcome to the {settings.PROJECT_NAME} API.",
        "documentation": "/docs"
    }
