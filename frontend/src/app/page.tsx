'use client'

import { useState } from 'react'

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)

  const handleSpotifyLogin = async () => {
    try {
      setIsLoading(true)
      
      // Call backend to get Spotify OAuth URL
      const response = await fetch('http://localhost:8000/api/auth/login')
      
      if (!response.ok) {
        throw new Error('Failed to initiate login')
      }
      
      const data = await response.json()
      
      // Redirect to Spotify OAuth
      window.location.href = data.auth_url
      
    } catch (error) {
      console.error('Login failed:', error)
      alert('Failed to connect to Spotify. Please try again.')
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