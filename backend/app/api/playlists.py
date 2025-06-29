"""
Playlist management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import spotipy
import structlog
from datetime import datetime
import redis.asyncio as aioredis
import json

from app.models.database import get_db, User, Playlist, Track, PlaylistTrack
from app.services.jwt_service import get_current_user_id
from app.utils.config import get_settings
from app.services.spotify_service import SpotifyService

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()


@router.get("/")
async def get_user_playlists(
    limit: int = 10000,  # High default to fetch all playlists
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user's playlists from Spotify"""
    try:
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == current_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.access_token:
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
        spotify_service = SpotifyService(user.access_token)
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
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed playlist information"""
    try:
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == current_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.access_token:
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
        spotify_service = SpotifyService(user.access_token)
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
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Save playlist and its tracks to database for mood analysis"""
    logger.info("💾 [DEBUG] Starting playlist save", 
                playlist_id=playlist_id, 
                user_id=current_user_id)
    
    try:
        # Get user from database
        result = await db.execute(
            select(User).where(User.id == current_user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.access_token:
            logger.error("❌ [DEBUG] User not authenticated")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Spotify"
            )
        
        logger.info("✅ [DEBUG] User authenticated", access_token_prefix=user.access_token[:20] + "..." if user.access_token else "None")
        
        # Check if playlist already exists
        result = await db.execute(
            select(Playlist).where(Playlist.id == playlist_id)
        )
        existing_playlist = result.scalar_one_or_none()
        
        if existing_playlist:
            logger.info("✅ [DEBUG] Playlist already exists in database")
            return {"message": "Playlist already saved", "playlist_id": playlist_id}
        
        logger.info("🔍 [DEBUG] Playlist not in database, fetching from Spotify")
        
        # Save playlist data synchronously (ensure complete save before returning)
        spotify_service = SpotifyService(user.access_token)
        
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
        
        # Save playlist
        playlist = Playlist(
            id=playlist_id,
            user_id=current_user_id,
            name=playlist_data["name"],
            description=playlist_data.get("description"),
            tracks_count=playlist_data["tracks"]["total"],
            is_public=playlist_data.get("public", True),
            spotify_url=playlist_data["external_urls"]["spotify"],
            image_url=playlist_data["images"][0]["url"] if playlist_data["images"] else None,
        )
        db.add(playlist)
        logger.info("💾 [DEBUG] Playlist entity created", tracks_count=playlist.tracks_count)
        
        # Get and save tracks with metadata (genres, artist info, etc.)
        logger.info("📡 [DEBUG] Fetching tracks with metadata")
        tracks_data = await spotify_service.get_playlist_tracks_with_metadata(playlist_id)
        logger.info("✅ [DEBUG] Tracks with metadata fetched", count=len(tracks_data))
        
        saved_tracks = 0
        for idx, track_data in enumerate(tracks_data):
            if not track_data.get("id"):
                logger.warning("⚠️ [DEBUG] Skipping invalid track", position=idx)
                continue
            
            # Save track with metadata (no audio features)
            track = Track(
                id=track_data["id"],
                name=track_data["name"],
                artist=track_data["artist"],
                album=track_data["album"],
                duration_ms=track_data["duration_ms"],
                popularity=track_data.get("popularity"),
                explicit=track_data.get("explicit", False),
                spotify_url=track_data.get("spotify_url"),
                preview_url=track_data.get("preview_url"),
                # Store genre and metadata information in JSON fields for mood analysis
                genres=json.dumps(track_data.get("genres", [])),
                artist_popularity=track_data.get("artist_popularity"),
                artist_followers=track_data.get("artist_followers"),
                release_year=track_data.get("release_year"),
                release_date=track_data.get("release_date"),
                # Set audio features to None since they're no longer available
                acousticness=None,
                danceability=None,
                energy=None,
                instrumentalness=None,
                liveness=None,
                loudness=None,
                speechiness=None,
                tempo=None,
                valence=None,
                key=None,
                mode=None,
                time_signature=None,
            )
            
            # Check if track already exists
            result = await db.execute(
                select(Track).where(Track.id == track_data["id"])
            )
            existing_track = result.scalar_one_or_none()
            
            if not existing_track:
                db.add(track)
                logger.debug("💾 [DEBUG] Added new track", 
                           track_name=track_data["name"],
                           genres=track_data.get("genres", []))
            else:
                logger.debug("✅ [DEBUG] Track already exists", track_name=track_data["name"])
            
            # Save playlist-track relationship
            playlist_track = PlaylistTrack(
                playlist_id=playlist_id,
                track_id=track_data["id"],
                position=idx,
            )
            db.add(playlist_track)
            saved_tracks += 1
        
        logger.info("💾 [DEBUG] Committing to database", saved_tracks=saved_tracks)
        await db.commit()
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
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get tracks from saved playlist"""
    try:
        # Check if user has access to this playlist
        result = await db.execute(
            select(Playlist).where(
                and_(Playlist.id == playlist_id, Playlist.user_id == current_user_id)
            )
        )
        playlist = result.scalar_one_or_none()
        
        if not playlist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Playlist not found or access denied"
            )
        
        # Get tracks with audio features
        result = await db.execute(
            select(Track, PlaylistTrack)
            .join(PlaylistTrack, Track.id == PlaylistTrack.track_id)
            .where(PlaylistTrack.playlist_id == playlist_id)
            .order_by(PlaylistTrack.position)
        )
        
        tracks_data = []
        for track, playlist_track in result.all():
            tracks_data.append({
                "id": track.id,
                "name": track.name,
                "artist": track.artist,
                "album": track.album,
                "duration_ms": track.duration_ms,
                "popularity": track.popularity,
                "explicit": track.explicit,
                "spotify_url": track.spotify_url,
                "preview_url": track.preview_url,
                "position": playlist_track.position,
                "audio_features": {
                    "acousticness": track.acousticness,
                    "danceability": track.danceability,
                    "energy": track.energy,
                    "instrumentalness": track.instrumentalness,
                    "liveness": track.liveness,
                    "loudness": track.loudness,
                    "speechiness": track.speechiness,
                    "tempo": track.tempo,
                    "valence": track.valence,
                    "key": track.key,
                    "mode": track.mode,
                    "time_signature": track.time_signature,
                }
            })
        
        return {
            "playlist_id": playlist_id,
            "playlist_name": playlist.name,
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