"""
Mood classification service using machine learning
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Any, Tuple
import structlog
import joblib
import os
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = structlog.get_logger()


class MoodClassifier:
    """Machine learning model for classifying playlist moods"""
    
    # Mood categories based on valence and energy
    MOOD_CATEGORIES = {
        "happy": {"valence": (0.6, 1.0), "energy": (0.6, 1.0)},
        "energetic": {"valence": (0.4, 0.8), "energy": (0.7, 1.0)},
        "calm": {"valence": (0.4, 0.8), "energy": (0.0, 0.4)},
        "sad": {"valence": (0.0, 0.4), "energy": (0.0, 0.6)},
        "angry": {"valence": (0.0, 0.5), "energy": (0.6, 1.0)},
        "romantic": {"valence": (0.5, 0.9), "energy": (0.0, 0.5)},
        "melancholic": {"valence": (0.2, 0.6), "energy": (0.2, 0.5)},
        "upbeat": {"valence": (0.7, 1.0), "energy": (0.5, 0.9)},
    }
    
    MOOD_DESCRIPTIONS = {
        "happy": "Joyful and positive music that lifts your spirits",
        "energetic": "High-energy music perfect for workouts or motivation",
        "calm": "Peaceful and relaxing music for unwinding",
        "sad": "Melancholic music that touches deep emotions",
        "angry": "Intense and aggressive music expressing frustration",
        "romantic": "Tender and loving music for intimate moments",
        "melancholic": "Bittersweet music with a touch of nostalgia",
        "upbeat": "Cheerful and lively music that makes you want to dance",
    }
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.model_version = "1.0.0"
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize or load the mood classification model"""
        try:
            model_path = Path("ml/models")
            model_path.mkdir(parents=True, exist_ok=True)
            
            model_file = model_path / "mood_classifier.pkl"
            scaler_file = model_path / "mood_scaler.pkl"
            
            if model_file.exists() and scaler_file.exists():
                # Load existing model
                self.model = joblib.load(model_file)
                self.scaler = joblib.load(scaler_file)
                logger.info("Loaded existing mood classification model")
            else:
                # Create and train new model
                self._create_model()
                logger.info("Created new mood classification model")
                
        except Exception as e:
            logger.error("Failed to initialize mood classifier", error=str(e))
            # Fallback to rule-based classification
            self.model = None
            self.scaler = None
    
    def _create_model(self):
        """Create and train a new mood classification model"""
        try:
            # Generate synthetic training data based on mood categories
            X, y = self._generate_training_data()
            
            # Initialize scaler
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)
            
            # Train Random Forest classifier
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            self.model.fit(X_scaled, y)
            
            # Save model and scaler
            model_path = Path("ml/models")
            joblib.dump(self.model, model_path / "mood_classifier.pkl")
            joblib.dump(self.scaler, model_path / "mood_scaler.pkl")
            
            logger.info("Trained and saved new mood classification model")
            
        except Exception as e:
            logger.error("Failed to create mood classification model", error=str(e))
            raise
    
    def _generate_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Generate synthetic training data for mood classification"""
        np.random.seed(42)
        
        features_list = []
        labels_list = []
        
        # Generate samples for each mood category
        for mood, ranges in self.MOOD_CATEGORIES.items():
            n_samples = 200  # Number of samples per mood
            
            for _ in range(n_samples):
                # Generate features within mood-specific ranges
                valence = np.random.uniform(ranges["valence"][0], ranges["valence"][1])
                energy = np.random.uniform(ranges["energy"][0], ranges["energy"][1])
                
                # Generate correlated features
                danceability = valence * 0.7 + energy * 0.3 + np.random.normal(0, 0.1)
                danceability = np.clip(danceability, 0, 1)
                
                acousticness = 1 - energy + np.random.normal(0, 0.15)
                acousticness = np.clip(acousticness, 0, 1)
                
                tempo = 60 + energy * 140 + np.random.normal(0, 20)
                tempo = np.clip(tempo, 60, 200)
                
                loudness = -60 + energy * 50 + np.random.normal(0, 5)
                loudness = np.clip(loudness, -60, 0)
                
                speechiness = np.random.uniform(0, 0.3)
                instrumentalness = np.random.uniform(0, 0.8)
                liveness = np.random.uniform(0, 0.3)
                
                features = [
                    valence, energy, danceability, acousticness, tempo,
                    loudness, speechiness, instrumentalness, liveness
                ]
                
                features_list.append(features)
                labels_list.append(mood)
        
        return np.array(features_list), np.array(labels_list)
    
    async def classify_playlist_mood(self, tracks_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Classify the mood of a playlist based on track audio features"""
        try:
            if not tracks_data:
                return {"primary_mood": "unknown", "confidence": 0.0, "mood_distribution": {}}
            
            # Extract features
            features = self._extract_features(tracks_data)
            
            if self.model and self.scaler:
                # Use ML model for classification
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor,
                    self._classify_with_model,
                    features
                )
            else:
                # Use rule-based classification as fallback
                result = self._classify_with_rules(features)
            
            return result
            
        except Exception as e:
            logger.error("Failed to classify playlist mood", error=str(e))
            return {"primary_mood": "unknown", "confidence": 0.0, "mood_distribution": {}}
    
    def _extract_features(self, tracks_data: List[Dict[str, Any]]) -> np.ndarray:
        """Extract and aggregate features from track data"""
        if not tracks_data:
            return np.array([])
        
        # Calculate average features across all tracks
        feature_names = [
            "valence", "energy", "danceability", "acousticness", "tempo",
            "loudness", "speechiness", "instrumentalness", "liveness"
        ]
        
        aggregated_features = []
        for feature in feature_names:
            values = [track.get(feature, 0) for track in tracks_data if track.get(feature) is not None]
            avg_value = np.mean(values) if values else 0
            aggregated_features.append(avg_value)
        
        return np.array(aggregated_features).reshape(1, -1)
    
    def _classify_with_model(self, features: np.ndarray) -> Dict[str, Any]:
        """Classify mood using the trained ML model"""
        try:
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Get predictions and probabilities
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Create mood distribution
            mood_distribution = {}
            for i, mood in enumerate(self.model.classes_):
                mood_distribution[mood] = float(probabilities[i])
            
            # Get confidence (max probability)
            confidence = float(np.max(probabilities))
            
            return {
                "primary_mood": prediction,
                "confidence": confidence,
                "mood_distribution": mood_distribution
            }
            
        except Exception as e:
            logger.error("ML model classification failed", error=str(e))
            # Fallback to rule-based
            return self._classify_with_rules(features)
    
    def _classify_with_rules(self, features: np.ndarray) -> Dict[str, Any]:
        """Classify mood using rule-based approach"""
        if features.size == 0:
            return {"primary_mood": "unknown", "confidence": 0.0, "mood_distribution": {}}
        
        valence, energy = features[0][0], features[0][1]
        
        # Rule-based classification
        if valence > 0.7 and energy > 0.7:
            primary_mood = "happy"
        elif valence > 0.6 and energy > 0.6:
            primary_mood = "upbeat"
        elif energy > 0.7:
            primary_mood = "energetic"
        elif valence < 0.4 and energy < 0.5:
            primary_mood = "sad"
        elif valence < 0.5 and energy > 0.6:
            primary_mood = "angry"
        elif valence > 0.5 and energy < 0.4:
            primary_mood = "romantic"
        elif energy < 0.4:
            primary_mood = "calm"
        else:
            primary_mood = "melancholic"
        
        # Create mock distribution with primary mood having high confidence
        mood_distribution = {mood: 0.1 for mood in self.MOOD_CATEGORIES.keys()}
        mood_distribution[primary_mood] = 0.8
        
        return {
            "primary_mood": primary_mood,
            "confidence": 0.8,
            "mood_distribution": mood_distribution
        }
    
    def get_supported_moods(self) -> List[str]:
        """Get list of supported mood categories"""
        return list(self.MOOD_CATEGORIES.keys())
    
    def get_mood_descriptions(self) -> Dict[str, str]:
        """Get descriptions for mood categories"""
        return self.MOOD_DESCRIPTIONS.copy()
    
    def get_model_version(self) -> str:
        """Get model version"""
        return self.model_version
    
    def __del__(self):
        """Cleanup executor on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False) 