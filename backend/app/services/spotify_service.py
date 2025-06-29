"""
Spotify API service for fetching user data, playlists, and track metadata
Updated to use genres and metadata instead of deprecated audio features API
"""
import asyncio
import spotipy
from typing import Optional, Dict, List, Any
import structlog
from spotipy.exceptions import SpotifyException

logger = structlog.get_logger()


class SpotifyService:
    """Service for interacting with Spotify Web API"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = spotipy.Spotify(auth=access_token)
    
    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current user profile"""
        try:
            loop = asyncio.get_event_loop()
            user = await loop.run_in_executor(None, self.client.current_user)
            return user
        except SpotifyException as e:
            logger.error("Failed to get current user", error=str(e))
            return None
    
    async def get_user_playlists(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's playlists"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.client.current_user_playlists(limit=limit, offset=offset)
            )
            return result.get('items', [])
        except SpotifyException as e:
            logger.error("Failed to get user playlists", error=str(e))
            return []
    
    async def get_playlist_details(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed playlist information"""
        try:
            loop = asyncio.get_event_loop()
            playlist = await loop.run_in_executor(
                None,
                lambda: self.client.playlist(playlist_id)
            )
            return playlist
        except SpotifyException as e:
            logger.error("Failed to get playlist details", playlist_id=playlist_id, error=str(e))
            return None
    
    async def get_playlist_tracks_with_metadata(self, playlist_id: str) -> List[Dict[str, Any]]:
        """
        Get playlist tracks with comprehensive metadata for mood analysis
        
        Returns list of tracks with:
        - Basic track info (name, duration, popularity, explicit)
        - Artist info with genres
        - Album info with release date
        """
        try:
            logger.info("Fetching playlist tracks with metadata", playlist_id=playlist_id)
            
            # Get basic playlist tracks
            loop = asyncio.get_event_loop()
            tracks_response = await loop.run_in_executor(
                None,
                lambda: self.client.playlist_tracks(playlist_id)
            )
            
            tracks = tracks_response.get('items', [])
            if not tracks:
                logger.warning("No tracks found in playlist", playlist_id=playlist_id)
                return []
            
            # Extract track metadata with genre information
            enriched_tracks = []
            
            for item in tracks:
                track = item.get('track')
                if not track or track.get('type') != 'track':
                    continue
                
                try:
                    # Get primary artist info (with genres)
                    primary_artist = track['artists'][0] if track['artists'] else None
                    artist_genres = []
                    artist_name = "Unknown Artist"
                    artist_popularity = 0
                    artist_followers = 0
                    
                    if primary_artist:
                        artist_name = primary_artist.get('name', 'Unknown Artist')
                        
                        # Get detailed artist info (including genres)
                        artist_details = await loop.run_in_executor(
                            None,
                            lambda: self.client.artist(primary_artist['id'])
                        )
                        
                        if artist_details:
                            artist_genres = artist_details.get('genres', [])
                            artist_popularity = artist_details.get('popularity', 0)
                            artist_followers = artist_details.get('followers', {}).get('total', 0)
                    
                    # Get album info
                    album = track.get('album', {})
                    album_name = album.get('name', 'Unknown Album')
                    release_date = album.get('release_date', '')
                    
                    # Calculate release year for decade analysis
                    release_year = None
                    if release_date:
                        try:
                            release_year = int(release_date.split('-')[0])
                        except (ValueError, IndexError):
                            pass
                    
                    # Create enriched track data
                    track_data = {
                        # Basic track info
                        'id': track.get('id'),
                        'name': track.get('name', 'Unknown Track'),
                        'duration_ms': track.get('duration_ms', 0),
                        'popularity': track.get('popularity', 0),
                        'explicit': track.get('explicit', False),
                        'preview_url': track.get('preview_url'),
                        
                        # Artist info with genres (key for mood analysis)
                        'artist': artist_name,
                        'artist_id': primary_artist.get('id') if primary_artist else None,
                        'genres': artist_genres,  # Most important for mood classification
                        'artist_popularity': artist_popularity,
                        'artist_followers': artist_followers,
                        
                        # Album info
                        'album': album_name,
                        'album_id': album.get('id'),
                        'release_date': release_date,
                        'release_year': release_year,
                        
                        # Additional metadata for analysis
                        'track_number': track.get('track_number'),
                        'disc_number': track.get('disc_number'),
                        'is_local': track.get('is_local', False),
                        
                        # Spotify URLs
                        'spotify_url': track.get('external_urls', {}).get('spotify'),
                        'uri': track.get('uri'),
                        
                        # All artists (for collaborations)
                        'all_artists': [a.get('name') for a in track.get('artists', [])],
                    }
                    
                    enriched_tracks.append(track_data)
                    logger.debug("Enriched track data", 
                               track_name=track_data['name'],
                               artist=track_data['artist'],
                               genres=track_data['genres'])
                    
                except Exception as e:
                    logger.warning("Failed to enrich track data", 
                                 track_id=track.get('id'), 
                                 error=str(e))
                    continue
            
            logger.info("Successfully fetched playlist tracks with metadata", 
                       playlist_id=playlist_id,
                       total_tracks=len(enriched_tracks))
            
            return enriched_tracks
            
        except SpotifyException as e:
            logger.error("Failed to get playlist tracks with metadata", 
                        playlist_id=playlist_id, 
                        error=str(e))
            return []
        except Exception as e:
            logger.error("Unexpected error getting playlist tracks", 
                        playlist_id=playlist_id, 
                        error=str(e))
            return []
    
    async def search_tracks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for tracks"""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.client.search(q=query, type='track', limit=limit)
            )
            return results.get('tracks', {}).get('items', [])
        except SpotifyException as e:
            logger.error("Failed to search tracks", query=query, error=str(e))
            return []
    
    async def get_artist_details(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed artist information including genres"""
        try:
            loop = asyncio.get_event_loop()
            artist = await loop.run_in_executor(
                None,
                lambda: self.client.artist(artist_id)
            )
            return artist
        except SpotifyException as e:
            logger.error("Failed to get artist details", artist_id=artist_id, error=str(e))
            return None
    
    def is_token_valid(self) -> bool:
        """Check if the access token is still valid"""
        try:
            self.client.current_user()
            return True
        except SpotifyException:
            return False 