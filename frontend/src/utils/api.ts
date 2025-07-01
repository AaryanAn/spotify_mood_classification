import axios, { AxiosResponse, AxiosError } from 'axios';
import {
  AuthResponse,
  LoginResponse,
  SpotifyPlaylistsResponse,
  SpotifyPlaylist,
  PlaylistTracksResponse,
  MoodAnalysis,
  MoodAnalysisHistoryResponse,
  HealthCheck,
} from '@/types';

// Create axios instance
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('spotify_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear auth token on 401
      localStorage.removeItem('spotify_access_token');
      localStorage.removeItem('spotify_user');
      // Redirect to login
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Authentication APIs
export const authApi = {
  login: async (): Promise<LoginResponse> => {
    const response: AxiosResponse<LoginResponse> = await api.get('/api/auth/login');
    return response.data;
  },

  callback: async (code: string, state: string): Promise<AuthResponse> => {
    const response: AxiosResponse<AuthResponse> = await api.post('/api/auth/callback', {
      code,
      state,
    });
    return response.data;
  },

  refreshToken: async (): Promise<void> => {
    await api.post('/api/auth/refresh');
  },

  logout: async (): Promise<void> => {
    await api.post('/api/auth/logout');
  },
};

// Playlist APIs
export const playlistApi = {
  getUserPlaylists: async (limit = 10000, offset = 0): Promise<SpotifyPlaylistsResponse> => {
    const response: AxiosResponse<SpotifyPlaylistsResponse> = await api.get(
      `/api/playlists?limit=${limit}&offset=${offset}`
    );
    return response.data;
  },

  getPlaylistDetails: async (playlistId: string): Promise<SpotifyPlaylist> => {
    const response: AxiosResponse<SpotifyPlaylist> = await api.get(
      `/api/playlists/${playlistId}`
    );
    return response.data;
  },

  savePlaylist: async (playlistId: string): Promise<{ message: string; playlist_id: string }> => {
    const response = await api.post(`/api/playlists/${playlistId}/save`);
    return response.data;
  },

  getPlaylistTracks: async (playlistId: string): Promise<PlaylistTracksResponse> => {
    const response: AxiosResponse<PlaylistTracksResponse> = await api.get(
      `/api/playlists/${playlistId}/tracks`
    );
    return response.data;
  },
};

// Mood analysis APIs
export const moodApi = {
  analyzePlaylist: async (playlistId: string): Promise<any> => {
    const response = await api.post(`/api/mood-analysis/analyze/${playlistId}`);
    return response.data;
  },

  getAnalysisHistory: async (playlistId: string): Promise<any[]> => {
    const response = await api.get(`/api/mood-analysis/history/${playlistId}`);
    return response.data;
  },

  getPlaylistStats: async (playlistId: string): Promise<any> => {
    const response = await api.get(`/api/mood-analysis/stats/${playlistId}`);
    return response.data;
  },

  // Deprecated endpoints (keeping for backward compatibility)
  getPlaylistAnalysis: async (playlistId: string): Promise<MoodAnalysis> => {
    const response: AxiosResponse<MoodAnalysis> = await api.get(
      `/api/mood-analysis/history/${playlistId}`
    );
    // Return the latest analysis from history
    const history = response.data as unknown as any[];
    if (history.length > 0) {
      return history[0] as MoodAnalysis;
    }
    throw new Error('No mood analysis found for this playlist');
  },

  getSupportedMoods: async (): Promise<{ moods: string[]; descriptions: { [key: string]: string } }> => {
    // Return static mood categories since we're using genre-metadata approach
    return {
      moods: ['happy', 'sad', 'energetic', 'calm', 'angry', 'romantic', 'melancholic', 'upbeat'],
      descriptions: {
        'happy': 'Joyful and positive music that lifts your spirits',
        'sad': 'Melancholic music that touches deep emotions',
        'energetic': 'High-energy music perfect for workouts or motivation',
        'calm': 'Peaceful and relaxing music for unwinding',
        'angry': 'Intense and aggressive music expressing frustration',
        'romantic': 'Tender and loving music for intimate moments',
        'melancholic': 'Bittersweet music with a touch of nostalgia',
        'upbeat': 'Cheerful and lively music that makes you want to dance'
      }
    };
  },
};

// Health check API
export const healthApi = {
  basic: async (): Promise<HealthCheck> => {
    const response: AxiosResponse<HealthCheck> = await api.get('/api/health');
    return response.data;
  },

  detailed: async (): Promise<HealthCheck> => {
    const response: AxiosResponse<HealthCheck> = await api.get('/api/health/detailed');
    return response.data;
  },
};

// Utility functions
export const handleApiError = (error: AxiosError): string => {
  if (error.response?.data) {
    const errorData = error.response.data as any;
    return errorData.detail || errorData.error || 'An unknown error occurred';
  }
  if (error.message) {
    return error.message;
  }
  return 'Network error occurred';
};

export default api; 