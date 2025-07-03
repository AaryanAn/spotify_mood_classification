"""
Lyrics Service for Genius API Integration
Handles fetching, caching, and processing song lyrics for mood analysis
"""
import asyncio
from typing import Dict, List, Any, Optional
import structlog
import re
import requests
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
        self.genius_token = None
        self.redis_client = None
        self._initialize_services()
        
    def _initialize_services(self):
        """Initialize Genius API and Redis clients"""
        try:
            # Initialize Genius API with direct requests
            genius_token = self.settings.genius_access_token
            if genius_token and genius_token.strip():
                self.genius_token = genius_token
                logger.info("Genius API token configured for direct API calls")
            else:
                logger.warning("Genius API token not provided or empty - lyrics analysis will be disabled")
                
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
        Fetch lyrics for a track with caching using official Genius API
        
        Args:
            track_name: Name of the track
            artist_name: Name of the artist
            track_id: Spotify track ID for caching
            
        Returns:
            Lyrics text or None if not found
        """
        if not self.genius_token:
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
            
            # Search for song on Genius using official API
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
        """Search for lyrics using official Genius API"""
        try:
            print(f'Searching for "{track_name}" by {artist_name}...')
            
            headers = {'Authorization': f'Bearer {self.genius_token}'}
            
            # Search for the song using official API
            search_url = 'https://api.genius.com/search'
            search_params = {
                'q': f'{track_name} {artist_name}'
            }
            
            response = requests.get(search_url, headers=headers, params=search_params, timeout=10)
            
            if response.status_code != 200:
                logger.warning("Genius API search failed", 
                             status_code=response.status_code, 
                             error=response.text)
                return None
            
            data = response.json()
            hits = data.get('response', {}).get('hits', [])
            
            if not hits:
                logger.info("No search results found")
                return None
            
            # Find the best match
            best_match = None
            for hit in hits:
                result = hit.get('result', {})
                song_title = result.get('title', '').lower()
                artist_name_result = result.get('primary_artist', {}).get('name', '').lower()
                
                # Simple matching - check if track and artist names are similar
                if (track_name.lower() in song_title or song_title in track_name.lower()) and \
                   (artist_name.lower() in artist_name_result or artist_name_result in artist_name.lower()):
                    best_match = result
                    break
            
            if not best_match:
                # If no exact match, use the first result
                best_match = hits[0].get('result', {})
            
            # Get the song URL to fetch lyrics
            song_url = best_match.get('url')
            if not song_url:
                logger.warning("No song URL found")
                return None
            
            # Fetch lyrics from the song page
            lyrics = self._scrape_lyrics_from_url(song_url)
            return lyrics
            
        except Exception as e:
            logger.warning("Genius API search failed", error=str(e))
            return None
    
    def _scrape_lyrics_from_url(self, song_url: str) -> Optional[str]:
        """Scrape lyrics from Genius song page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(song_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try different selectors for lyrics
            lyrics_selectors = [
                '[data-lyrics-container="true"]',
                '.lyrics',
                '[class*="Lyrics__Container"]',
                '.song_body-lyrics'
            ]
            
            lyrics_text = ""
            for selector in lyrics_selectors:
                lyrics_elements = soup.select(selector)
                if lyrics_elements:
                    for element in lyrics_elements:
                        lyrics_text += element.get_text(separator='\n') + '\n'
                    break
            
            if lyrics_text.strip():
                return lyrics_text.strip()
            
            # Fallback: search for any element containing lyrics-like content
            possible_lyrics = soup.find_all(['div', 'p'], string=re.compile(r'\[.*\]'))
            if possible_lyrics:
                for element in possible_lyrics:
                    parent = element.parent
                    if parent:
                        text = parent.get_text(separator='\n')
                        if len(text) > 100:  # Likely to be lyrics if it's long enough
                            return text
            
            return None
            
        except Exception as e:
            logger.warning("Error scraping lyrics", error=str(e))
            return None
    
    def _clean_track_name(self, track_name: str) -> str:
        """Clean track name for better search results"""
        # Remove common suffixes and prefixes
        patterns = [
            r'\s*-\s*Remastered.*$',
            r'\s*-\s*Remix.*$',
            r'\s*\(Remastered.*\)$',
            r'\s*\(Remix.*\)$',
            r'\s*\(feat\..*\)$',
            r'\s*\(ft\..*\)$',
            r'\s*\(Live.*\)$',
            r'\s*\(Acoustic.*\)$',
        ]
        
        cleaned = track_name
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _clean_artist_name(self, artist_name: str) -> str:
        """Clean artist name for better search results"""
        # Remove common suffixes
        patterns = [
            r'\s*feat\..*$',
            r'\s*ft\..*$',
            r'\s*featuring.*$',
            r'\s*&.*$',
        ]
        
        cleaned = artist_name
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _process_lyrics(self, raw_lyrics: str) -> str:
        """Process and clean raw lyrics"""
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
    
    async def get_batch_lyrics(self, tracks: List[Dict[str, Any]], max_concurrent: int = 2) -> Dict[str, str]:
        """
        Fetch lyrics for multiple tracks concurrently (reduced concurrency for stability)
        
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
        return self.genius_token is not None 