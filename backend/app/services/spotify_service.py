"""
Spotify API service wrapper
"""
import spotipy
from spotipy.exceptions import SpotifyException
from typing import List, Dict, Any, Optional
import structlog
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

logger = structlog.get_logger()


class SpotifyService:
    """Service for interacting with Spotify Web API"""
    
    def __init__(self, access_token: str):
        self.sp = spotipy.Spotify(auth=access_token)
        self.executor = ThreadPoolExecutor(max_workers=5)
    
    async def get_user_playlists(self, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Get user's playlists"""
        try:
            loop = asyncio.get_event_loop()
            playlists = await loop.run_in_executor(
                self.executor,
                lambda: self.sp.current_user_playlists(limit=limit, offset=offset)
            )
            return playlists
        except SpotifyException as e:
            logger.error("Spotify API error getting playlists", error=str(e))
            raise
    
    async def get_playlist_details(self, playlist_id: str) -> Dict[str, Any]:
        """Get detailed playlist information"""
        try:
            loop = asyncio.get_event_loop()
            playlist = await loop.run_in_executor(
                self.executor,
                lambda: self.sp.playlist(playlist_id)
            )
            return playlist
        except SpotifyException as e:
            logger.error("Spotify API error getting playlist details", error=str(e), playlist_id=playlist_id)
            raise
    
    async def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all tracks from a playlist"""
        try:
            tracks = []
            offset = 0
            
            while True:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    self.executor,
                    lambda: self.sp.playlist_tracks(
                        playlist_id, 
                        limit=min(limit, 100), 
                        offset=offset
                    )
                )
                
                tracks.extend(results["items"])
                
                if len(results["items"]) < 100 or len(tracks) >= limit:
                    break
                
                offset += 100
                # Rate limiting - Spotify allows 100 requests per minute
                await asyncio.sleep(0.1)
            
            return tracks[:limit]
            
        except SpotifyException as e:
            logger.error("Spotify API error getting playlist tracks", error=str(e), playlist_id=playlist_id)
            raise
    
    async def get_audio_features(self, track_ids: List[str]) -> List[Dict[str, Any]]:
        """Get audio features for multiple tracks"""
        try:
            # Spotify allows up to 100 track IDs per request
            all_features = []
            
            for i in range(0, len(track_ids), 100):
                batch_ids = track_ids[i:i+100]
                
                loop = asyncio.get_event_loop()
                features = await loop.run_in_executor(
                    self.executor,
                    lambda: self.sp.audio_features(batch_ids)
                )
                
                all_features.extend(features)
                
                # Rate limiting
                if i + 100 < len(track_ids):
                    await asyncio.sleep(0.1)
            
            return all_features
            
        except SpotifyException as e:
            logger.error("Spotify API error getting audio features", error=str(e))
            raise
    
    async def get_playlist_tracks_with_features(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get playlist tracks with their audio features"""
        try:
            # Get all tracks
            tracks = await self.get_playlist_tracks(playlist_id)
            
            # Extract track IDs (filter out None values)
            track_ids = [
                track["track"]["id"] 
                for track in tracks 
                if track["track"] and track["track"]["id"]
            ]
            
            if not track_ids:
                return tracks
            
            # Get audio features
            audio_features = await self.get_audio_features(track_ids)
            
            # Create mapping of track ID to audio features
            features_map = {
                features["id"]: features 
                for features in audio_features 
                if features
            }
            
            # Combine tracks with their audio features
            for track in tracks:
                if track["track"] and track["track"]["id"]:
                    track_id = track["track"]["id"]
                    track["audio_features"] = features_map.get(track_id, {})
            
            return tracks
            
        except SpotifyException as e:
            logger.error("Spotify API error getting tracks with features", error=str(e), playlist_id=playlist_id)
            raise
    
    async def search_tracks(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """Search for tracks"""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                self.executor,
                lambda: self.sp.search(q=query, type="track", limit=limit)
            )
            return results
        except SpotifyException as e:
            logger.error("Spotify API error searching tracks", error=str(e), query=query)
            raise
    
    async def get_track_details(self, track_id: str) -> Dict[str, Any]:
        """Get detailed track information including audio features"""
        try:
            loop = asyncio.get_event_loop()
            
            # Get track details and audio features concurrently
            track_task = loop.run_in_executor(
                self.executor,
                lambda: self.sp.track(track_id)
            )
            
            features_task = loop.run_in_executor(
                self.executor,
                lambda: self.sp.audio_features([track_id])[0]
            )
            
            track, features = await asyncio.gather(track_task, features_task)
            
            return {
                "track": track,
                "audio_features": features
            }
            
        except SpotifyException as e:
            logger.error("Spotify API error getting track details", error=str(e), track_id=track_id)
            raise
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 