import { MoodType } from '@/types';

// Mood colors mapping
export const MOOD_COLORS: Record<MoodType, string> = {
  happy: '#FFD700',
  sad: '#4169E1',
  energetic: '#FF6347',
  calm: '#87CEEB',
  angry: '#DC143C',
  romantic: '#FF69B4',
  melancholic: '#9370DB',
  upbeat: '#32CD32',
};

// Mood emojis mapping
export const MOOD_EMOJIS: Record<MoodType, string> = {
  happy: '😊',
  sad: '😢',
  energetic: '⚡',
  calm: '😌',
  angry: '😠',
  romantic: '💕',
  melancholic: '🖤',
  upbeat: '🎉',
};

// Storage keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'spotify_access_token',
  USER: 'spotify_user',
  SELECTED_PLAYLIST: 'selected_playlist',
} as const;

// API endpoints
export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/api/auth/login',
    CALLBACK: '/api/auth/callback',
    REFRESH: '/api/auth/refresh',
    LOGOUT: '/api/auth/logout',
  },
  PLAYLISTS: {
    LIST: '/api/playlists',
    DETAILS: (id: string) => `/api/playlists/${id}`,
    SAVE: (id: string) => `/api/playlists/${id}/save`,
    TRACKS: (id: string) => `/api/playlists/${id}/tracks`,
  },
  MOOD: {
    ANALYZE: (id: string) => `/api/mood/${id}/analyze`,
    ANALYSIS: (id: string) => `/api/mood/${id}/analysis`,
    HISTORY: '/api/mood/history',
    MOODS: '/api/mood/moods',
  },
  HEALTH: {
    BASIC: '/api/health',
    DETAILED: '/api/health/detailed',
  },
} as const;

// App configuration
export const APP_CONFIG = {
  APP_NAME: 'Spotify Mood Classifier',
  VERSION: '1.0.0',
  DESCRIPTION: 'AI-powered playlist mood analysis',
  GITHUB_URL: 'https://github.com/AaryanAn/spotify_mood_classification',
  SPOTIFY_SCOPES: [
    'user-read-private',
    'user-read-email',
    'playlist-read-private',
    'playlist-read-collaborative',
    'user-library-read',
  ],
} as const;

// Chart configuration
export const CHART_CONFIG = {
  MOOD_DISTRIBUTION: {
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom' as const,
        },
        tooltip: {
          callbacks: {
            label: (context: any) => {
              const value = (context.parsed * 100).toFixed(1);
              return `${context.label}: ${value}%`;
            },
          },
        },
      },
    },
  },
  AUDIO_FEATURES: {
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          beginAtZero: true,
          max: 1,
          ticks: {
            stepSize: 0.2,
          },
        },
      },
      plugins: {
        legend: {
          display: false,
        },
      },
    },
  },
} as const;

// Animation variants for Framer Motion
export const ANIMATION_VARIANTS = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },
  slideUp: {
    initial: { y: 20, opacity: 0 },
    animate: { y: 0, opacity: 1 },
    exit: { y: -20, opacity: 0 },
  },
  slideDown: {
    initial: { y: -20, opacity: 0 },
    animate: { y: 0, opacity: 1 },
    exit: { y: 20, opacity: 0 },
  },
  scale: {
    initial: { scale: 0.9, opacity: 0 },
    animate: { scale: 1, opacity: 1 },
    exit: { scale: 0.9, opacity: 0 },
  },
} as const;

// Responsive breakpoints
export const BREAKPOINTS = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
} as const; 