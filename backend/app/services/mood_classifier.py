"""
Genre and Metadata-Based Mood Classification Service
Since Spotify's audio features API was deprecated (Nov 2024), this classifier uses:
- Artist genres
- Track metadata (popularity, duration, release year, explicit content)
- Artist popularity and follower metrics
- Text analysis of track/artist names
"""
import asyncio
from typing import Dict, List, Any, Optional
import structlog
import re
from collections import Counter
from datetime import datetime

logger = structlog.get_logger()


class MoodClassifier:
    """Mood classifier using genres, metadata, and text analysis"""
    
    def __init__(self):
        self.model_version = "genre-metadata-v1.0"
        
        # Genre to mood mapping
        self.genre_mood_map = {
            # Happy/Upbeat genres
            'pop': {'happy': 0.8, 'upbeat': 0.9, 'energetic': 0.6},
            'dance': {'upbeat': 0.9, 'energetic': 0.8, 'happy': 0.7},
            'funk': {'upbeat': 0.8, 'energetic': 0.7, 'happy': 0.6},
            'disco': {'upbeat': 0.9, 'happy': 0.8, 'energetic': 0.6},
            'reggae': {'calm': 0.7, 'happy': 0.6, 'upbeat': 0.5},
            'afrobeat': {'upbeat': 0.8, 'energetic': 0.7, 'happy': 0.8},
            
            # Energetic genres
            'rock': {'energetic': 0.8, 'upbeat': 0.6, 'angry': 0.4},
            'punk': {'energetic': 0.9, 'angry': 0.7, 'upbeat': 0.5},
            'metal': {'energetic': 0.9, 'angry': 0.8, 'aggressive': 0.9},
            'hard rock': {'energetic': 0.8, 'upbeat': 0.6, 'angry': 0.5},
            'electronic': {'energetic': 0.7, 'upbeat': 0.8, 'happy': 0.5},
            'edm': {'energetic': 0.9, 'upbeat': 0.8, 'happy': 0.6},
            'dubstep': {'energetic': 0.9, 'aggressive': 0.7, 'upbeat': 0.6},
            'techno': {'energetic': 0.8, 'upbeat': 0.7, 'hypnotic': 0.6},
            'house': {'upbeat': 0.8, 'energetic': 0.7, 'happy': 0.6},
            
            # Calm/Chill genres
            'ambient': {'calm': 0.9, 'peaceful': 0.8, 'meditative': 0.7},
            'chillout': {'calm': 0.8, 'relaxed': 0.8, 'peaceful': 0.6},
            'lo-fi': {'calm': 0.8, 'melancholic': 0.5, 'peaceful': 0.7},
            'new age': {'calm': 0.9, 'peaceful': 0.8, 'meditative': 0.8},
            'meditation': {'calm': 0.9, 'peaceful': 0.9, 'meditative': 0.9},
            
            # Sad/Melancholic genres
            'blues': {'sad': 0.8, 'melancholic': 0.9, 'soulful': 0.8},
            'folk': {'melancholic': 0.6, 'calm': 0.6, 'nostalgic': 0.7},
            'indie folk': {'melancholic': 0.7, 'calm': 0.6, 'introspective': 0.8},
            'shoegaze': {'melancholic': 0.8, 'dreamy': 0.7, 'introspective': 0.6},
            'emo': {'sad': 0.8, 'melancholic': 0.8, 'emotional': 0.9},
            'gothic': {'melancholic': 0.8, 'dark': 0.9, 'sad': 0.7},
            
            # Romantic genres
            'r&b': {'romantic': 0.8, 'sensual': 0.7, 'smooth': 0.8},
            'soul': {'romantic': 0.7, 'emotional': 0.8, 'soulful': 0.9},
            'neo soul': {'romantic': 0.8, 'sensual': 0.8, 'smooth': 0.7},
            'jazz': {'romantic': 0.6, 'sophisticated': 0.8, 'smooth': 0.7},
            'smooth jazz': {'romantic': 0.7, 'calm': 0.7, 'smooth': 0.9},
            'bossa nova': {'romantic': 0.8, 'calm': 0.7, 'sophisticated': 0.6},
            
            # Aggressive/Angry genres
            'hardcore': {'angry': 0.9, 'aggressive': 0.9, 'energetic': 0.8},
            'death metal': {'angry': 0.9, 'aggressive': 0.9, 'dark': 0.8},
            'thrash metal': {'angry': 0.8, 'aggressive': 0.8, 'energetic': 0.9},
            'rap': {'energetic': 0.7, 'confident': 0.8, 'upbeat': 0.6},
            'trap': {'energetic': 0.8, 'aggressive': 0.6, 'confident': 0.7},
            'drill': {'aggressive': 0.8, 'dark': 0.7, 'energetic': 0.7},
            
            # Cultural/World genres
            'latin': {'upbeat': 0.8, 'energetic': 0.7, 'happy': 0.8},
            'salsa': {'upbeat': 0.9, 'energetic': 0.8, 'happy': 0.8},
            'reggaeton': {'upbeat': 0.8, 'energetic': 0.8, 'sensual': 0.6},
            'k-pop': {'upbeat': 0.8, 'energetic': 0.7, 'happy': 0.8},
            'bollywood': {'upbeat': 0.7, 'energetic': 0.6, 'dramatic': 0.8},
            
            # Alternative/Indie
            'indie': {'melancholic': 0.6, 'introspective': 0.7, 'alternative': 0.8},
            'alternative': {'melancholic': 0.5, 'energetic': 0.6, 'edgy': 0.7},
            'grunge': {'angry': 0.6, 'melancholic': 0.7, 'alternative': 0.8},
        }
        
        # Mood keywords for text analysis
        self.mood_keywords = {
            'happy': ['happy', 'joy', 'celebrate', 'party', 'fun', 'good', 'sunshine', 'bright', 'smile'],
            'sad': ['sad', 'cry', 'tear', 'lonely', 'hurt', 'pain', 'goodbye', 'miss', 'lost', 'broken'],
            'angry': ['angry', 'hate', 'rage', 'mad', 'fight', 'war', 'destroy', 'kill', 'revenge'],
            'romantic': ['love', 'heart', 'baby', 'kiss', 'forever', 'together', 'beautiful', 'darling', 'mine'],
            'energetic': ['power', 'energy', 'fire', 'strong', 'loud', 'fast', 'run', 'jump', 'wild'],
            'calm': ['calm', 'peace', 'quiet', 'still', 'gentle', 'soft', 'breathe', 'relax', 'zen'],
            'melancholic': ['blue', 'grey', 'rain', 'alone', 'empty', 'shadow', 'dream', 'yesterday'],
            'upbeat': ['up', 'high', 'fly', 'dance', 'move', 'groove', 'rhythm', 'beat', 'alive']
        }
    
    async def classify_playlist_mood(self, tracks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classify playlist mood using genres, metadata, and text analysis
        
        Args:
            tracks_data: List of track data with genres and metadata
            
        Returns:
            Dict with mood classification results
        """
        try:
            if not tracks_data:
                return self._create_default_result()
            
            mood_scores = Counter()
            total_tracks = len(tracks_data)
            
            # Analyze each track
            for track_data in tracks_data:
                track_moods = self._analyze_track_mood(track_data)
                
                # Add to overall mood scores
                for mood, score in track_moods.items():
                    mood_scores[mood] += score
            
            # Normalize scores
            for mood in mood_scores:
                mood_scores[mood] = mood_scores[mood] / total_tracks
            
            # Get primary mood and confidence
            if mood_scores:
                primary_mood = mood_scores.most_common(1)[0][0]
                confidence = min(mood_scores[primary_mood], 1.0)
            else:
                primary_mood = "neutral"
                confidence = 0.5
            
            # Create mood distribution
            mood_distribution = dict(mood_scores.most_common(8))
            
            # Ensure we have all 8 standard moods
            standard_moods = ['happy', 'sad', 'energetic', 'calm', 'angry', 'romantic', 'melancholic', 'upbeat']
            for mood in standard_moods:
                if mood not in mood_distribution:
                    mood_distribution[mood] = 0.0
            
            # Normalize distribution to sum to 1.0
            total_score = sum(mood_distribution.values())
            if total_score > 0:
                mood_distribution = {k: v/total_score for k, v in mood_distribution.items()}
            else:
                # Equal distribution if no scores
                mood_distribution = {k: 1.0/len(standard_moods) for k in standard_moods}
            
            logger.info("Mood classification completed", 
                       primary_mood=primary_mood, 
                       confidence=confidence,
                       tracks_analyzed=total_tracks)
            
            return {
                "primary_mood": primary_mood,
                "confidence": float(confidence),
                "mood_distribution": mood_distribution,
                "tracks_analyzed": total_tracks,
                "method": "genre-metadata-analysis"
            }
            
        except Exception as e:
            logger.error("Error in mood classification", error=str(e))
            return self._create_default_result()
    
    def _analyze_track_mood(self, track_data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze mood of a single track using all available data"""
        mood_scores = Counter()
        
        # 1. Genre-based analysis (primary method)
        genres = track_data.get('genres', [])
        if genres:
            for genre in genres:
                genre_lower = genre.lower()
                if genre_lower in self.genre_mood_map:
                    for mood, score in self.genre_mood_map[genre_lower].items():
                        mood_scores[mood] += score * 0.7  # Weight: 70%
        
        # 2. Text analysis of track and artist names
        track_name = track_data.get('name', '').lower()
        artist_name = track_data.get('artist', '').lower()
        album_name = track_data.get('album', '').lower()
        
        text_content = f"{track_name} {artist_name} {album_name}"
        
        for mood, keywords in self.mood_keywords.items():
            for keyword in keywords:
                if keyword in text_content:
                    mood_scores[mood] += 0.3  # Weight: 30% per keyword match
        
        # 3. Metadata-based inference
        duration_ms = track_data.get('duration_ms', 0)
        popularity = track_data.get('popularity', 50)
        explicit = track_data.get('explicit', False)
        
        # Duration analysis
        if duration_ms > 0:
            duration_minutes = duration_ms / 60000
            if duration_minutes < 2.5:  # Very short tracks often energetic
                mood_scores['energetic'] += 0.2
                mood_scores['upbeat'] += 0.2
            elif duration_minutes > 6:  # Long tracks often calm or melancholic
                mood_scores['calm'] += 0.1
                mood_scores['melancholic'] += 0.1
        
        # Popularity analysis
        if popularity > 80:  # Very popular tracks often happy/upbeat
            mood_scores['happy'] += 0.1
            mood_scores['upbeat'] += 0.1
        elif popularity < 30:  # Less popular tracks might be more melancholic/alternative
            mood_scores['melancholic'] += 0.1
        
        # Explicit content analysis
        if explicit:
            mood_scores['angry'] += 0.1
            mood_scores['energetic'] += 0.1
        
        return dict(mood_scores)
    
    def _create_default_result(self) -> Dict[str, Any]:
        """Create default mood classification result"""
        return {
            "primary_mood": "neutral",
            "confidence": 0.5,
            "mood_distribution": {
                'happy': 0.125, 'sad': 0.125, 'energetic': 0.125, 'calm': 0.125,
                'angry': 0.125, 'romantic': 0.125, 'melancholic': 0.125, 'upbeat': 0.125
            },
            "tracks_analyzed": 0,
            "method": "default"
        }
    
    def get_model_version(self) -> str:
        """Get current model version"""
        return self.model_version 