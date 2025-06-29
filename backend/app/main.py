"""
Main FastAPI application for Spotify Mood Classification
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
import uvicorn

from app.api import auth, playlists, mood_analysis, health
from app.models.database import init_db
from app.utils.config import get_settings
from app.utils.logging_config import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Spotify Mood Classification API")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down Spotify Mood Classification API")


app = FastAPI(
    title="Spotify Mood Classification API",
    description="Production-ready API for classifying Spotify playlist moods using ML",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app"] if settings.debug else ["yourdomain.com"],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["playlists"])
app.include_router(mood_analysis.router, prefix="/api/mood", tags=["mood-analysis"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Spotify Mood Classification API",
        "version": "1.0.0",
        "docs_url": "/docs" if settings.debug else None,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    logger.error("HTTP exception occurred", path=request.url.path, status_code=exc.status_code, detail=exc.detail)
    return {"error": exc.detail, "status_code": exc.status_code}


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    """Global server error handler"""
    logger.error("Internal server error", path=request.url.path, error=str(exc))
    return {"error": "Internal server error", "status_code": 500}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.reload,
        workers=settings.api_workers if not settings.reload else 1,
        log_level=settings.log_level.lower(),
    ) 