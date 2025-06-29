"""
Enhanced Mood Classification Service with Lyrics Analysis
Combines genre-metadata analysis with NLTK sentiment analysis of lyrics
"""
import asyncio
from typing import Dict, List, Any, Optional
import structlog
import re
from collections import Counter
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

from app.services.mood_classifier import MoodClassifier
from app.services.lyrics_service import LyricsService

logger = structlog.get_logger()


class EnhancedMoodClassifier(MoodClassifier):
    """Enhanced mood classifier with lyrics sentiment analysis"""
    
    def __init__(self):
        super().__init__()
        self.model_version = "enhanced-lyrics-v1.0"
        self.lyrics_service = LyricsService()
        self._initialize_nltk()
        
        # Enhanced mood keywords for lyrics analysis
        self.lyrics_mood_keywords = {
            'happy': [
                'happy', 'joy', 'celebrate', 'party', 'fun', 'good', 'sunshine', 'bright', 'smile',
                'laugh', 'cheer', 'excited', 'awesome', 'amazing', 'wonderful', 'fantastic',
                'euphoric', 'bliss', 'delight', 'uplifting', 'positive', 'elated', 'cheerful'
            ],
            'sad': [
                'sad', 'cry', 'tear', 'lonely', 'hurt', 'pain', 'goodbye', 'miss', 'lost', 'broken',
                'depressed', 'sorrow', 'grief', 'mourn', 'weep', 'despair', 'anguish', 'heartbreak',
                'devastated', 'miserable', 'gloomy', 'melancholy', 'blue', 'down'
            ],
            'angry': [
                'angry', 'hate', 'rage', 'mad', 'fight', 'war', 'destroy', 'kill', 'revenge',
                'furious', 'pissed', 'livid', 'outraged', 'hostile', 'aggressive', 'violent',
                'wrath', 'fury', 'enraged', 'irritated', 'annoyed', 'frustrated'
            ],
            'romantic': [
                'love', 'heart', 'baby', 'kiss', 'forever', 'together', 'beautiful', 'darling', 'mine',
                'romantic', 'passion', 'affection', 'adore', 'cherish', 'devoted', 'soulmate',
                'intimate', 'tender', 'sweet', 'loving', 'desire', 'romance', 'valentine'
            ],
            'energetic': [
                'power', 'energy', 'fire', 'strong', 'loud', 'fast', 'run', 'jump', 'wild',
                'pumped', 'intense', 'explosive', 'dynamic', 'vigorous', 'fierce', 'powerful',
                'electric', 'charged', 'hyped', 'adrenaline', 'boost', 'rush'
            ],
            'calm': [
                'calm', 'peace', 'quiet', 'still', 'gentle', 'soft', 'breathe', 'relax', 'zen',
                'serene', 'tranquil', 'peaceful', 'soothing', 'mellow', 'chill', 'laid-back',
                'smooth', 'easy', 'comfortable', 'restful', 'meditative', 'mindful'
            ],
            'melancholic': [
                'blue', 'grey', 'rain', 'alone', 'empty', 'shadow', 'dream', 'yesterday',
                'nostalgia', 'bittersweet', 'wistful', 'pensive', 'contemplative', 'reflective',
                'somber', 'subdued', 'thoughtful', 'introspective', 'distant', 'fading'
            ],
            'upbeat': [
                'up', 'high', 'fly', 'dance', 'move', 'groove', 'rhythm', 'beat', 'alive',
                'vibrant', 'lively', 'bouncy', 'peppy', 'spirited', 'animated', 'enthusiastic',
                'zippy', 'snappy', 'perky', 'buoyant', 'vivacious', 'zesty'
            ]
        }
        
        # Emotional intensifiers and modifiers
        self.intensifiers = [
            'very', 'really', 'extremely', 'incredibly', 'absolutely', 'totally',
            'completely', 'utterly', 'deeply', 'truly', 'so', 'too', 'quite'
        ]
        
        self.negations = [
            'not', 'no', 'never', 'none', 'nothing', 'nobody', 'nowhere',
            "don't", "won't", "can't", "shouldn't", "wouldn't", "couldn't"
        ]
    
    def _initialize_nltk(self):
        """Initialize NLTK components and download required data"""
        try:
            # Download required NLTK data
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            
            # Initialize sentiment analyzer
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            self.stop_words = set(stopwords.words('english'))
            
            logger.info("NLTK components initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize NLTK", error=str(e))
            self.sentiment_analyzer = None
    
    async def classify_playlist_mood_with_lyrics(self, tracks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enhanced mood classification using both genre-metadata and lyrics analysis
        
        Args:
            tracks_data: List of track data with genres and metadata
            
        Returns:
            Dict with enhanced mood classification results
        """
        try:
            if not tracks_data:
                return self._create_default_result()
            
            total_tracks = len(tracks_data)
            logger.info("Starting enhanced mood analysis with lyrics", total_tracks=total_tracks)
            
            # Step 1: Get base genre-metadata analysis
            base_analysis = await self.classify_playlist_mood(tracks_data)
            
            # Step 2: Fetch lyrics for all tracks
            lyrics_data = {}
            if self.lyrics_service.is_available():
                lyrics_data = await self._fetch_playlist_lyrics(tracks_data)
                logger.info("Lyrics fetched", tracks_with_lyrics=len(lyrics_data))
            
            # Step 3: Combine analysis methods
            if lyrics_data:
                combined_analysis = await self._combine_analyses(
                    tracks_data, base_analysis, lyrics_data
                )
                combined_analysis["method"] = "enhanced-lyrics-genre-metadata"
                combined_analysis["lyrics_coverage"] = len(lyrics_data) / total_tracks
            else:
                # Fallback to genre-metadata only
                combined_analysis = base_analysis
                combined_analysis["method"] = "genre-metadata-only"
                combined_analysis["lyrics_coverage"] = 0.0
            
            logger.info("Enhanced mood analysis completed",
                       primary_mood=combined_analysis["primary_mood"],
                       confidence=combined_analysis["confidence"],
                       method=combined_analysis["method"])
            
            return combined_analysis
            
        except Exception as e:
            logger.error("Error in enhanced mood classification", error=str(e))
            return self._create_default_result()
    
    async def _fetch_playlist_lyrics(self, tracks_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Fetch lyrics for all tracks in the playlist"""
        tracks_for_lyrics = []
        for track in tracks_data:
            tracks_for_lyrics.append({
                'id': track.get('id', ''),
                'name': track.get('name', ''),
                'artist': track.get('artist', '')
            })
        
        # Fetch lyrics with limited concurrency to respect API limits
        return await self.lyrics_service.get_batch_lyrics(tracks_for_lyrics, max_concurrent=2)
    
    async def _combine_analyses(self, tracks_data: List[Dict[str, Any]], 
                               base_analysis: Dict[str, Any], 
                               lyrics_data: Dict[str, str]) -> Dict[str, Any]:
        """Combine genre-metadata analysis with lyrics sentiment analysis"""
        
        # Get lyrics-based mood scores
        lyrics_mood_scores = await self._analyze_lyrics_mood(lyrics_data)
        
        # Weight the different analysis methods
        genre_weight = 0.6  # 60% weight for genre-metadata
        lyrics_weight = 0.4  # 40% weight for lyrics
        
        # If we have very few lyrics, increase genre weight
        lyrics_coverage = len(lyrics_data) / len(tracks_data)
        if lyrics_coverage < 0.3:  # Less than 30% lyrics coverage
            genre_weight = 0.8
            lyrics_weight = 0.2
        
        # Combine mood distributions
        combined_mood_scores = Counter()
        
        # Add weighted genre-metadata scores
        for mood, score in base_analysis["mood_distribution"].items():
            combined_mood_scores[mood] += score * genre_weight
        
        # Add weighted lyrics scores
        for mood, score in lyrics_mood_scores.items():
            combined_mood_scores[mood] += score * lyrics_weight
        
        # Normalize combined scores
        total_score = sum(combined_mood_scores.values())
        if total_score > 0:
            normalized_scores = {k: v/total_score for k, v in combined_mood_scores.items()}
        else:
            normalized_scores = base_analysis["mood_distribution"]
        
        # Determine primary mood and confidence
        if normalized_scores:
            primary_mood = max(normalized_scores, key=normalized_scores.get)
            confidence = min(normalized_scores[primary_mood], 1.0)
        else:
            primary_mood = base_analysis["primary_mood"]
            confidence = base_analysis["confidence"]
        
        return {
            "primary_mood": primary_mood,
            "confidence": float(confidence),
            "mood_distribution": normalized_scores,
            "tracks_analyzed": len(tracks_data),
            "analysis_components": {
                "genre_metadata_weight": genre_weight,
                "lyrics_weight": lyrics_weight,
                "lyrics_tracks": len(lyrics_data),
                "total_tracks": len(tracks_data)
            }
        }
    
    async def _analyze_lyrics_mood(self, lyrics_data: Dict[str, str]) -> Dict[str, float]:
        """Analyze mood from lyrics using NLTK sentiment analysis and keyword matching"""
        if not lyrics_data or not self.sentiment_analyzer:
            return {}
        
        mood_scores = Counter()
        total_tracks = len(lyrics_data)
        
        for track_id, lyrics in lyrics_data.items():
            if not lyrics:
                continue
                
            # Get track mood scores
            track_mood = self._analyze_single_lyrics(lyrics)
            
            # Add to overall scores
            for mood, score in track_mood.items():
                mood_scores[mood] += score
        
        # Normalize by number of tracks with lyrics
        if total_tracks > 0:
            normalized_scores = {mood: score/total_tracks for mood, score in mood_scores.items()}
        else:
            normalized_scores = {}
        
        return dict(normalized_scores)
    
    def _analyze_single_lyrics(self, lyrics: str) -> Dict[str, float]:
        """Analyze mood of individual song lyrics"""
        mood_scores = Counter()
        
        if not lyrics:
            return {}
        
        # Detect language (focus on English for now)
        try:
            lang = detect(lyrics)
            if lang != 'en':
                logger.debug("Non-English lyrics detected, using limited analysis", language=lang)
                return self._basic_keyword_analysis(lyrics)
        except LangDetectException:
            pass
        
        # 1. VADER Sentiment Analysis
        if self.sentiment_analyzer:
            sentiment_scores = self._get_vader_sentiment(lyrics)
            mood_scores.update(sentiment_scores)
        
        # 2. Enhanced keyword analysis
        keyword_scores = self._enhanced_keyword_analysis(lyrics)
        mood_scores.update(keyword_scores)
        
        # 3. Structural analysis (chorus emphasis, etc.)
        structural_scores = self._analyze_lyrics_structure(lyrics)
        mood_scores.update(structural_scores)
        
        return dict(mood_scores)
    
    def _get_vader_sentiment(self, lyrics: str) -> Dict[str, float]:
        """Use VADER sentiment analyzer to get mood scores"""
        sentiment = self.sentiment_analyzer.polarity_scores(lyrics)
        
        mood_scores = {}
        
        # Map VADER scores to our mood categories
        compound = sentiment['compound']
        positive = sentiment['pos']
        negative = sentiment['neg']
        neutral = sentiment['neu']
        
        # Positive emotions
        if compound > 0.1:
            mood_scores['happy'] = positive * 0.8
            mood_scores['upbeat'] = positive * 0.6
            if compound > 0.5:
                mood_scores['energetic'] = positive * 0.4
        
        # Negative emotions
        if compound < -0.1:
            mood_scores['sad'] = negative * 0.8
            mood_scores['melancholic'] = negative * 0.6
            if compound < -0.5:
                mood_scores['angry'] = negative * 0.4
        
        # Neutral/calm
        if -0.1 <= compound <= 0.1 and neutral > 0.5:
            mood_scores['calm'] = neutral * 0.6
        
        return mood_scores
    
    def _enhanced_keyword_analysis(self, lyrics: str) -> Dict[str, float]:
        """Enhanced keyword analysis with context and intensifiers"""
        mood_scores = Counter()
        
        # Tokenize and clean lyrics
        words = word_tokenize(lyrics.lower())
        words = [word for word in words if word.isalpha() and word not in self.stop_words]
        
        for i, word in enumerate(words):
            # Check if word is a mood keyword
            for mood, keywords in self.lyrics_mood_keywords.items():
                if word in keywords:
                    score = 1.0
                    
                    # Check for intensifiers before the word
                    if i > 0 and words[i-1] in self.intensifiers:
                        score *= 1.5
                    
                    # Check for negations
                    negated = False
                    for j in range(max(0, i-3), i):
                        if words[j] in self.negations:
                            negated = True
                            break
                    
                    if negated:
                        # Flip to opposite mood or reduce score
                        score *= -0.5
                        if mood == 'happy':
                            mood_scores['sad'] += abs(score)
                        elif mood == 'sad':
                            mood_scores['happy'] += abs(score)
                        elif mood == 'energetic':
                            mood_scores['calm'] += abs(score)
                        elif mood == 'calm':
                            mood_scores['energetic'] += abs(score)
                    else:
                        mood_scores[mood] += score
        
        return dict(mood_scores)
    
    def _basic_keyword_analysis(self, lyrics: str) -> Dict[str, float]:
        """Basic keyword analysis for non-English lyrics"""
        mood_scores = Counter()
        lyrics_lower = lyrics.lower()
        
        # Use basic emotion words that might work across languages
        basic_patterns = {
            'happy': ['happy', 'amor', 'love', 'joy', 'feliz'],
            'sad': ['sad', 'triste', 'cry', 'dolor', 'pain'],
            'energetic': ['energy', 'power', 'fuerte', 'strong'],
            'romantic': ['love', 'amor', 'heart', 'corazón']
        }
        
        for mood, patterns in basic_patterns.items():
            for pattern in patterns:
                if pattern in lyrics_lower:
                    mood_scores[mood] += 0.5
        
        return dict(mood_scores)
    
    def _analyze_lyrics_structure(self, lyrics: str) -> Dict[str, float]:
        """Analyze structural elements of lyrics for mood cues"""
        mood_scores = Counter()
        
        # Count repetitive elements (often happy/energetic)
        lines = lyrics.split('\n')
        repeated_lines = 0
        unique_lines = set()
        
        for line in lines:
            clean_line = line.strip().lower()
            if clean_line and clean_line in unique_lines:
                repeated_lines += 1
            unique_lines.add(clean_line)
        
        if repeated_lines > 2:  # Repetitive structure suggests upbeat/energetic
            mood_scores['upbeat'] += 0.3
            mood_scores['energetic'] += 0.2
        
        # Analyze punctuation patterns
        exclamation_count = lyrics.count('!')
        question_count = lyrics.count('?')
        
        if exclamation_count > 2:
            mood_scores['energetic'] += 0.2
            mood_scores['happy'] += 0.1
        
        if question_count > exclamation_count:
            mood_scores['melancholic'] += 0.1
            mood_scores['contemplative'] = mood_scores.get('contemplative', 0) + 0.2
        
        return dict(mood_scores)
    
    def _create_default_result(self) -> Dict[str, Any]:
        """Create default enhanced mood classification result"""
        result = super()._create_default_result()
        result["method"] = "enhanced-default"
        result["lyrics_coverage"] = 0.0
        return result 