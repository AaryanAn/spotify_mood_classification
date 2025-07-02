// User types
export interface User {
  id: string;
  display_name: string;
  email?: string;
  country?: string;
  followers?: number;
  spotify_url?: string;
}

// Authentication types
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginResponse {
  auth_url: string;
  state: string;
}

// Spotify playlist types
export interface SpotifyImage {
  url: string;
  height: number;
  width: number;
}

export interface SpotifyPlaylist {
  id: string;
  name: string;
  description?: string;
  public: boolean;
  collaborative: boolean;
  tracks: {
    total: number;
  };
  images: SpotifyImage[];
  external_urls: {
    spotify: string;
  };
  owner: {
    id: string;
    display_name: string;
  };
}

export interface SpotifyPlaylistsResponse {
  items: SpotifyPlaylist[];
  total: number;
  limit: number;
  offset: number;
  next?: string;
  previous?: string;
}

// Track types
export interface AudioFeatures {
  acousticness: number;
  danceability: number;
  energy: number;
  instrumentalness: number;
  liveness: number;
  loudness: number;
  speechiness: number;
  tempo: number;
  valence: number;
  key: number;
  mode: number;
  time_signature: number;
}

export interface Track {
  id: string;
  name: string;
  artist: string;
  album: string;
  duration_ms: number;
  popularity?: number;
  explicit: boolean;
  spotify_url: string;
  preview_url?: string;
  position: number;
  audio_features: AudioFeatures;
}

export interface PlaylistTracksResponse {
  playlist_id: string;
  playlist_name: string;
  tracks: Track[];
}

// Mood analysis types
export type MoodType = 
  | 'happy' 
  | 'sad' 
  | 'energetic' 
  | 'calm' 
  | 'angry' 
  | 'romantic' 
  | 'melancholic' 
  | 'upbeat';

export interface MoodDistribution {
  [key: string]: number;
}

export interface MoodAnalysis {
  playlist_id: string;
  primary_mood: MoodType;
  mood_confidence: number;
  mood_distribution: MoodDistribution;
  tracks_analyzed: number;
  created_at: string;
  analysis_method: string;
  // Legacy audio features (direct fields for backward compatibility)
  avg_valence: number;
  avg_energy: number;
  avg_danceability: number;
  // Optional nested structures for enhanced data
  audio_features?: {
    avg_valence: number;
    avg_energy: number;
    avg_danceability: number;
    avg_acousticness?: number;
    avg_tempo?: number;
  };
  metadata?: {
    tracks_analyzed: number;
    model_version: string;
    analysis_duration_ms: number;
    analyzed_at: string;
  };
}

export interface MoodAnalysisHistory {
  playlist_id: string;
  playlist_name: string;
  playlist_image?: string;
  primary_mood: MoodType;
  mood_confidence: number;
  tracks_analyzed: number;
  analyzed_at: string;
  analysis_duration_ms: number;
}

export interface MoodAnalysisHistoryResponse {
  history: MoodAnalysisHistory[];
  total: number;
  limit: number;
  offset: number;
}

// API response types
export interface ApiError {
  error: string;
  status_code: number;
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  services?: {
    [key: string]: {
      status: 'healthy' | 'unhealthy';
      message: string;
    };
  };
}

// Component props types
export interface PlaylistCardProps {
  playlist: SpotifyPlaylist;
  onSelect: (playlist: SpotifyPlaylist) => void;
  isSelected?: boolean;
}

export interface MoodVisualizationProps {
  analysis: MoodAnalysis;
  className?: string;
}

export interface MoodBadgeProps {
  mood: MoodType;
  confidence?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

// Chart data types
export interface ChartData {
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor: string[];
    borderColor: string[];
    borderWidth: number;
  }[];
}

// State management types
export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}

export interface PlaylistState {
  playlists: SpotifyPlaylist[];
  selectedPlaylist: SpotifyPlaylist | null;
  playlistTracks: Track[];
  loading: boolean;
  error: string | null;
}

export interface MoodState {
  currentAnalysis: MoodAnalysis | null;
  analysisHistory: MoodAnalysisHistory[];
  supportedMoods: string[];
  moodDescriptions: { [key: string]: string };
  loading: boolean;
  error: string | null;
} 