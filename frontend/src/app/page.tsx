'use client'

import { useState } from 'react'

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState('')

  const getApiUrl = () => {
    // Use the production URL by default, fallback to localhost for development
    return process.env.NEXT_PUBLIC_API_URL || 'https://spotify-mood-classification.onrender.com'
  }

  const warmUpBackend = async (retries = 2) => {
    const API_URL = getApiUrl()
    console.log('Using API URL:', API_URL) // Debug log
    
    setStatus('Waking up server (this may take 30+ seconds on first visit)...')
    
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout for cold starts
        
        console.log(`Health check attempt ${attempt}/${retries}`)
        const healthResponse = await fetch(`${API_URL}/api/health`, {
          method: 'GET',
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
          },
        })
        
        clearTimeout(timeoutId)
        
        if (healthResponse.ok) {
          const data = await healthResponse.json()
          console.log('Health check successful:', data)
          setStatus('Server ready! Connecting to Spotify...')
          return true
        } else {
          console.warn(`Health check failed with status: ${healthResponse.status}`)
          if (attempt < retries) {
            setStatus(`Server warming up... Retrying (${attempt}/${retries})`)
            await new Promise(resolve => setTimeout(resolve, 5000)) // Wait 5s before retry
          }
        }
      } catch (error) {
        console.warn(`Health check attempt ${attempt} failed:`, error)
        if (attempt < retries) {
          setStatus(`Server warming up... Retrying (${attempt}/${retries})`)
          await new Promise(resolve => setTimeout(resolve, 5000)) // Wait 5s before retry
        } else {
          console.warn('All health check attempts failed, but continuing anyway')
          setStatus('Server warming up... Attempting login...')
        }
      }
    }
    return true // Continue even if all health checks fail
  }

  const handleSpotifyLogin = async () => {
    try {
      setIsLoading(true)
      
      // First warm up the backend (important for Render free tier)
      await warmUpBackend()
      
      // Call backend to get Spotify OAuth URL
      const API_URL = getApiUrl()
      setStatus('Getting authorization URL...')
      
      // Implement proper timeout for login request
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
      
      const response = await fetch(`${API_URL}/api/auth/login`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Failed to initiate login: ${response.status} - ${errorText}`)
      }
      
      const data = await response.json()
      
      if (!data.auth_url) {
        throw new Error('No authorization URL received from server')
      }
      
      setStatus('Redirecting to Spotify...')
      
      // Redirect to Spotify OAuth
      window.location.href = data.auth_url
      
    } catch (error) {
      console.error('Login failed:', error)
      setStatus('')
      if (error instanceof Error && error.name === 'AbortError') {
        alert('Connection timed out. The server may be waking up - please try again in a moment.')
      } else {
        const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred'
        alert(`Failed to connect to Spotify: ${errorMessage}`)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const features = [
    {
      icon: '🎵',
      title: 'AI Mood Analysis',
      description: 'Advanced machine learning algorithms analyze your music to detect emotional patterns and moods.'
    },
    {
      icon: '📊',
      title: 'Visual Insights',
      description: 'Beautiful charts and visualizations reveal the emotional journey of your playlists.'
    },
    {
      icon: '🎯',
      title: 'Smart Recommendations',
      description: 'Get personalized playlist suggestions based on your mood preferences and listening habits.'
    }
  ]

  return (
    <main className="min-h-screen gradient-bg overflow-hidden">
      {/* Floating Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-spotify-green opacity-10 rounded-full blur-3xl animate-pulse-slow"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-mood-happy opacity-8 rounded-full blur-3xl animate-pulse-slow" style={{animationDelay: '1s'}}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-mood-romantic opacity-5 rounded-full blur-3xl animate-pulse-slow" style={{animationDelay: '2s'}}></div>
      </div>

      <div className="relative z-10 container mx-auto px-4 py-12">
        {/* Hero Section */}
        <div className="text-center mb-16 fade-in">
          <div className="inline-flex items-center justify-center p-2 glass rounded-full mb-6">
            <span className="text-4xl animate-pulse">🎵</span>
          </div>
          
          <h1 className="text-6xl md:text-7xl font-bold mb-6 leading-tight">
            <span className="gradient-text">Spotify</span>
            <br />
            <span className="text-white">Mood Classifier</span>
          </h1>
          
          <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto leading-relaxed">
            Discover the emotional essence of your music with AI-powered sentiment analysis. 
            Transform your playlists into <span className="text-spotify-green font-semibold">mood journeys</span>.
          </p>

          {/* Main CTA Card */}
          <div className="max-w-lg mx-auto mb-16">
            <div className="glass rounded-3xl p-8 card-hover">
              <div className="flex items-center justify-center mb-6">
                <div className="w-16 h-16 bg-gradient-to-br from-spotify-green to-spotify-green-dark rounded-2xl flex items-center justify-center">
                  <span className="text-2xl">🚀</span>
                </div>
              </div>
              
              <h2 className="text-2xl font-bold mb-4 text-white">Ready to Begin?</h2>
              <p className="text-gray-300 mb-6">
                Connect your Spotify account to unlock AI-powered mood insights for your music library.
              </p>
              
              {status && (
                <div className="mb-6 p-4 glass rounded-xl border border-spotify-green/20">
                  <div className="flex items-center justify-center space-x-3">
                    {isLoading && (
                      <div className="w-5 h-5 border-2 border-spotify-green border-t-transparent rounded-full animate-spin"></div>
                    )}
                    <p className="text-spotify-green text-sm font-medium">{status}</p>
                  </div>
                </div>
              )}
              
              <button 
                onClick={handleSpotifyLogin}
                disabled={isLoading}
                className="w-full btn-primary text-black font-bold py-4 px-8 rounded-xl text-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none relative overflow-hidden group"
              >
                <span className="relative z-10 flex items-center justify-center space-x-3">
                  <span>🎵</span>
                  <span>{isLoading ? 'Connecting...' : 'Login with Spotify'}</span>
                </span>
              </button>
            </div>
          </div>
        </div>

        {/* Features Section */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {features.map((feature, index) => (
            <div 
              key={index} 
              className="glass rounded-2xl p-6 card-hover fade-in"
              style={{animationDelay: `${index * 0.2}s`}}
            >
              <div className="text-4xl mb-4 text-center">{feature.icon}</div>
              <h3 className="text-xl font-bold mb-3 text-center text-white">{feature.title}</h3>
              <p className="text-gray-300 text-center leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>

        {/* Mood Preview Section */}
        <div className="text-center">
          <h3 className="text-3xl font-bold mb-8 text-white">Discover Your Music's <span className="gradient-text">Emotional Palette</span></h3>
          
          <div className="flex flex-wrap justify-center gap-4 mb-8">
            {[
              { mood: 'Happy', color: 'bg-mood-happy', emoji: '😊' },
              { mood: 'Energetic', color: 'bg-mood-energetic', emoji: '⚡' },
              { mood: 'Calm', color: 'bg-mood-calm', emoji: '🧘' },
              { mood: 'Romantic', color: 'bg-mood-romantic', emoji: '💝' },
              { mood: 'Melancholic', color: 'bg-mood-melancholic', emoji: '🌙' },
              { mood: 'Upbeat', color: 'bg-mood-upbeat', emoji: '🎉' }
            ].map((item, index) => (
              <div 
                key={item.mood}
                className="glass rounded-full px-6 py-3 flex items-center space-x-2 card-hover fade-in"
                style={{animationDelay: `${index * 0.1}s`}}
              >
                <span className="text-lg">{item.emoji}</span>
                <span className="text-white font-medium">{item.mood}</span>
                <div className={`w-3 h-3 ${item.color} rounded-full opacity-80`}></div>
              </div>
            ))}
          </div>

          <p className="text-gray-400 max-w-2xl mx-auto">
            Our advanced AI analyzes audio features, lyrics sentiment, and musical patterns to create 
            a comprehensive emotional profile of your music collection.
          </p>
        </div>
      </div>
    </main>
  )
} 