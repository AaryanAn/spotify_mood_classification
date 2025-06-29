"""
Main FastAPI application for Spotify Mood Classification
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog
import uvicorn
import os
import time

from app.api import auth, playlists, mood_analysis, health
from app.models.database import init_db
from app.utils.config import get_settings
from app.utils.logging_config import setup_logging

# Configure structured logging
setup_logging()
logger = structlog.get_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Spotify Mood Classifier API")
    settings = get_settings()
    logger.info("📊 Configuration loaded", 
                environment=settings.environment,
                cors_origins=settings.cors_origins,
                has_spotify_credentials=bool(settings.spotify_client_id and settings.spotify_client_secret))
    
    await init_db()
    logger.info("🗄️ Database initialized")
    yield
    # Shutdown
    logger.info("👋 Shutting down Spotify Mood Classifier API")


app = FastAPI(
    title="Spotify Mood Classifier",
    description="AI-powered mood classification for Spotify playlists",
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

# Debug logging middleware
@app.middleware("http")
async def debug_logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Log incoming request
    logger.info("📥 [REQUEST]", 
                method=request.method,
                url=str(request.url),
                headers=dict(request.headers),
                client_host=request.client.host if request.client else None)
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info("📤 [RESPONSE]",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=f"{process_time:.4f}s",
                response_headers=dict(response.headers))
    
    return response

# CORS middleware with debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

logger.info("🌐 CORS configured", origins=settings.cors_origins)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(playlists.router, prefix="/api/playlists", tags=["playlists"])
app.include_router(mood_analysis.router, prefix="/api/mood-analysis", tags=["mood-analysis"])

logger.info("🛣️ API routes configured")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Spotify Mood Classifier API",
        "version": "1.0.0",
        "docs_url": "/docs" if settings.debug else None,
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Global HTTP exception handler"""
    logger.error("HTTP exception occurred", path=request.url.path, status_code=exc.status_code, detail=exc.detail)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all other exceptions"""
    logger.error("Internal server error", path=request.url.path, error=str(exc))
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 