"""
Mood analysis endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import Dict, Any, List
import structlog
from datetime import datetime
import redis.asyncio as aioredis
import json

from app.models.database import get_db, User, Playlist, Track, PlaylistTrack, MoodAnalysis
from app.services.jwt_service import get_current_user_id
from app.services.mood_classifier import MoodClassifier
from app.utils.config import get_settings

router = APIRouter()
logger = structlog.get_logger()
settings = get_settings()

# Initialize mood classifier
mood_classifier = MoodClassifier()


@router.post("/{playlist_id}/analyze")
async def analyze_playlist_mood(
    playlist_id: str,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Analyze playlist mood"""
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
        
        # Check if analysis already exists and is recent
        result = await db.execute(
            select(MoodAnalysis).where(
                and_(
                    MoodAnalysis.playlist_id == playlist_id,
                    MoodAnalysis.user_id == current_user_id
                )
            ).order_by(MoodAnalysis.created_at.desc())
        )
        existing_analysis = result.scalar_one_or_none()
        
        if existing_analysis:
            # Return existing analysis if less than 1 hour old
            time_diff = datetime.utcnow() - existing_analysis.created_at
            if time_diff.total_seconds() < 3600:  # 1 hour
                return format_mood_analysis(existing_analysis)
        
        # Add background task to perform analysis
        background_tasks.add_task(
            analyze_playlist_mood_background,
            playlist_id,
            current_user_id
        )
        
        return {"message": "Mood analysis started", "playlist_id": playlist_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start mood analysis", error=str(e), playlist_id=playlist_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start mood analysis"
        )


async def analyze_playlist_mood_background(playlist_id: str, user_id: str):
    """Background task to analyze playlist mood"""
    start_time = datetime.utcnow()
    
    from app.models.database import async_session_maker
    try:
        # Create new database session for background task
        async with async_session_maker() as db:
            # Get playlist tracks with audio features
            result = await db.execute(
                select(Track, PlaylistTrack)
                .join(PlaylistTrack, Track.id == PlaylistTrack.track_id)
                .where(PlaylistTrack.playlist_id == playlist_id)
                .order_by(PlaylistTrack.position)
            )
            
            tracks_data = []
            for track, playlist_track in result.all():
                if all([
                    track.valence is not None,
                    track.energy is not None,
                    track.danceability is not None,
                    track.acousticness is not None,
                    track.tempo is not None
                ]):
                    tracks_data.append({
                        "valence": track.valence,
                        "energy": track.energy,
                        "danceability": track.danceability,
                        "acousticness": track.acousticness,
                        "tempo": track.tempo,
                        "loudness": track.loudness,
                        "speechiness": track.speechiness,
                        "instrumentalness": track.instrumentalness,
                        "liveness": track.liveness,
                    })
            
            if not tracks_data:
                logger.error("No tracks with audio features found", playlist_id=playlist_id)
                return
            
            # Perform mood classification
            mood_result = await mood_classifier.classify_playlist_mood(tracks_data)
            
            # Calculate aggregated features
            avg_features = calculate_average_features(tracks_data)
            
            # Save analysis results
            analysis = MoodAnalysis(
                playlist_id=playlist_id,
                user_id=user_id,
                primary_mood=mood_result["primary_mood"],
                mood_confidence=mood_result["confidence"],
                mood_distribution=mood_result["mood_distribution"],
                avg_valence=avg_features["valence"],
                avg_energy=avg_features["energy"],
                avg_danceability=avg_features["danceability"],
                avg_acousticness=avg_features["acousticness"],
                avg_tempo=avg_features["tempo"],
                tracks_analyzed=len(tracks_data),
                model_version=mood_classifier.get_model_version(),
                analysis_duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            )
            
            db.add(analysis)
            await db.commit()
            
            # Update playlist analyzed timestamp
            await db.execute(
                select(Playlist).where(Playlist.id == playlist_id)
            )
            playlist = result.scalar_one_or_none()
            if playlist:
                playlist.analyzed_at = datetime.utcnow()
                await db.commit()
            
            # Cache results
            redis_client = aioredis.from_url(settings.redis_url)
            cache_key = f"mood_analysis:{playlist_id}:{user_id}"
            await redis_client.setex(
                cache_key, 
                3600,  # 1 hour
                json.dumps(format_mood_analysis(analysis))
            )
            await redis_client.close()
            
            logger.info("Mood analysis completed", playlist_id=playlist_id, user_id=user_id, 
                       primary_mood=mood_result["primary_mood"], confidence=mood_result["confidence"])
            
    except Exception as e:
        logger.error("Failed to analyze playlist mood", error=str(e), playlist_id=playlist_id)


@router.get("/{playlist_id}/analysis")
async def get_playlist_mood_analysis(
    playlist_id: str,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get playlist mood analysis results"""
    try:
        # Check cache first
        redis_client = aioredis.from_url(settings.redis_url)
        cache_key = f"mood_analysis:{playlist_id}:{current_user_id}"
        cached_analysis = await redis_client.get(cache_key)
        
        if cached_analysis:
            await redis_client.close()
            return json.loads(cached_analysis)
        
        # Get from database
        result = await db.execute(
            select(MoodAnalysis).where(
                and_(
                    MoodAnalysis.playlist_id == playlist_id,
                    MoodAnalysis.user_id == current_user_id
                )
            ).order_by(MoodAnalysis.created_at.desc())
        )
        analysis = result.scalar_one_or_none()
        
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mood analysis not found. Please run analysis first."
            )
        
        formatted_analysis = format_mood_analysis(analysis)
        
        # Cache results
        await redis_client.setex(cache_key, 3600, json.dumps(formatted_analysis))
        await redis_client.close()
        
        return formatted_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get mood analysis", error=str(e), playlist_id=playlist_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve mood analysis"
        )


@router.get("/history")
async def get_mood_analysis_history(
    limit: int = 10,
    offset: int = 0,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get user's mood analysis history"""
    try:
        result = await db.execute(
            select(MoodAnalysis, Playlist)
            .join(Playlist, MoodAnalysis.playlist_id == Playlist.id)
            .where(MoodAnalysis.user_id == current_user_id)
            .order_by(MoodAnalysis.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        history = []
        for analysis, playlist in result.all():
            history.append({
                "playlist_id": playlist.id,
                "playlist_name": playlist.name,
                "playlist_image": playlist.image_url,
                "primary_mood": analysis.primary_mood,
                "mood_confidence": analysis.mood_confidence,
                "tracks_analyzed": analysis.tracks_analyzed,
                "analyzed_at": analysis.created_at.isoformat(),
                "analysis_duration_ms": analysis.analysis_duration_ms,
            })
        
        return {
            "history": history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error("Failed to get mood analysis history", error=str(e), user_id=current_user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve mood analysis history"
        )


@router.get("/moods")
async def get_supported_moods():
    """Get list of supported mood categories"""
    return {
        "moods": mood_classifier.get_supported_moods(),
        "descriptions": mood_classifier.get_mood_descriptions()
    }


def calculate_average_features(tracks_data: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate average audio features for tracks"""
    if not tracks_data:
        return {}
    
    features = ["valence", "energy", "danceability", "acousticness", "tempo"]
    averages = {}
    
    for feature in features:
        values = [track[feature] for track in tracks_data if track.get(feature) is not None]
        averages[feature] = sum(values) / len(values) if values else 0.0
    
    return averages


def format_mood_analysis(analysis: MoodAnalysis) -> Dict[str, Any]:
    """Format mood analysis for API response"""
    return {
        "playlist_id": analysis.playlist_id,
        "primary_mood": analysis.primary_mood,
        "mood_confidence": analysis.mood_confidence,
        "mood_distribution": analysis.mood_distribution,
        "audio_features": {
            "avg_valence": analysis.avg_valence,
            "avg_energy": analysis.avg_energy,
            "avg_danceability": analysis.avg_danceability,
            "avg_acousticness": analysis.avg_acousticness,
            "avg_tempo": analysis.avg_tempo,
        },
        "metadata": {
            "tracks_analyzed": analysis.tracks_analyzed,
            "model_version": analysis.model_version,
            "analysis_duration_ms": analysis.analysis_duration_ms,
            "analyzed_at": analysis.created_at.isoformat(),
        }
    } 