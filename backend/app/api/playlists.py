"""
Playlist management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
import spotipy
import structlog
from datetime import datetime
import redis.asyncio as aioredis
import json

from app.services.jwt_service import get_current_user_id
from app.utils.config import get_settings
from app.services.spotify_service import SpotifyService

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


async def get_user_asyncpg(user_id: str) -> Optional[dict]:
    """Get user data using direct asyncpg (bypasses SQLAlchemy prepared statements)"""
    from app.models.database import get_asyncpg_pool
    
    pool = await get_asyncpg_pool()
    async with pool.acquire() as conn:
        # Get user data using raw SQL
        user_row = await conn.fetchrow(
            "SELECT id, access_token, refresh_token, token_expires_at FROM users WHERE id = $1",
            user_id
        )
        
        if user_row:
            return {
                "id": user_row["id"],
                "access_token": user_row["access_token"],
                "refresh_token": user_row["refresh_token"],
                "token_expires_at": user_row["token_expires_at"]
            }
        return None


@router.get("/")
async def get_user_playlists(
    limit: int = 10000,  # High default to fetch all playlists
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get user's playlists from Spotify - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        # Get user from database using direct asyncpg (NO SQLALCHEMY)
        user_data = await get_user_asyncpg(current_user_id)
        
        if not user_data or not user_data.get('access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Spotify"
            )
        
        # Check Redis cache first
        redis_client = aioredis.from_url(settings.redis_url)
        cache_key = f"playlists:{current_user_id}:{limit}:{offset}"
        cached_playlists = await redis_client.get(cache_key)
        
        if cached_playlists:
            await redis_client.close()
            return json.loads(cached_playlists)
        
        # Get playlists from Spotify (returns list directly)
        spotify_service = SpotifyService(user_data['access_token'])
        playlists_list = await spotify_service.get_user_playlists(limit=limit, offset=offset)
        
        # Format response to match expected frontend structure
        response_data = {
            "items": playlists_list,
            "total": len(playlists_list),
            "limit": limit,
            "offset": offset
        }
        
        # Cache results for 5 minutes
        await redis_client.setex(cache_key, 300, json.dumps(response_data))
        await redis_client.close()
        
        logger.info("Retrieved user playlists", user_id=current_user_id, count=len(playlists_list))
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get playlists", error=str(e), user_id=current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve playlists"
        )


@router.get("/{playlist_id}")
async def get_playlist_details(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get detailed playlist information - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        # Get user from database using direct asyncpg (NO SQLALCHEMY)
        user_data = await get_user_asyncpg(current_user_id)
        
        if not user_data or not user_data.get('access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Spotify"
            )
        
        # Check cache first
        redis_client = aioredis.from_url(settings.redis_url)
        cache_key = f"playlist_details:{playlist_id}"
        cached_data = await redis_client.get(cache_key)
        
        if cached_data:
            await redis_client.close()
            return json.loads(cached_data)
        
        # Get playlist from Spotify
        spotify_service = SpotifyService(user_data['access_token'])
        playlist_data = await spotify_service.get_playlist_details(playlist_id)
        
        # Cache for 10 minutes
        await redis_client.setex(cache_key, 600, json.dumps(playlist_data))
        await redis_client.close()
        
        logger.info("Retrieved playlist details", playlist_id=playlist_id, user_id=current_user_id)
        return playlist_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get playlist details", error=str(e), playlist_id=playlist_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve playlist details"
        )


@router.post("/{playlist_id}/save")
async def save_playlist_to_db(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Save playlist and its tracks to database for mood analysis - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    logger.info("💾 [DEBUG] Starting playlist save", 
                playlist_id=playlist_id, 
                user_id=current_user_id)
    
    try:
        # Get user from database using direct asyncpg (NO SQLALCHEMY)
        user_data = await get_user_asyncpg(current_user_id)
        
        if not user_data or not user_data.get('access_token'):
            logger.error("❌ [DEBUG] User not authenticated")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Spotify"
            )
        
        logger.info("✅ [DEBUG] User authenticated", access_token_prefix=user_data['access_token'][:20] + "..." if user_data['access_token'] else "None")
        
        # Check if playlist already exists using raw asyncpg
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Check if playlist already exists
            existing_playlist = await conn.fetchrow(
                "SELECT id FROM playlists WHERE id = $1",
                playlist_id
            )
            
            if existing_playlist:
                logger.info("✅ [DEBUG] Playlist already exists in database")
                return {"message": "Playlist already saved", "playlist_id": playlist_id}
            
            logger.info("🔍 [DEBUG] Playlist not in database, fetching from Spotify")
            
            # Save playlist data synchronously (ensure complete save before returning)
            spotify_service = SpotifyService(user_data['access_token'])
            
            # Get playlist details
            logger.info("📡 [DEBUG] Fetching playlist details from Spotify")
            playlist_data = await spotify_service.get_playlist_details(playlist_id)
            
            if not playlist_data:
                logger.error("❌ [DEBUG] Failed to fetch playlist details")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Playlist not found or access denied"
                )
            
            logger.info("✅ [DEBUG] Playlist details fetched", name=playlist_data.get("name"))
            
            # Save playlist using raw SQL
            await conn.execute("""
                INSERT INTO playlists (
                    id, user_id, name, description, tracks_count, is_public, 
                    spotify_url, image_url, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                playlist_id,
                current_user_id,
                playlist_data["name"],
                playlist_data.get("description"),
                playlist_data["tracks"]["total"],
                playlist_data.get("public", True),
                playlist_data["external_urls"]["spotify"],
                playlist_data["images"][0]["url"] if playlist_data["images"] else None,
                datetime.utcnow(),
                datetime.utcnow()
            )
            logger.info("💾 [DEBUG] Playlist entity created", tracks_count=playlist_data["tracks"]["total"])
            
            # Get and save tracks with metadata (genres, artist info, etc.)
            logger.info("📡 [DEBUG] Fetching tracks with metadata")
            tracks_data = await spotify_service.get_playlist_tracks_with_metadata(playlist_id)
            logger.info("✅ [DEBUG] Tracks with metadata fetched", count=len(tracks_data))
            
            saved_tracks = 0
            for idx, track_data in enumerate(tracks_data):
                if not track_data.get("id"):
                    logger.warning("⚠️ [DEBUG] Skipping invalid track", position=idx)
                    continue
                
                # Check if track already exists
                existing_track = await conn.fetchrow(
                    "SELECT id FROM tracks WHERE id = $1",
                    track_data["id"]
                )
                
                if not existing_track:
                    # Save track with metadata using raw SQL
                    await conn.execute("""
                        INSERT INTO tracks (
                            id, name, artist, album, duration_ms, popularity, explicit,
                            spotify_url, preview_url, genres, artist_popularity, artist_followers,
                            release_year, release_date, acousticness, danceability, energy,
                            instrumentalness, liveness, loudness, speechiness, tempo, valence,
                            key, mode, time_signature, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28)
                    """,
                        track_data["id"],
                        track_data["name"],
                        track_data["artist"],
                        track_data["album"],
                        track_data["duration_ms"],
                        track_data.get("popularity"),
                        track_data.get("explicit", False),
                        track_data.get("spotify_url"),
                        track_data.get("preview_url"),
                        json.dumps(track_data.get("genres", [])),
                        track_data.get("artist_popularity"),
                        track_data.get("artist_followers"),
                        track_data.get("release_year"),
                        track_data.get("release_date"),
                        None,  # acousticness
                        None,  # danceability  
                        None,  # energy
                        None,  # instrumentalness
                        None,  # liveness
                        None,  # loudness
                        None,  # speechiness
                        None,  # tempo
                        None,  # valence
                        None,  # key
                        None,  # mode
                        None,  # time_signature
                        datetime.utcnow(),
                        datetime.utcnow()
                    )
                    logger.debug("💾 [DEBUG] Added new track", 
                               track_name=track_data["name"],
                               genres=track_data.get("genres", []))
                else:
                    logger.debug("✅ [DEBUG] Track already exists", track_name=track_data["name"])
                
                # Save playlist-track relationship using raw SQL
                await conn.execute("""
                    INSERT INTO playlist_tracks (playlist_id, track_id, position, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5)
                """,
                    playlist_id,
                    track_data["id"],
                    idx,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                saved_tracks += 1
            
            logger.info("💾 [DEBUG] All data committed successfully", saved_tracks=saved_tracks)
            
        logger.info("✅ [DEBUG] Playlist saved successfully", 
                   playlist_id=playlist_id, 
                   user_id=current_user_id,
                   total_tracks=saved_tracks)
        
        return {
            "message": "Playlist saved successfully", 
            "playlist_id": playlist_id,
            "tracks_saved": saved_tracks,
            "method": "genre-metadata-based"
        }
        
    except HTTPException as he:
        logger.error("❌ [DEBUG] HTTP Exception in playlist save", 
                    status_code=he.status_code,
                    detail=he.detail)
        raise
    except Exception as e:
        logger.error("❌ [DEBUG] Unexpected error saving playlist", 
                    error=str(e), 
                    error_type=type(e).__name__,
                    playlist_id=playlist_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save playlist: {str(e)}"
        )


@router.get("/{playlist_id}/tracks")
async def get_playlist_tracks(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Get tracks from saved playlist - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Check if user has access to this playlist
            playlist = await conn.fetchrow(
                "SELECT id, name FROM playlists WHERE id = $1 AND user_id = $2",
                playlist_id, current_user_id
            )
            
            if not playlist:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Playlist not found or access denied"
                )
            
            # Get tracks with their metadata using raw SQL
            tracks_rows = await conn.fetch("""
                SELECT 
                    t.id, t.name, t.artist, t.album, t.duration_ms, t.popularity, 
                    t.explicit, t.spotify_url, t.preview_url, t.genres,
                    t.acousticness, t.danceability, t.energy, t.instrumentalness,
                    t.liveness, t.loudness, t.speechiness, t.tempo, t.valence,
                    t.key, t.mode, t.time_signature, pt.position
                FROM tracks t
                JOIN playlist_tracks pt ON t.id = pt.track_id
                WHERE pt.playlist_id = $1
                ORDER BY pt.position
            """, playlist_id)
            
            tracks_data = []
            for track_row in tracks_rows:
                tracks_data.append({
                    "id": track_row["id"],
                    "name": track_row["name"],
                    "artist": track_row["artist"],
                    "album": track_row["album"],
                    "duration_ms": track_row["duration_ms"],
                    "popularity": track_row["popularity"],
                    "explicit": track_row["explicit"],
                    "spotify_url": track_row["spotify_url"],
                    "preview_url": track_row["preview_url"],
                    "position": track_row["position"],
                    "genres": json.loads(track_row["genres"]) if track_row["genres"] else [],
                    "audio_features": {
                        "acousticness": track_row["acousticness"],
                        "danceability": track_row["danceability"],
                        "energy": track_row["energy"],
                        "instrumentalness": track_row["instrumentalness"],
                        "liveness": track_row["liveness"],
                        "loudness": track_row["loudness"],
                        "speechiness": track_row["speechiness"],
                        "tempo": track_row["tempo"],
                        "valence": track_row["valence"],
                        "key": track_row["key"],
                        "mode": track_row["mode"],
                        "time_signature": track_row["time_signature"],
                    }
                })
            
            return {
                "playlist_id": playlist_id,
                "playlist_name": playlist["name"],
                "tracks": tracks_data
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get playlist tracks", error=str(e), playlist_id=playlist_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve playlist tracks"
        ) 