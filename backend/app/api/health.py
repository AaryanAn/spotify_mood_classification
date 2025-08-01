"""
Health check endpoints
"""
from fastapi import APIRouter
import redis.asyncio as aioredis
import structlog
from datetime import datetime

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
async def detailed_health_check():
    """Detailed health check including database and Redis connectivity"""
    checks = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Database check using asyncpg pool directly (bypasses SQLAlchemy prepared statements)
    try:
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
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