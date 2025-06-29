"""
Lyrics Service for Genius API Integration
Handles fetching, caching, and processing song lyrics for mood analysis
"""
import asyncio
from typing import Dict, List, Any, Optional
import structlog
import re
import lyricsgenius
from bs4 import BeautifulSoup
import redis
import json
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from app.utils.config import get_settings

logger = structlog.get_logger()


class LyricsService:
    """Service for fetching and processing song lyrics from Genius API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.genius = None
        self.redis_client = None
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize Genius API and Redis clients"""
        try:
            # Initialize Genius API
            genius_token = self.settings.genius_access_token
            if genius_token:
                self.genius = lyricsgenius.Genius(genius_token)
                self.genius.timeout = 10  # 10 second timeout
                self.genius.sleep_time = 0.2  # Rate limiting
                self.genius.remove_section_headers = True
                self.genius.skip_non_songs = True
                self.genius.excluded_terms = ["(Remix)", "(Live)", "(Acoustic)", "(Instrumental)"]
                logger.info("Genius API client initialized")
            else:
                logger.warning("Genius API token not provided, lyrics analysis disabled")
                
            # Initialize Redis for caching
            try:
                # Parse Redis URL or use defaults
                if self.settings.redis_url.startswith("redis://"):
                    self.redis_client = redis.from_url(self.settings.redis_url, decode_responses=True)
                else:
                    self.redis_client = redis.Redis(
                        host="localhost",
                        port=6379,
                        db=self.settings.redis_db,
                        decode_responses=True
                    )
                self.redis_client.ping()  # Test connection
                logger.info("Redis client connected for lyrics caching")
            except Exception as e:
                logger.warning("Redis connection failed, lyrics caching disabled", error=str(e))
                self.redis_client = None
                
        except Exception as e:
            logger.error("Failed to initialize lyrics service", error=str(e))
    
    async def get_lyrics(self, track_name: str, artist_name: str, track_id: str) -> Optional[str]:
        """
        Fetch lyrics for a track with caching
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            track_id: Spotify track ID for caching
            
        Returns:
            Lyrics text or None if not found
        """
        if not self.genius:
            return None
            
        cache_key = f"lyrics:{track_id}"
        
        try:
            # Check cache first
            cached_lyrics = await self._get_cached_lyrics(cache_key)
            if cached_lyrics is not None:
                return cached_lyrics
            
            # Clean track and artist names for better search
            clean_track = self._clean_track_name(track_name)
            clean_artist = self._clean_artist_name(artist_name)
            
            # Search for song on Genius
            logger.info("Fetching lyrics from Genius", 
                       track=clean_track, 
                       artist=clean_artist,
                       track_id=track_id)
                       
            # Run Genius API call in thread pool to avoid blocking
            lyrics = await asyncio.get_event_loop().run_in_executor(
                None, 
                self._search_lyrics_sync, 
                clean_track, 
                clean_artist
            )
            
            if lyrics:
                # Process and clean lyrics
                processed_lyrics = self._process_lyrics(lyrics)
                
                # Cache the result
                await self._cache_lyrics(cache_key, processed_lyrics)
                
                logger.info("Successfully fetched lyrics", 
                           track_id=track_id,
                           lyrics_length=len(processed_lyrics))
                return processed_lyrics
            else:
                # Cache empty result to avoid repeated API calls
                await self._cache_lyrics(cache_key, "")
                logger.info("No lyrics found", track=clean_track, artist=clean_artist)
                return None
                
        except Exception as e:
            logger.error("Error fetching lyrics", 
                        track=track_name,
                        artist=artist_name,
                        error=str(e))
            return None
    
    def _search_lyrics_sync(self, track_name: str, artist_name: str) -> Optional[str]:
        """Synchronous lyrics search for thread pool execution"""
        try:
            # Try artist and track name first
            song = self.genius.search_song(track_name, artist_name)
            if song and song.lyrics:
                return song.lyrics
            
            # Fallback: search by track name only
            song = self.genius.search_song(track_name)
            if song and song.lyrics and artist_name.lower() in song.artist.lower():
                return song.lyrics
                
            return None
            
        except Exception as e:
            logger.warning("Genius API search failed", error=str(e))
            return None
    
    def _clean_track_name(self, track_name: str) -> str:
        """Clean track name for better search results"""
        # Remove common suffixes that interfere with search
        patterns = [
            r'\s*\(feat\..*?\)',  # (feat. Artist)
            r'\s*\(ft\..*?\)',    # (ft. Artist)
            r'\s*\(with.*?\)',    # (with Artist)
            r'\s*\(.*?remix.*?\)', # (Remix)
            r'\s*\(.*?version.*?\)', # (Version)
            r'\s*\(.*?edit.*?\)',   # (Edit)
            r'\s*\-.*?remix',       # - Remix
            r'\s*\-.*?version',     # - Version
        ]
        
        cleaned = track_name
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _clean_artist_name(self, artist_name: str) -> str:
        """Clean artist name for better search results"""
        # Remove featuring artists, keep primary artist
        patterns = [
            r'\s*feat\..*',
            r'\s*ft\..*',
            r'\s*&.*',
            r'\s*,.*',
        ]
        
        cleaned = artist_name
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _process_lyrics(self, raw_lyrics: str) -> str:
        """Process and clean raw lyrics from Genius"""
        if not raw_lyrics:
            return ""
        
        # Remove HTML if present
        soup = BeautifulSoup(raw_lyrics, 'html.parser')
        lyrics = soup.get_text()
        
        # Remove Genius-specific annotations
        lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove [Verse 1], [Chorus], etc.
        lyrics = re.sub(r'^\d+$', '', lyrics, flags=re.MULTILINE)  # Remove line numbers
        lyrics = re.sub(r'Embed$', '', lyrics)  # Remove "Embed" footer
        lyrics = re.sub(r'You might also like', '', lyrics)  # Remove suggestions
        
        # Clean whitespace
        lyrics = re.sub(r'\n\s*\n', '\n', lyrics)  # Remove empty lines
        lyrics = lyrics.strip()
        
        return lyrics
    
    async def _get_cached_lyrics(self, cache_key: str) -> Optional[str]:
        """Get lyrics from Redis cache"""
        if not self.redis_client:
            return None
            
        try:
            cached = self.redis_client.get(cache_key)
            if cached is not None:
                logger.debug("Lyrics cache hit", cache_key=cache_key)
                return cached if cached else None  # Empty string means no lyrics found
            return None
        except Exception as e:
            logger.warning("Redis cache read failed", error=str(e))
            return None
    
    async def _cache_lyrics(self, cache_key: str, lyrics: str, expire_hours: int = 24*7) -> None:
        """Cache lyrics in Redis with expiration"""
        if not self.redis_client:
            return
            
        try:
            # Cache for 1 week
            self.redis_client.setex(cache_key, expire_hours * 3600, lyrics)
            logger.debug("Lyrics cached", cache_key=cache_key, lyrics_length=len(lyrics))
        except Exception as e:
            logger.warning("Redis cache write failed", error=str(e))
    
    def detect_language(self, text: str) -> str:
        """Detect language of lyrics text"""
        try:
            return detect(text)
        except LangDetectException:
            return "unknown"
    
    async def get_batch_lyrics(self, tracks: List[Dict[str, Any]], max_concurrent: int = 3) -> Dict[str, str]:
        """
        Fetch lyrics for multiple tracks concurrently
        
        Args:
            tracks: List of track dictionaries with 'id', 'name', 'artist'
            max_concurrent: Maximum concurrent requests to Genius API
            
        Returns:
            Dictionary mapping track_id to lyrics
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_single(track):
            async with semaphore:
                lyrics = await self.get_lyrics(
                    track.get('name', ''),
                    track.get('artist', ''),
                    track.get('id', '')
                )
                return track.get('id'), lyrics
        
        # Execute all requests concurrently
        tasks = [fetch_single(track) for track in tracks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        lyrics_dict = {}
        for result in results:
            if isinstance(result, tuple):
                track_id, lyrics = result
                if lyrics:
                    lyrics_dict[track_id] = lyrics
            else:
                logger.warning("Batch lyrics fetch error", error=str(result))
        
        logger.info("Batch lyrics fetch completed", 
                   total_tracks=len(tracks),
                   lyrics_found=len(lyrics_dict))
        
        return lyrics_dict
    
    def is_available(self) -> bool:
        """Check if lyrics service is properly configured and available"""
        return self.genius is not None 