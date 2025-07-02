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