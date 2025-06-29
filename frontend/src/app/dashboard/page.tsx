'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

interface User {
  id: string
  display_name: string
  email: string
  country: string
  followers: number
}

interface Playlist {
  id: string
  name: string
  description: string | null
  tracks: {
    total: number
  }
  images: Array<{
    url: string
    height: number
    width: number
  }> | null
  external_urls: {
    spotify: string
  }
  owner: {
    display_name: string
  }
}

interface MoodAnalysis {
  playlist_id: string
  primary_mood: string
  mood_confidence: number
  mood_distribution: Record<string, number>
  avg_valence: number
  avg_energy: number
  avg_danceability: number
  tracks_analyzed: number
  created_at: string
}

export default function Dashboard() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [playlists, setPlaylists] = useState<Playlist[]>([])
  const [loadingPlaylists, setLoadingPlaylists] = useState(false)
  const [selectedPlaylist, setSelectedPlaylist] = useState<Playlist | null>(null)
  const [analysis, setAnalysis] = useState<MoodAnalysis | null>(null)
  const [analyzingPlaylist, setAnalyzingPlaylist] = useState<string | null>(null)
  const [showPlaylists, setShowPlaylists] = useState(false)
  const router = useRouter()

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('access_token')
    const userData = localStorage.getItem('user')

    if (!token || !userData) {
      router.push('/')
      return
    }

    try {
      setUser(JSON.parse(userData))
    } catch (error) {
      console.error('Failed to parse user data:', error)
      router.push('/')
    } finally {
      setLoading(false)
    }
  }, [router])

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    router.push('/')
  }

  const fetchPlaylists = async () => {
    setLoadingPlaylists(true)
    setShowPlaylists(true)
    
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('http://localhost:8000/api/playlists/', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })

      if (response.status === 401 || response.status === 403) {
        alert('Your session has expired. Please log in again.')
        handleLogout()
        return
      }

      if (!response.ok) {
        throw new Error('Failed to fetch playlists')
      }

      const data = await response.json()
      setPlaylists(data.items || [])
    } catch (error) {
      console.error('Error fetching playlists:', error)
      alert('Failed to fetch playlists. Your session may have expired. Please try logging out and back in.')
    } finally {
      setLoadingPlaylists(false)
    }
  }

  const analyzePlaylist = async (playlist: Playlist) => {
    console.log('🎵 [DEBUG] Starting playlist analysis:', {
      playlistId: playlist.id,
      playlistName: playlist.name,
      timestamp: new Date().toISOString()
    })
    
    setAnalyzingPlaylist(playlist.id)
    setSelectedPlaylist(playlist)
    setAnalysis(null)

    try {
      const token = localStorage.getItem('access_token')
      console.log('🔑 [DEBUG] Token check:', {
        hasToken: !!token,
        tokenPrefix: token ? token.substring(0, 20) + '...' : 'null',
        tokenLength: token?.length || 0
      })
      
      // First, save the playlist to our database
      const saveUrl = `http://localhost:8000/api/playlists/${playlist.id}/save`
      console.log('💾 [DEBUG] Attempting to save playlist:', {
        url: saveUrl,
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token?.substring(0, 20)}...`,
        }
      })

      const saveResponse = await fetch(saveUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      console.log('💾 [DEBUG] Save response:', {
        status: saveResponse.status,
        statusText: saveResponse.statusText,
        ok: saveResponse.ok,
        headers: Object.fromEntries(saveResponse.headers.entries())
      })

      if (saveResponse.status === 401 || saveResponse.status === 403) {
        console.error('🚫 [DEBUG] Token expired during save')
        alert('Your session has expired. Please log in again.')
        handleLogout()
        return
      }

      if (!saveResponse.ok) {
        const errorText = await saveResponse.text()
        console.error('💾 [DEBUG] Save failed:', {
          status: saveResponse.status,
          errorText: errorText
        })
        throw new Error(`Failed to save playlist: ${saveResponse.status} - ${errorText}`)
      }

      console.log('✅ [DEBUG] Playlist saved successfully')

      // Then analyze the playlist  
      const analyzeUrl = `http://localhost:8000/api/mood-analysis/${playlist.id}/analyze`
      console.log('🔍 [DEBUG] Attempting to analyze playlist:', {
        url: analyzeUrl,
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token?.substring(0, 20)}...`,
        }
      })

      const response = await fetch(analyzeUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      console.log('🔍 [DEBUG] Analysis response:', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      })

      if (response.status === 401 || response.status === 403) {
        console.error('🚫 [DEBUG] Token expired during analysis')
        alert('Your session has expired. Please log in again.')
        handleLogout()
        return
      }

      if (!response.ok) {
        const errorText = await response.text()
        console.error('🔍 [DEBUG] Analysis failed:', {
          status: response.status,
          errorText: errorText
        })
        throw new Error(`Failed to analyze playlist: ${response.status} - ${errorText}`)
      }

      console.log('✅ [DEBUG] Analysis started successfully')
      
      // Poll for results
      await pollForAnalysisResults(playlist.id)
    } catch (error) {
      console.error('❌ [DEBUG] Error analyzing playlist:', {
        error: error,
        errorMessage: error instanceof Error ? error.message : 'Unknown error',
        stack: error instanceof Error ? error.stack : 'No stack trace'
      })
      alert('Failed to analyze playlist. Your session may have expired. Please try logging out and back in.')
    } finally {
      setAnalyzingPlaylist(null)
    }
  }

  const pollForAnalysisResults = async (playlistId: string) => {
    const maxAttempts = 30 // 30 seconds max wait
    let attempts = 0

    const poll = async () => {
      try {
        const token = localStorage.getItem('access_token')
        const response = await fetch(`http://localhost:8000/api/mood-analysis/${playlistId}/analysis`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.status === 401 || response.status === 403) {
          alert('Your session has expired. Please log in again.')
          handleLogout()
          return false
        }

        if (response.ok) {
          const analysisData = await response.json()
          setAnalysis(analysisData)
          return true
        }

        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000) // Poll every second
        } else {
          throw new Error('Analysis timeout')
        }
      } catch (error) {
        console.error('Error polling for results:', error)
        alert('Analysis is taking longer than expected. Please refresh and check again.')
      }
    }

    await poll()
  }

  const getMoodEmoji = (mood: string) => {
    const moodEmojis: Record<string, string> = {
      'happy': '😊',
      'sad': '😢',
      'energetic': '⚡',
      'calm': '😌',
      'angry': '😠',
      'romantic': '💕',
      'melancholic': '😔',
      'upbeat': '🎉'
    }
    return moodEmojis[mood.toLowerCase()] || '🎵'
  }

  const getMoodColor = (mood: string) => {
    const moodColors: Record<string, string> = {
      'happy': 'text-yellow-400',
      'sad': 'text-blue-400',
      'energetic': 'text-red-400',
      'calm': 'text-green-400',
      'angry': 'text-red-600',
      'romantic': 'text-pink-400',
      'melancholic': 'text-purple-400',
      'upbeat': 'text-orange-400'
    }
    return moodColors[mood.toLowerCase()] || 'text-spotify-green'
  }

  const getPlaylistImageUrl = (playlist: Playlist) => {
    if (playlist.images && playlist.images.length > 0) {
      return playlist.images[0].url
    }
    // SVG placeholder for playlists without images
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iIzM3NDE0ZiIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5Y2EzYWYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj7wn461IFBsYXlsaXN0PC90ZXh0Pjwvc3ZnPg=='
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-spotify-black text-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-spotify-green"></div>
      </main>
    )
  }

  if (!user) {
    return null
  }

  return (
    <main className="min-h-screen bg-spotify-black text-white">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-spotify-green">
            🎵 Spotify Mood Classifier
          </h1>
          <button
            onClick={handleLogout}
            className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>

        {/* Welcome Section */}
        <div className="bg-spotify-medium-gray rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">
            Welcome back, {user.display_name}! 👋
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Email:</span>
              <p className="text-white">{user.email || 'Not provided'}</p>
            </div>
            <div>
              <span className="text-gray-400">Country:</span>
              <p className="text-white">{user.country || 'Not provided'}</p>
            </div>
            <div>
              <span className="text-gray-400">Followers:</span>
              <p className="text-white">{user.followers?.toLocaleString() || '0'}</p>
            </div>
          </div>
        </div>

        {/* Analysis Results */}
        {analysis && selectedPlaylist && (
          <div className="bg-spotify-medium-gray rounded-lg p-6 mb-8">
            <h3 className="text-xl font-semibold mb-4">Analysis Results</h3>
            <div className="bg-spotify-dark-gray rounded-lg p-6">
              <div className="flex items-center gap-4 mb-4">
                <img 
                  src={getPlaylistImageUrl(selectedPlaylist)} 
                  alt={selectedPlaylist.name}
                  className="w-16 h-16 rounded-lg"
                />
                <div>
                  <h4 className="text-lg font-semibold">{selectedPlaylist.name}</h4>
                  <p className="text-gray-400">{selectedPlaylist.tracks.total} tracks analyzed</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <div className="text-center">
                  <div className={`text-4xl mb-2 ${getMoodColor(analysis.primary_mood)}`}>
                    {getMoodEmoji(analysis.primary_mood)}
                  </div>
                  <h5 className="font-semibold text-lg capitalize">{analysis.primary_mood}</h5>
                  <p className="text-sm text-gray-400">Primary Mood</p>
                  <p className="text-xs text-gray-500">{Math.round(analysis.mood_confidence * 100)}% confidence</p>
                </div>

                <div className="text-center">
                  <div className="text-2xl mb-2">💫</div>
                  <h5 className="font-semibold">{Math.round(analysis.avg_valence * 100)}%</h5>
                  <p className="text-sm text-gray-400">Positivity</p>
                </div>

                <div className="text-center">
                  <div className="text-2xl mb-2">⚡</div>
                  <h5 className="font-semibold">{Math.round(analysis.avg_energy * 100)}%</h5>
                  <p className="text-sm text-gray-400">Energy</p>
                </div>

                <div className="text-center">
                  <div className="text-2xl mb-2">💃</div>
                  <h5 className="font-semibold">{Math.round(analysis.avg_danceability * 100)}%</h5>
                  <p className="text-sm text-gray-400">Danceability</p>
                </div>
              </div>

              <div className="border-t border-gray-600 pt-4">
                <h6 className="font-semibold mb-3">Mood Distribution</h6>
                <div className="space-y-2">
                  {Object.entries(analysis.mood_distribution).map(([mood, percentage]) => (
                    <div key={mood} className="flex items-center justify-between">
                      <span className="capitalize flex items-center gap-2">
                        <span className={getMoodColor(mood)}>{getMoodEmoji(mood)}</span>
                        {mood}
                      </span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-600 rounded-full h-2">
                          <div 
                            className="bg-spotify-green h-2 rounded-full" 
                            style={{ width: `${percentage}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-400 w-12 text-right">
                          {Math.round(percentage)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Playlist Analysis Section */}
        <div className="bg-spotify-medium-gray rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Playlist Mood Analysis</h3>
          
          {!showPlaylists ? (
            <>
              <p className="text-gray-300 mb-6">
                Your Spotify account is now connected! Start analyzing your playlist moods with our AI-powered system.
              </p>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                <div className="bg-spotify-dark-gray p-4 rounded-lg text-center">
                  <div className="text-3xl mb-2">🎭</div>
                  <h4 className="font-semibold mb-2">Mood Detection</h4>
                  <p className="text-sm text-gray-400">
                    Analyze the emotional tone of your playlists using advanced ML algorithms
                  </p>
                </div>
                
                <div className="bg-spotify-dark-gray p-4 rounded-lg text-center">
                  <div className="text-3xl mb-2">📊</div>
                  <h4 className="font-semibold mb-2">Detailed Analytics</h4>
                  <p className="text-sm text-gray-400">
                    Get comprehensive insights about energy, valence, and mood distributions
                  </p>
                </div>
                
                <div className="bg-spotify-dark-gray p-4 rounded-lg text-center">
                  <div className="text-3xl mb-2">🚀</div>
                  <h4 className="font-semibold mb-2">Real-time Processing</h4>
                  <p className="text-sm text-gray-400">
                    Experience fast, background processing with Redis caching
                  </p>
                </div>
              </div>

              <div className="text-center">
                <button 
                  onClick={fetchPlaylists}
                  disabled={loadingPlaylists}
                  className="bg-spotify-green hover:bg-spotify-green-dark text-black font-semibold py-3 px-8 rounded-lg transition-colors disabled:opacity-50"
                >
                  {loadingPlaylists ? 'Loading...' : 'Analyze My Playlists'}
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex justify-between items-center mb-6">
                <p className="text-gray-300">
                  Select a playlist to analyze its mood
                </p>
                <button 
                  onClick={() => setShowPlaylists(false)}
                  className="text-spotify-green hover:text-spotify-green-dark transition-colors"
                >
                  ← Back to Overview
                </button>
              </div>

              {loadingPlaylists ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-spotify-green mx-auto mb-4"></div>
                  <p className="text-gray-400">Loading your playlists...</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {playlists.map((playlist) => (
                    <div 
                      key={playlist.id} 
                      className="bg-spotify-dark-gray p-4 rounded-lg hover:bg-gray-600 transition-colors cursor-pointer"
                      onClick={() => analyzePlaylist(playlist)}
                    >
                      <div className="relative">
                        <img 
                          src={getPlaylistImageUrl(playlist)} 
                          alt={playlist.name}
                          className="w-full aspect-square object-cover rounded-lg mb-3"
                        />
                        {analyzingPlaylist === playlist.id && (
                          <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center rounded-lg">
                            <div className="text-center">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-spotify-green mx-auto mb-2"></div>
                              <p className="text-sm text-white">Analyzing...</p>
                            </div>
                          </div>
                        )}
                      </div>
                      <h4 className="font-semibold mb-1 truncate">{playlist.name}</h4>
                      <p className="text-sm text-gray-400 mb-2">{playlist.tracks.total} tracks</p>
                      <p className="text-xs text-gray-500 truncate">by {playlist.owner.display_name}</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  )
} 