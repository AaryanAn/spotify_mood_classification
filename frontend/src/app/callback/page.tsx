'use client'

import { useEffect, useState, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'

export default function CallbackPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('Processing your login...')
  const searchParams = useSearchParams()
  const router = useRouter()
  const isProcessing = useRef(false)

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent duplicate processing
      if (isProcessing.current) {
        return
      }
      isProcessing.current = true
      try {
        const code = searchParams.get('code')
        const state = searchParams.get('state')
        const error = searchParams.get('error')

        if (error) {
          throw new Error(`Spotify authorization failed: ${error}`)
        }

        if (!code || !state) {
          throw new Error('Missing authorization code or state')
        }

        setMessage('Waking up server and exchanging authorization code...')

        // First ensure backend is awake (critical for authorization code timing)
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://spotify-mood-classification.onrender.com'
        
        try {
          const healthController = new AbortController()
          const healthTimeoutId = setTimeout(() => healthController.abort(), 45000) // 45s timeout
          
          await fetch(`${API_URL}/api/health`, {
            signal: healthController.signal
          })
          clearTimeout(healthTimeoutId)
          setMessage('Server ready! Exchanging authorization code...')
        } catch (healthError) {
          console.warn('Health check failed during callback, but continuing...', healthError)
          setMessage('Exchanging authorization code (server may be starting up)...')
        }

        // Send code and state to backend as query parameters
        const params = new URLSearchParams({ code, state })
        
        // Use longer timeout for callback since it involves Spotify API calls
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout
        
        const response = await fetch(`${API_URL}/api/auth/callback?${params}`, {
          method: 'POST',
          signal: controller.signal,
        })
        
        clearTimeout(timeoutId)

        if (!response.ok) {
          let errorMessage = 'Authentication failed'
          try {
            const errorData = await response.json()
            if (errorData.detail) {
              errorMessage = Array.isArray(errorData.detail) 
                ? errorData.detail.map((err: any) => err.msg || err).join(', ')
                : errorData.detail
            }
          } catch (e) {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`
          }
          throw new Error(errorMessage)
        }

        const data = await response.json()
        
        // Store the access token
        localStorage.setItem('spotify_access_token', data.access_token)
        localStorage.setItem('spotify_user', JSON.stringify(data.user))

        setStatus('success')
        setMessage(`Welcome, ${data.user.display_name}! Redirecting to dashboard...`)

        // Redirect to dashboard after 2 seconds
        setTimeout(() => {
          router.push('/dashboard')
        }, 2000)

      } catch (error) {
        console.error('Callback error:', error)
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'An unknown error occurred')
        isProcessing.current = false // Reset on error so user can retry
      }
    }

    handleCallback()
  }, [searchParams, router])

  return (
    <main className="min-h-screen bg-spotify-black text-white flex items-center justify-center">
      <div className="text-center">
        <div className="mb-8">
          {status === 'loading' && (
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-spotify-green mx-auto"></div>
          )}
          {status === 'success' && (
            <div className="text-6xl text-spotify-green mb-4">✓</div>
          )}
          {status === 'error' && (
            <div className="text-6xl text-red-500 mb-4">✗</div>
          )}
        </div>
        
        <h1 className="text-2xl font-bold mb-4">
          {status === 'loading' && 'Connecting to Spotify...'}
          {status === 'success' && 'Success!'}
          {status === 'error' && 'Authentication Failed'}
        </h1>
        
        <p className="text-gray-300 mb-8 max-w-md">
          {message}
        </p>

        {status === 'error' && (
          <button
            onClick={() => router.push('/')}
            className="bg-spotify-green hover:bg-spotify-green-dark text-black font-semibold py-3 px-6 rounded-lg transition-colors"
          >
            Try Again
          </button>
        )}
      </div>
    </main>
  )
} 