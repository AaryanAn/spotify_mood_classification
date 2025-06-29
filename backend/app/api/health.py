"""
Health check endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
import structlog
from datetime import datetime

from app.models.database import get_db
from app.utils.config import get_settings

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check including database and Redis connectivity"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Database check
    try:
        result = await db.execute(text("SELECT 1"))
        await result.fetchone()
        checks["services"]["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        checks["services"]["database"] = {"status": "unhealthy", "message": str(e)}
        checks["status"] = "degraded"
    
    # Redis check
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        checks["services"]["redis"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        checks["services"]["redis"] = {"status": "unhealthy", "message": str(e)}
        checks["status"] = "degraded"
    
    return checks 