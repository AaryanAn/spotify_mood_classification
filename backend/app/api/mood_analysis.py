"""
Mood Analysis API endpoints
Updated to use genre and metadata-based classification instead of deprecated audio features
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, Any, List
import structlog

from app.services.jwt_service import get_current_user_id
from app.services.spotify_service import SpotifyService
from app.services.mood_classifier import MoodClassifier
from app.services.enhanced_mood_classifier import EnhancedMoodClassifier
import json
from datetime import datetime

logger = structlog.get_logger()
router = APIRouter()

# Initialize mood classifier
# mood_classifier will be instantiated based on use_lyrics parameter


async def get_user_asyncpg(user_id: str) -> dict:
    """Get user data using direct asyncpg (bypasses SQLAlchemy prepared statements)"""
    from app.models.database import get_asyncpg_pool
    
    pool = await get_asyncpg_pool()
    async with pool.acquire() as conn:
        # Get user data using raw SQL
        user_row = await conn.fetchrow(
            "SELECT id, access_token, refresh_token, token_expires_at, display_name, email FROM users WHERE id = $1",
            user_id
        )
        
        if user_row:
            return {
                "id": user_row["id"],
                "access_token": user_row["access_token"],
                "refresh_token": user_row["refresh_token"],
                "token_expires_at": user_row["token_expires_at"],
                "display_name": user_row["display_name"],
                "email": user_row["email"]
            }
        return None


@router.post("/{playlist_id}/analyze")
async def analyze_playlist_mood(
    playlist_id: str,
    use_lyrics: bool = False,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Analyze playlist mood using genre and metadata-based classification - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues
    """
    try:
        logger.info("Starting playlist mood analysis", 
                   playlist_id=playlist_id, 
                   user_id=current_user_id)
        
        # Get user from database using direct asyncpg (NO SQLALCHEMY)
        current_user = await get_user_asyncpg(current_user_id)
        
        if not current_user or not current_user.get('access_token'):
            raise HTTPException(
                status_code=401,
                detail="User not authenticated with Spotify"
            )
        
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Check if playlist exists in database using raw SQL
            playlist = await conn.fetchrow(
                "SELECT id, name FROM playlists WHERE id = $1 AND user_id = $2",
                playlist_id, current_user_id
            )
            
            if not playlist:
                logger.warning("Playlist not found for mood analysis", 
                              playlist_id=playlist_id, 
                              user_id=current_user_id)
                raise HTTPException(
                    status_code=404, 
                    detail=f"Playlist not found or access denied. Make sure you've saved the playlist first."
                )
            
            # Initialize Spotify service
            spotify_service = SpotifyService(current_user["access_token"])
            
            # Check if token is valid
            if not spotify_service.is_token_valid():
                logger.error("Invalid Spotify token for mood analysis", user_id=current_user_id)
                raise HTTPException(
                    status_code=401,
                    detail="Spotify token expired. Please log out and log back in."
                )
            
            # Get tracks with comprehensive metadata (genres, artist info, etc.)
            logger.info("Fetching tracks with metadata for mood analysis", playlist_id=playlist_id)
            tracks_data = await spotify_service.get_playlist_tracks_with_metadata(playlist_id)
            
            if not tracks_data:
                logger.warning("No tracks found for mood analysis", playlist_id=playlist_id)
                raise HTTPException(
                    status_code=404,
                    detail="No tracks found in playlist or unable to fetch track data"
                )
            
            logger.info("Fetched tracks for analysis", 
                       playlist_id=playlist_id,
                       track_count=len(tracks_data))
            
            # Analyze mood using genre and metadata (and optionally lyrics)
            logger.info("Performing mood classification", 
                       playlist_id=playlist_id,
                       tracks_count=len(tracks_data),
                       use_lyrics=use_lyrics)
            
            if use_lyrics:
                mood_classifier = EnhancedMoodClassifier()
                mood_result = await mood_classifier.classify_playlist_mood_with_lyrics(tracks_data)
            else:
                mood_classifier = MoodClassifier()
                mood_result = await mood_classifier.classify_playlist_mood(tracks_data)
            
            logger.info("Mood analysis completed", 
                       playlist_id=playlist_id,
                       primary_mood=mood_result.get("primary_mood"),
                       confidence=mood_result.get("confidence"))
            
            # Save mood analysis to database using raw SQL
            analysis_id = f"{playlist_id}_{current_user_id}_{int(datetime.utcnow().timestamp())}"
            await conn.execute("""
                INSERT INTO mood_analyses (
                    id, playlist_id, user_id, primary_mood, confidence, mood_distribution,
                    tracks_analyzed, analysis_method, analysis_data, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                analysis_id,
                playlist_id,
                current_user_id,
                mood_result["primary_mood"],
                mood_result["confidence"],
                json.dumps(mood_result["mood_distribution"]),
                mood_result.get("tracks_analyzed", len(tracks_data)),
                mood_result.get("method", "genre-metadata-analysis"),
                json.dumps({
                    "model_version": mood_classifier.get_model_version(),
                    "total_tracks": len(tracks_data),
                    "tracks_with_genres": len([t for t in tracks_data if t.get('genres')]),
                    "unique_genres": len(set([g for t in tracks_data for g in t.get('genres', [])])),
                    "sample_genres": list(set([g for t in tracks_data for g in t.get('genres', [])]))[:10],
                    "use_lyrics": use_lyrics,
                    "lyrics_coverage": mood_result.get("lyrics_coverage", 0.0),
                    "analysis_components": mood_result.get("analysis_components", {})
                }),
                datetime.utcnow()
            )
            
            logger.info("Mood analysis saved to database", 
                       playlist_id=playlist_id,
                       analysis_id=analysis_id)
            
            # Prepare response with enhanced track analysis data
            response = {
                "playlist_id": playlist_id,
                "primary_mood": mood_result["primary_mood"],
                "confidence": mood_result["confidence"],
                "mood_distribution": mood_result["mood_distribution"],
                "analysis_summary": {
                    "total_tracks": len(tracks_data),
                    "tracks_analyzed": mood_result.get("tracks_analyzed", len(tracks_data)),
                    "analysis_method": mood_result.get("method", "genre-metadata-analysis"),
                    "model_version": mood_classifier.get_model_version(),
                    "tracks_with_genres": len([t for t in tracks_data if t.get('genres')]),
                    "unique_genres_count": len(set([g for t in tracks_data for g in t.get('genres', [])])),
                    "sample_genres": list(set([g for t in tracks_data for g in t.get('genres', [])]))[:10],
                    "use_lyrics": use_lyrics,
                    "lyrics_coverage": mood_result.get("lyrics_coverage", 0.0),
                    "analysis_components": mood_result.get("analysis_components", {})
                },
                "track_details": [
                    {
                        "name": track["name"],
                        "artist": track["artist"],
                        "genres": track.get("genres", []),
                        "popularity": track.get("popularity", 0),
                        "duration_ms": track.get("duration_ms", 0),
                        "explicit": track.get("explicit", False),
                        "release_year": track.get("release_year")
                    }
                    for track in tracks_data[:10]  # First 10 tracks for UI display
                ],
                "created_at": datetime.utcnow().isoformat()
            }
            
            return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze playlist mood", 
                    playlist_id=playlist_id,
                    user_id=current_user_id,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze playlist mood: {str(e)}"
        )


@router.get("/{playlist_id}/analysis")
async def get_playlist_analysis(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get the latest mood analysis for a playlist - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Get the latest mood analysis using raw SQL
            analysis = await conn.fetchrow("""
                SELECT id, playlist_id, user_id, primary_mood, confidence, mood_distribution,
                       tracks_analyzed, analysis_method, created_at
                FROM mood_analyses
                WHERE playlist_id = $1 AND user_id = $2
                ORDER BY created_at DESC
                LIMIT 1
            """, playlist_id, current_user_id)
            
            if not analysis:
                raise HTTPException(
                    status_code=404,
                    detail="No mood analysis found for this playlist"
                )
            
            return {
                "playlist_id": analysis["playlist_id"],
                "primary_mood": analysis["primary_mood"],
                "mood_confidence": analysis["confidence"],  # Frontend expects this name
                "mood_distribution": json.loads(analysis["mood_distribution"]) if analysis["mood_distribution"] else {},
                "tracks_analyzed": analysis["tracks_analyzed"],
                "created_at": analysis["created_at"].isoformat() if analysis["created_at"] else None,
                "analysis_method": analysis["analysis_method"],
                # Add legacy fields for frontend compatibility
                "avg_valence": 0.5,  # Placeholder values
                "avg_energy": 0.5,
                "avg_danceability": 0.5,
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get playlist analysis", 
                    playlist_id=playlist_id,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve mood analysis"
        )


@router.get("/{playlist_id}/history")
async def get_mood_analysis_history(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> List[Dict[str, Any]]:
    """Get mood analysis history for a playlist - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Get all analyses for this playlist using raw SQL
            analyses = await conn.fetch("""
                SELECT id, primary_mood, confidence, mood_distribution, tracks_analyzed,
                       analysis_method, created_at
                FROM mood_analyses
                WHERE playlist_id = $1 AND user_id = $2
                ORDER BY created_at DESC
            """, playlist_id, current_user_id)
            
            return [
                {
                    "id": analysis["id"],
                    "primary_mood": analysis["primary_mood"],
                    "confidence": analysis["confidence"],
                    "mood_distribution": json.loads(analysis["mood_distribution"]) if analysis["mood_distribution"] else {},
                    "tracks_analyzed": analysis["tracks_analyzed"],
                    "analysis_method": analysis["analysis_method"],
                    "created_at": analysis["created_at"].isoformat() if analysis["created_at"] else None
                }
                for analysis in analyses
            ]
        
    except Exception as e:
        logger.error("Failed to get mood analysis history", 
                    playlist_id=playlist_id,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve mood analysis history"
        )


@router.get("/{playlist_id}/stats")
async def get_mood_stats(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """Get aggregated mood statistics for a playlist - BYPASSES SQLALCHEMY to avoid pgbouncer prepared statement issues"""
    try:
        from app.models.database import get_asyncpg_pool
        pool = await get_asyncpg_pool()
        
        async with pool.acquire() as conn:
            # Get all analyses for this playlist using raw SQL
            analyses = await conn.fetch("""
                SELECT id, primary_mood, confidence, analysis_method, created_at
                FROM mood_analyses
                WHERE playlist_id = $1 AND user_id = $2
                ORDER BY created_at DESC
            """, playlist_id, current_user_id)
            
            if not analyses:
                raise HTTPException(
                    status_code=404,
                    detail="No mood analysis found for this playlist"
                )
            
            # Get latest analysis
            latest = analyses[0]
            
            # Calculate trends if multiple analyses exist
            mood_trend = None
            if len(analyses) > 1:
                previous = analyses[1]
                if latest["primary_mood"] == previous["primary_mood"]:
                    mood_trend = "stable"
                else:
                    mood_trend = f"changed from {previous['primary_mood']} to {latest['primary_mood']}"
            
            return {
                "playlist_id": playlist_id,
                "latest_analysis": {
                    "primary_mood": latest["primary_mood"],
                    "confidence": latest["confidence"],
                    "analysis_method": latest["analysis_method"],
                    "created_at": latest["created_at"].isoformat() if latest["created_at"] else None
                },
                "total_analyses": len(analyses),
                "mood_trend": mood_trend,
                "analysis_history": [
                    {
                        "mood": analysis["primary_mood"],
                        "confidence": analysis["confidence"],
                        "date": analysis["created_at"].isoformat() if analysis["created_at"] else None
                    }
                    for analysis in analyses[:5]  # Last 5 analyses
                ]
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get mood stats", 
                    playlist_id=playlist_id,
                    error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve mood statistics"
        ) 