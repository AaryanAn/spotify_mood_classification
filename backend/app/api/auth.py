"""
Spotify OAuth authentication endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import structlog
from datetime import datetime, timedelta
from typing import Optional
import secrets
import redis.asyncio as aioredis

from app.models.database import get_db, User
from app.utils.config import get_settings
from app.services.jwt_service import create_access_token, verify_token

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


def get_spotify_oauth() -> SpotifyOAuth:
    """Get Spotify OAuth handler"""
    return SpotifyOAuth(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
        redirect_uri=settings.spotify_redirect_uri,
        scope="user-read-private user-read-email playlist-read-private playlist-read-collaborative user-library-read",
        show_dialog=True,
    )


@router.get("/login")
async def login():
    """Initiate Spotify OAuth login"""
    try:
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in Redis with expiration
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.setex(f"oauth_state:{state}", 600, "valid")  # 10 min expiration
        await redis_client.close()
        
        # Create authorization URL
        sp_oauth = get_spotify_oauth()
        auth_url = sp_oauth.get_authorize_url(state=state)
        
        return {"auth_url": auth_url, "state": state}
    
    except Exception as e:
        logger.error("OAuth login initiation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate login"
        )


@router.post("/callback")
async def callback(
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Spotify OAuth callback"""
    try:
        # Verify state parameter
        redis_client = aioredis.from_url(settings.redis_url)
        stored_state = await redis_client.get(f"oauth_state:{state}")
        await redis_client.delete(f"oauth_state:{state}")
        await redis_client.close()
        
        if not stored_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired state parameter"
            )
        
        # Exchange authorization code for access token
        sp_oauth = get_spotify_oauth()
        token_info = sp_oauth.get_access_token(code)
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain access token"
            )
        
        # Get user information from Spotify
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user_info = sp.current_user()
        
        # Create or update user in database
        user = await get_or_create_user(db, user_info, token_info)
        
        # Generate JWT token
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email}
        )
        
        logger.info("User authenticated successfully", user_id=user.id)
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "display_name": user.display_name,
                "email": user.email,
                "country": user.country,
                "followers": user.followers,
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


async def get_or_create_user(
    db: AsyncSession,
    user_info: dict,
    token_info: dict
) -> User:
    """Get existing user or create new one"""
    # Check if user exists
    result = await db.execute(
        select(User).where(User.id == user_info['id'])
    )
    user = result.scalar_one_or_none()
    
    if user:
        # Update existing user
        user.display_name = user_info.get('display_name')
        user.email = user_info.get('email')
        user.country = user_info.get('country')
        user.followers = user_info.get('followers', {}).get('total', 0)
        user.spotify_url = user_info.get('external_urls', {}).get('spotify')
        user.access_token = token_info['access_token']
        user.refresh_token = token_info.get('refresh_token')
        user.token_expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
        user.updated_at = datetime.utcnow()
    else:
        # Create new user
        user = User(
            id=user_info['id'],
            display_name=user_info.get('display_name'),
            email=user_info.get('email'),
            country=user_info.get('country'),
            followers=user_info.get('followers', {}).get('total', 0),
            spotify_url=user_info.get('external_urls', {}).get('spotify'),
            access_token=token_info['access_token'],
            refresh_token=token_info.get('refresh_token'),
            token_expires_at=datetime.utcnow() + timedelta(seconds=token_info['expires_in']),
        )
        db.add(user)
    
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/refresh")
async def refresh_token(
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Refresh Spotify access token"""
    try:
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == current_user["sub"])
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Refresh Spotify token
        sp_oauth = get_spotify_oauth()
        token_info = sp_oauth.refresh_access_token(user.refresh_token)
        
        # Update user tokens
        user.access_token = token_info['access_token']
        if 'refresh_token' in token_info:
            user.refresh_token = token_info['refresh_token']
        user.token_expires_at = datetime.utcnow() + timedelta(seconds=token_info['expires_in'])
        user.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {"message": "Token refreshed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token refresh failed", error=str(e), user_id=current_user.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(current_user: dict = Depends(verify_token)):
    """Logout user"""
    # In a production app, you might want to blacklist the JWT token
    # For now, we'll just return success
    logger.info("User logged out", user_id=current_user["sub"])
    return {"message": "Successfully logged out"}


@router.get("/debug-token")
async def debug_token(
    current_user: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check token status"""
    try:
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == current_user["sub"])
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}
        
        # Check token expiration
        token_expired = user.token_expires_at < datetime.utcnow() if user.token_expires_at else True
        
        return {
            "user_id": user.id,
            "token_expires_at": user.token_expires_at.isoformat() if user.token_expires_at else None,
            "token_expired": token_expired,
            "has_refresh_token": bool(user.refresh_token),
            "current_time": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Token debug failed", error=str(e))
        return {"error": str(e)} 