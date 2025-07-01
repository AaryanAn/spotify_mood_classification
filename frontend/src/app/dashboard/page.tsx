'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { MoodAnalysis } from '@/types'

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
    id: string
    display_name: string
  }
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
  const [useLyrics, setUseLyrics] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [showOwnOnly, setShowOwnOnly] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [playlistsPerPage] = useState(12)
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
    setCurrentPage(1)
    
    try {
      const token = localStorage.getItem('access_token')
      // Fetch ALL playlists (no limit)
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

  // Filter and search playlists
  const filteredPlaylists = playlists.filter(playlist => {
    const matchesSearch = playlist.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         playlist.owner.display_name.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesOwner = !showOwnOnly || playlist.owner.id === user?.id
    return matchesSearch && matchesOwner
  })

  // Pagination
  const totalPages = Math.ceil(filteredPlaylists.length / playlistsPerPage)
  const startIndex = (currentPage - 1) * playlistsPerPage
  const paginatedPlaylists = filteredPlaylists.slice(startIndex, startIndex + playlistsPerPage)

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
        alert('Your Spotify session has expired. Please log out and log back in to refresh your token.')
        handleLogout()
        return
      }

      if (!saveResponse.ok) {
        const errorText = await saveResponse.text()
        console.error('💾 [DEBUG] Save failed:', {
          status: saveResponse.status,
          errorText: errorText
        })
        
        // Show specific error messages based on status code
        if (saveResponse.status === 429) {
          alert('Rate limit exceeded. Please wait a moment and try again.')
        } else if (saveResponse.status >= 500) {
          alert('Server error occurred. Please try again in a few moments.')
        } else {
          alert(`Failed to save playlist (${saveResponse.status}). Please check your connection and try again.`)
        }
        return
      }

      console.log('✅ [DEBUG] Playlist saved successfully')

      // Then analyze the playlist  
      const analyzeUrl = `http://localhost:8000/api/mood-analysis/${playlist.id}/analyze${useLyrics ? '?use_lyrics=true' : ''}`
      console.log('🔍 [DEBUG] Attempting to analyze playlist:', {
        url: analyzeUrl,
        method: 'POST',
        useLyrics: useLyrics,
        analysisType: useLyrics ? 'Enhanced (with lyrics)' : 'Standard (genre + metadata)',
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
        alert('Your Spotify session has expired. Please log out and log back in to refresh your token.')
        handleLogout()
        return
      }

      if (!response.ok) {
        const errorText = await response.text()
        console.error('🔍 [DEBUG] Analysis failed:', {
          status: response.status,
          errorText: errorText
        })
        
        // Show specific error messages based on status code
        if (response.status === 404) {
          alert('Playlist not found. Please try saving the playlist again.')
        } else if (response.status === 429) {
          alert('Rate limit exceeded. Please wait a moment and try again.')
        } else if (response.status >= 500) {
          alert('Server error occurred during analysis. Please try again in a few moments.')
        } else {
          alert(`Failed to analyze playlist (${response.status}). Please try again.`)
        }
        return
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
      alert('Failed to analyze playlist. This is often due to an expired Spotify session. Please log out and log back in to refresh your token.')
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
          alert('Your Spotify session has expired. Please log out and log back in to refresh your token.')
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
    <main className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        {/* Header */}
        <div className="flex justify-between items-center mb-12 fade-in">
          <div>
            <h1 className="text-5xl font-extrabold gradient-text mb-2">
              🎵 Spotify Mood Classifier
            </h1>
            <p className="text-gray-400 text-lg font-light">
              Advanced AI-powered playlist emotion analysis
            </p>
          </div>
          <div className="flex items-center gap-4">
            <a
              href="/how-it-works"
              className="glass hover:bg-opacity-80 text-white font-medium py-3 px-6 rounded-xl transition-all duration-300 hover:transform hover:scale-105"
            >
              🧠 How It Works
            </a>
            <button
              onClick={handleLogout}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white font-medium py-3 px-6 rounded-xl transition-all duration-300 hover:transform hover:scale-105 hover:shadow-lg"
            >
              Logout
            </button>
          </div>
        </div>

        {/* Welcome Section */}
        <div className="glass rounded-2xl p-8 mb-12 fade-in border border-white/10">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-spotify-green to-spotify-green-light rounded-2xl flex items-center justify-center text-2xl">
              👋
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-1">
                Welcome back, {user.display_name}!
              </h2>
              <p className="text-gray-400 text-lg">
                Ready to dive deep into your music's emotional landscape?
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-spotify-green/20 to-spotify-green/10 rounded-xl p-4 border border-spotify-green/20">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 bg-spotify-green/20 rounded-lg flex items-center justify-center">
                  📧
                </div>
                <span className="text-gray-400 font-medium">Email</span>
              </div>
              <p className="text-white font-semibold">{user.email || 'Not provided'}</p>
            </div>
            
            <div className="bg-gradient-to-br from-blue-500/20 to-blue-500/10 rounded-xl p-4 border border-blue-500/20">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center">
                  🌍
                </div>
                <span className="text-gray-400 font-medium">Country</span>
              </div>
              <p className="text-white font-semibold">{user.country || 'Not provided'}</p>
            </div>
            
            <div className="bg-gradient-to-br from-purple-500/20 to-purple-500/10 rounded-xl p-4 border border-purple-500/20">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center">
                  👥
                </div>
                <span className="text-gray-400 font-medium">Followers</span>
              </div>
              <p className="text-white font-semibold">{user.followers?.toLocaleString() || '0'}</p>
            </div>
          </div>
        </div>

        {/* Enhanced Analysis Results */}
        {analysis && selectedPlaylist && (
          <div className="glass rounded-2xl p-8 mb-12 fade-in border border-white/10">
            <div className="flex items-center gap-4 mb-8">
              <div className="text-4xl">🎯</div>
              <div>
                <h3 className="text-3xl font-bold gradient-text">Deep Analysis Results</h3>
                <p className="text-gray-400 text-lg">Comprehensive emotional breakdown of your playlist</p>
              </div>
            </div>

            {/* Playlist Header */}
            <div className="bg-gradient-to-r from-spotify-green/20 to-spotify-green/10 rounded-2xl p-6 mb-8 border border-spotify-green/20">
              <div className="flex items-center gap-6">
                <div className="relative">
                  <img 
                    src={getPlaylistImageUrl(selectedPlaylist)} 
                    alt={selectedPlaylist.name}
                    className="w-20 h-20 rounded-2xl shadow-lg"
                  />
                  <div className="absolute -top-2 -right-2 w-6 h-6 bg-spotify-green rounded-full flex items-center justify-center">
                    ✓
                  </div>
                </div>
                <div className="flex-1">
                  <h4 className="text-2xl font-bold text-white mb-2">{selectedPlaylist.name}</h4>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-gray-300">{analysis.metadata.tracks_analyzed} tracks analyzed</span>
                    <span className="text-gray-500">•</span>
                    <span className="text-gray-300">
                      {Math.round((Date.now() - new Date(analysis.metadata.analyzed_at).getTime()) / 1000 / 60)} minutes ago
                    </span>
                  </div>
                  {(analysis as any).analysis_data && typeof (analysis as any).analysis_data === 'object' && (
                    <div className="flex items-center gap-3 mt-3">
                      {((analysis as any).analysis_data as any).use_lyrics ? (
                        <span className="bg-gradient-to-r from-spotify-green to-spotify-green-light text-black px-3 py-1 rounded-full text-xs font-bold">
                          🎵 Enhanced with Lyrics
                        </span>
                      ) : (
                        <span className="bg-gradient-to-r from-gray-600 to-gray-700 text-gray-200 px-3 py-1 rounded-full text-xs font-bold">
                          📊 Standard Analysis
                        </span>
                      )}
                      {((analysis as any).analysis_data as any).lyrics_coverage && ((analysis as any).analysis_data as any).lyrics_coverage > 0 && (
                        <span className="bg-blue-500/20 text-blue-300 px-3 py-1 rounded-full text-xs font-medium">
                          {Math.round(((analysis as any).analysis_data as any).lyrics_coverage * 100)}% lyrics coverage
                        </span>
                      )}
                      <span className="bg-purple-500/20 text-purple-300 px-3 py-1 rounded-full text-xs font-medium">
                        {Math.round((analysis.mood_confidence || 0) * 100)}% confidence
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
              {/* Primary Mood & Key Metrics */}
              <div className="xl:col-span-1">
                <div className="bg-gradient-to-br from-spotify-dark-gray/80 to-spotify-dark-gray/40 rounded-2xl p-6 border border-white/10">
                  <h5 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    🎭 Primary Emotion
                  </h5>
                  
                  <div className="text-center mb-6">
                    <div className={`text-6xl mb-4 ${getMoodColor(analysis.primary_mood)}`}>
                      {getMoodEmoji(analysis.primary_mood)}
                    </div>
                    <h6 className="text-2xl font-bold capitalize text-white mb-2">{analysis.primary_mood}</h6>
                    <div className="bg-white/10 rounded-full px-4 py-2 inline-block">
                      <span className="text-lg font-semibold text-spotify-green">
                        {Math.round((analysis.mood_confidence || 0) * 100)}% confidence
                      </span>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl">
                      <span className="text-gray-300">💫 Positivity</span>
                      <span className="font-bold text-yellow-400">{Math.round(analysis.audio_features.avg_valence * 100)}%</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl">
                      <span className="text-gray-300">⚡ Energy</span>
                      <span className="font-bold text-red-400">{Math.round(analysis.audio_features.avg_energy * 100)}%</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-white/5 rounded-xl">
                      <span className="text-gray-300">💃 Danceability</span>
                      <span className="font-bold text-purple-400">{Math.round(analysis.audio_features.avg_danceability * 100)}%</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Mood Distribution */}
              <div className="xl:col-span-2">
                <div className="bg-gradient-to-br from-spotify-dark-gray/80 to-spotify-dark-gray/40 rounded-2xl p-6 border border-white/10">
                  <h5 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
                    📊 Emotional Spectrum
                  </h5>
                  
                  <div className="space-y-4">
                    {Object.entries(analysis.mood_distribution)
                      .sort(([,a], [,b]) => b - a)
                      .map(([mood, percentage], index) => (
                        <div key={mood} className="group">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                              <span className={`text-2xl ${getMoodColor(mood)}`}>
                                {getMoodEmoji(mood)}
                              </span>
                              <span className="capitalize font-semibold text-white">{mood}</span>
                              {index === 0 && (
                                <span className="bg-spotify-green text-black px-2 py-1 rounded-full text-xs font-bold">
                                  DOMINANT
                                </span>
                              )}
                            </div>
                            <span className="text-lg font-bold text-white">
                              {Math.round(percentage * 100)}%
                            </span>
                          </div>
                          <div className="w-full bg-white/10 rounded-full h-3 overflow-hidden">
                            <div 
                              className={`mood-bar h-full rounded-full bg-gradient-to-r ${
                                index === 0 ? 'from-spotify-green to-spotify-green-light' : 
                                index === 1 ? 'from-blue-500 to-blue-600' :
                                index === 2 ? 'from-purple-500 to-purple-600' :
                                'from-gray-500 to-gray-600'
                              }`}
                              style={{ 
                                width: `${Math.round(percentage * 100)}%`,
                                animationDelay: `${index * 0.1}s`
                              }}
                            ></div>
                          </div>
                        </div>
                      ))
                    }
                  </div>
                </div>
              </div>
            </div>

            {/* Analysis Breakdown */}
            {(analysis as any).analysis_data && typeof (analysis as any).analysis_data === 'object' && (
              <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Method Breakdown */}
                <div className="bg-gradient-to-br from-blue-500/20 to-blue-500/10 rounded-2xl p-6 border border-blue-500/20">
                  <h5 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    🔬 Analysis Method
                  </h5>
                  
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Method Used</span>
                      <span className="font-semibold text-blue-300">
                        {((analysis as any).analysis_data as any).use_lyrics ? 'Enhanced (Lyrics + Metadata)' : 'Standard (Metadata Only)'}
                      </span>
                    </div>
                    
                    {((analysis as any).analysis_data as any).use_lyrics && (
                      <>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-300">Genre & Metadata Weight</span>
                          <span className="font-semibold text-yellow-300">60%</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-300">Lyrics Sentiment Weight</span>
                          <span className="font-semibold text-green-300">40%</span>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-gray-300">Lyrics Found</span>
                          <span className="font-semibold text-purple-300">
                            {((analysis as any).analysis_data as any).analysis_components?.lyrics_tracks || 0} / {analysis.metadata.tracks_analyzed}
                          </span>
                        </div>
                      </>
                    )}
                    
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Processing Time</span>
                      <span className="font-semibold text-orange-300">
                        {((analysis as any).analysis_data as any).use_lyrics ? '~8 seconds' : '~2 seconds'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Genre Analysis */}
                <div className="bg-gradient-to-br from-purple-500/20 to-purple-500/10 rounded-2xl p-6 border border-purple-500/20">
                  <h5 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    🎼 Genre Insights
                  </h5>
                  
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Tracks with Genres</span>
                      <span className="font-semibold text-purple-300">
                        {((analysis as any).analysis_data as any).tracks_with_genres || 0} / {analysis.metadata.tracks_analyzed}
                      </span>
                    </div>
                    
                    <div className="flex justify-between items-center">
                      <span className="text-gray-300">Unique Genres</span>
                      <span className="font-semibold text-purple-300">
                        {((analysis as any).analysis_data as any).unique_genres || 0}
                      </span>
                    </div>
                    
                    {((analysis as any).analysis_data as any).sample_genres && (
                      <div>
                        <span className="text-gray-300 block mb-2">Top Genres</span>
                        <div className="flex flex-wrap gap-2">
                          {((analysis as any).analysis_data as any).sample_genres.slice(0, 3).map((genre: string, index: number) => (
                            <span key={index} className="bg-purple-500/30 text-purple-200 px-3 py-1 rounded-full text-xs font-medium">
                              {genre}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Confidence Explanation */}
            <div className="mt-8 bg-gradient-to-br from-green-500/20 to-green-500/10 rounded-2xl p-6 border border-green-500/20">
              <h5 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                🎯 Confidence Analysis
              </h5>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className={`text-3xl mb-2 ${
                    (analysis.mood_confidence || 0) >= 0.7 ? 'text-green-400' :
                    (analysis.mood_confidence || 0) >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {(analysis.mood_confidence || 0) >= 0.7 ? '🎯' : 
                     (analysis.mood_confidence || 0) >= 0.4 ? '🎲' : '❓'}
                  </div>
                  <h6 className="font-bold text-lg text-white">
                    {(analysis.mood_confidence || 0) >= 0.7 ? 'HIGH' : 
                     (analysis.mood_confidence || 0) >= 0.4 ? 'MEDIUM' : 'LOW'}
                  </h6>
                  <p className="text-sm text-gray-400">Confidence Level</p>
                </div>
                
                <div className="md:col-span-2">
                  <p className="text-gray-300 mb-4">
                    {(analysis.mood_confidence || 0) >= 0.7 ? 
                      'Strong consensus across genres and lyrics. This analysis is highly reliable.' :
                     (analysis.mood_confidence || 0) >= 0.4 ? 
                      'Moderate agreement between data sources. Analysis shows clear patterns with some variation.' :
                      'Mixed signals from genres and lyrics. This playlist has diverse emotional content.'}
                  </p>
                  
                  <div className="bg-white/5 rounded-xl p-4">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-400">Confidence Score</span>
                      <span className="text-white font-semibold">
                        {Math.round((analysis.mood_confidence || 0) * 100)}%
                      </span>
                    </div>
                    <div className="w-full bg-white/10 rounded-full h-2">
                      <div 
                        className={`h-full rounded-full bg-gradient-to-r ${
                          (analysis.mood_confidence || 0) >= 0.7 ? 'from-green-500 to-green-400' :
                          (analysis.mood_confidence || 0) >= 0.4 ? 'from-yellow-500 to-yellow-400' : 'from-red-500 to-red-400'
                        }`}
                        style={{ width: `${Math.round((analysis.mood_confidence || 0) * 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Playlist Analysis Section */}
        <div className="glass rounded-2xl p-8 border border-white/10 fade-in">
          <div className="flex items-center gap-4 mb-6">
            <div className="text-4xl">🎵</div>
            <div>
              <h3 className="text-3xl font-bold gradient-text">Playlist Mood Analysis</h3>
              <p className="text-gray-400 text-lg">Discover the emotional DNA of your music</p>
            </div>
          </div>
          
          {!showPlaylists ? (
            <>
              <div className="text-center mb-8">
                <p className="text-xl text-gray-300 mb-2">
                  Your Spotify account is now connected! 🎉
                </p>
                <p className="text-gray-400">
                  Start analyzing your playlist moods with our advanced AI-powered system.
                </p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
                <div className="card-hover bg-gradient-to-br from-spotify-green/20 to-spotify-green/10 rounded-2xl p-6 text-center border border-spotify-green/20">
                  <div className="w-16 h-16 bg-gradient-to-br from-spotify-green to-spotify-green-light rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
                    🎭
                  </div>
                  <h4 className="text-xl font-bold text-white mb-3">Mood Detection</h4>
                  <p className="text-gray-300 leading-relaxed">
                    Analyze the emotional tone of your playlists using advanced ML algorithms and sentiment analysis
                  </p>
                </div>
                
                <div className="card-hover bg-gradient-to-br from-blue-500/20 to-blue-500/10 rounded-2xl p-6 text-center border border-blue-500/20">
                  <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
                    📊
                  </div>
                  <h4 className="text-xl font-bold text-white mb-3">Detailed Analytics</h4>
                  <p className="text-gray-300 leading-relaxed">
                    Get comprehensive insights about energy, valence, mood distributions, and confidence scores
                  </p>
                </div>
                
                <div className="card-hover bg-gradient-to-br from-purple-500/20 to-purple-500/10 rounded-2xl p-6 text-center border border-purple-500/20">
                  <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4">
                    🚀
                  </div>
                  <h4 className="text-xl font-bold text-white mb-3">Real-time Processing</h4>
                  <p className="text-gray-300 leading-relaxed">
                    Experience fast, background processing with Redis caching and parallel analysis
                  </p>
                </div>
              </div>

              <div className="text-center">
                <button 
                  onClick={fetchPlaylists}
                  disabled={loadingPlaylists}
                  className={`btn-primary text-black font-bold py-4 px-12 rounded-2xl text-lg transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed ${
                    loadingPlaylists ? 'pulse-green' : 'hover:shadow-2xl hover:shadow-spotify-green/50'
                  }`}
                >
                  {loadingPlaylists ? (
                    <div className="flex items-center gap-3">
                      <div className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin"></div>
                      Loading Your Playlists...
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <span>🎵</span>
                      Analyze My Playlists
                    </div>
                  )}
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Controls Header */}
              <div className="flex justify-between items-center mb-6">
                <div>
                  <p className="text-gray-300 mb-3">
                    Select a playlist to analyze its mood ({filteredPlaylists.length} playlists found)
                  </p>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-gray-400">Analysis Type:</span>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={useLyrics}
                        onChange={(e) => setUseLyrics(e.target.checked)}
                        className="w-4 h-4 text-spotify-green bg-gray-700 border-gray-600 rounded focus:ring-spotify-green focus:ring-2"
                      />
                      <span className="text-sm">
                        {useLyrics ? (
                          <span className="text-spotify-green font-semibold">🎵 Enhanced (with lyrics)</span>
                        ) : (
                          <span className="text-gray-300">📊 Standard (genre + metadata)</span>
                        )}
                      </span>
                    </label>
                    {useLyrics && (
                      <span className="text-xs text-gray-500 bg-gray-700 px-2 py-1 rounded">
                        Powered by Genius API
                      </span>
                    )}
                  </div>
                </div>
                <button 
                  onClick={() => setShowPlaylists(false)}
                  className="text-spotify-green hover:text-spotify-green-dark transition-colors"
                >
                  ← Back to Overview
                </button>
              </div>

              {/* Search and Filter Controls */}
              <div className="bg-gradient-to-br from-spotify-dark-gray/60 to-spotify-dark-gray/30 rounded-2xl p-6 mb-8 border border-white/10">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Search Bar */}
                  <div>
                    <label className="block text-lg font-semibold text-white mb-3 flex items-center gap-2">
                      🔍 Search Playlists
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        placeholder="Search by playlist name or creator..."
                        value={searchTerm}
                        onChange={(e) => {
                          setSearchTerm(e.target.value)
                          setCurrentPage(1)
                        }}
                        className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-spotify-green focus:border-transparent backdrop-blur-sm transition-all duration-300"
                      />
                      <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                        🔍
                      </div>
                    </div>
                  </div>

                  {/* Filter Controls */}
                  <div>
                    <label className="block text-lg font-semibold text-white mb-3 flex items-center gap-2">
                      🎯 Filter Options
                    </label>
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 cursor-pointer p-3 bg-white/5 rounded-xl hover:bg-white/10 transition-all duration-300">
                        <input
                          type="checkbox"
                          checked={showOwnOnly}
                          onChange={(e) => {
                            setShowOwnOnly(e.target.checked)
                            setCurrentPage(1)
                          }}
                          className="w-5 h-5 text-spotify-green bg-transparent border-2 border-gray-400 rounded focus:ring-spotify-green focus:ring-2"
                        />
                        <span className="text-white font-medium">My playlists only</span>
                        <div className="ml-auto bg-spotify-green/20 text-spotify-green px-3 py-1 rounded-full text-sm font-bold">
                          {showOwnOnly ? 
                            `${filteredPlaylists.filter(p => p.owner.id === user?.id).length} owned` : 
                            `${playlists.length} total`
                          }
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>

              {loadingPlaylists ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-spotify-green mx-auto mb-4"></div>
                  <p className="text-gray-400">Loading your playlists...</p>
                </div>
              ) : filteredPlaylists.length === 0 ? (
                <div className="text-center py-8">
                  <div className="text-6xl mb-4">🎵</div>
                  <h4 className="text-xl font-semibold mb-2">No playlists found</h4>
                  <p className="text-gray-400 mb-4">
                    {searchTerm ? `No playlists match "${searchTerm}"` : 'No playlists available'}
                  </p>
                  {searchTerm && (
                    <button
                      onClick={() => {
                        setSearchTerm('')
                        setCurrentPage(1)
                      }}
                      className="bg-spotify-green hover:bg-spotify-green-dark text-black font-semibold py-2 px-4 rounded-lg transition-colors"
                    >
                      Clear Search
                    </button>
                  )}
                </div>
              ) : (
                <>
                  {/* Playlist Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
                    {paginatedPlaylists.map((playlist, index) => (
                      <div 
                        key={playlist.id} 
                        className="group card-hover bg-gradient-to-br from-spotify-dark-gray/80 to-spotify-dark-gray/40 rounded-2xl p-5 cursor-pointer border border-white/10 fade-in"
                        style={{ animationDelay: `${index * 0.1}s` }}
                        onClick={() => analyzePlaylist(playlist)}
                      >
                        <div className="relative mb-4">
                          <div className="relative overflow-hidden rounded-2xl">
                            <img 
                              src={getPlaylistImageUrl(playlist)} 
                              alt={playlist.name}
                              className="w-full aspect-square object-cover group-hover:scale-110 transition-transform duration-500"
                            />
                            <div className="absolute inset-0 bg-black/20 group-hover:bg-black/10 transition-all duration-300"></div>
                          </div>
                          
                          {analyzingPlaylist === playlist.id && (
                            <div className="absolute inset-0 bg-black/80 flex items-center justify-center rounded-2xl backdrop-blur-sm">
                              <div className="text-center">
                                <div className="w-10 h-10 border-3 border-spotify-green/30 border-t-spotify-green rounded-full animate-spin mx-auto mb-3"></div>
                                <p className="text-white font-semibold">Analyzing...</p>
                                <p className="text-xs text-gray-400 mt-1">
                                  {useLyrics ? 'Enhanced analysis in progress' : 'Standard analysis in progress'}
                                </p>
                              </div>
                            </div>
                          )}
                          
                          {playlist.owner.id === user?.id && (
                            <div className="absolute top-3 right-3">
                              <span className="bg-gradient-to-r from-spotify-green to-spotify-green-light text-black px-3 py-1 rounded-full text-xs font-bold shadow-lg">
                                YOURS
                              </span>
                            </div>
                          )}
                        </div>
                        
                        <div className="space-y-2">
                          <h4 className="font-bold text-lg text-white truncate group-hover:text-spotify-green transition-colors duration-300" title={playlist.name}>
                            {playlist.name}
                          </h4>
                          
                          <div className="flex items-center gap-2 text-sm">
                            <span className="bg-white/10 text-gray-300 px-2 py-1 rounded-lg font-medium">
                              {playlist.tracks.total} tracks
                            </span>
                            <span className="text-gray-500">•</span>
                            <span className="text-gray-400 truncate flex-1" title={`by ${playlist.owner.display_name}`}>
                              by {playlist.owner.display_name}
                            </span>
                          </div>
                          
                          <div className="pt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                            <div className="bg-gradient-to-r from-spotify-green/20 to-spotify-green/10 rounded-lg p-2 border border-spotify-green/20">
                              <p className="text-xs text-spotify-green font-medium text-center">
                                Click to analyze emotional content
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination Controls */}
                  {totalPages > 1 && (
                    <div className="bg-gradient-to-br from-spotify-dark-gray/60 to-spotify-dark-gray/30 rounded-2xl p-6 border border-white/10">
                      <div className="flex justify-center items-center gap-6">
                        <button
                          onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                          disabled={currentPage === 1}
                          className="bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-xl transition-all duration-300 hover:transform hover:scale-105 border border-white/20"
                        >
                          ← Previous
                        </button>
                        
                        <div className="flex items-center gap-3">
                          {Array.from({ length: totalPages }, (_, i) => i + 1)
                            .filter(page => {
                              // Show first page, last page, current page, and pages around current
                              return page === 1 || 
                                     page === totalPages || 
                                     Math.abs(page - currentPage) <= 1
                            })
                            .map((page, index, array) => (
                              <div key={page} className="flex items-center">
                                {index > 0 && array[index - 1] !== page - 1 && (
                                  <span className="text-gray-500 mx-2 text-lg">...</span>
                                )}
                                <button
                                  onClick={() => setCurrentPage(page)}
                                  className={`w-12 h-12 rounded-xl font-bold transition-all duration-300 hover:transform hover:scale-110 ${
                                    currentPage === page
                                      ? 'bg-gradient-to-r from-spotify-green to-spotify-green-light text-black shadow-lg shadow-spotify-green/50'
                                      : 'bg-white/10 hover:bg-white/20 text-white border border-white/20'
                                  }`}
                                >
                                  {page}
                                </button>
                              </div>
                            ))
                          }
                        </div>

                        <button
                          onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                          disabled={currentPage === totalPages}
                          className="bg-white/10 hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 px-6 rounded-xl transition-all duration-300 hover:transform hover:scale-105 border border-white/20"
                        >
                          Next →
                        </button>
                      </div>
                      
                      {/* Pagination Info */}
                      <div className="text-center text-gray-400 mt-4 font-medium">
                        Showing {startIndex + 1}-{Math.min(startIndex + playlistsPerPage, filteredPlaylists.length)} of {filteredPlaylists.length} playlists
                        {totalPages > 1 && (
                          <span className="text-spotify-green"> • Page {currentPage} of {totalPages}</span>
                        )}
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>
      </div>
    </main>
  )
} 