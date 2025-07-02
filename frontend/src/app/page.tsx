'use client'

import { useState } from 'react'

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)
  const [status, setStatus] = useState('')

  const warmUpBackend = async () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    setStatus('Waking up server (this may take 30+ seconds on first visit)...')
    
    try {
      // Try health check first to wake up the server with proper timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout for cold starts
      
      const healthResponse = await fetch(`${API_URL}/api/health`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (healthResponse.ok) {
        setStatus('Server ready! Connecting to Spotify...')
        return true
      }
    } catch (error) {
      console.warn('Health check failed, but continuing anyway:', error)
      setStatus('Server warming up... Attempting login...')
    }
    return true // Continue even if health check fails
  }

  const handleSpotifyLogin = async () => {
    try {
      setIsLoading(true)
      
      // First warm up the backend (important for Render free tier)
      await warmUpBackend()
      
      // Call backend to get Spotify OAuth URL
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
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
      if (error.name === 'AbortError') {
        alert('Connection timed out. The server may be waking up - please try again in a moment.')
      } else {
        alert(`Failed to connect to Spotify: ${error.message}`)
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-spotify-black text-white">
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4 text-spotify-green">
            🎵 Spotify Mood Classifier
          </h1>
          <p className="text-xl mb-8 text-gray-300">
            AI-powered playlist mood analysis
          </p>
          <div className="bg-spotify-medium-gray rounded-lg p-8 max-w-md mx-auto">
            <h2 className="text-2xl font-semibold mb-4">Get Started</h2>
            <p className="text-gray-300 mb-6">
              Connect your Spotify account to analyze your playlist moods with AI
            </p>
            
            {status && (
              <div className="mb-4 p-3 bg-spotify-dark-gray rounded-lg">
                <p className="text-spotify-green text-sm">{status}</p>
                {isLoading && (
                  <div className="mt-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-spotify-green mx-auto"></div>
                  </div>
                )}
              </div>
            )}
            
            <button 
              onClick={handleSpotifyLogin}
              disabled={isLoading}
              className="bg-spotify-green hover:bg-spotify-green-dark text-black font-semibold py-3 px-6 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Connecting...' : 'Login with Spotify'}
            </button>
          </div>
        </div>
      </div>
    </main>
  )
} 