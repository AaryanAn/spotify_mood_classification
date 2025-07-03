'use client'

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-4 py-12 max-w-6xl">
        {/* Hero Section */}
        <div className="text-center mb-20 fade-in">
          <div className="inline-flex items-center gap-4 mb-8">
            <div className="w-24 h-24 bg-gradient-to-br from-spotify-green to-spotify-green-light rounded-3xl flex items-center justify-center text-5xl shadow-2xl shadow-spotify-green/30 animate-float">
              🎵
            </div>
          </div>
          <h1 className="text-6xl md:text-7xl font-extrabold gradient-text mb-8">
            The Science Behind<br />Your Music's Mood
          </h1>
          <p className="text-2xl text-gray-300 font-light leading-relaxed max-w-3xl mx-auto">
            Discover how our AI combines audio features, lyrics, and genre analysis to reveal the emotional essence of your playlists.
          </p>
        </div>

        {/* Process Steps */}
        <div className="space-y-24 mb-24">
          {/* Step 1: Data Collection */}
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="glass rounded-3xl p-8 order-2 md:order-1">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-3 text-spotify-green">
                  <span className="text-xl font-bold">Step 1</span>
                  <div className="h-px bg-spotify-green flex-1 opacity-30"></div>
                </div>
                <h2 className="text-4xl font-bold mb-6">Data Collection</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  When you select a playlist, our system gathers rich data from multiple sources:
                </p>
                <div className="grid gap-4">
                  <div className="glass p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">🎹</span>
                      <h3 className="font-semibold text-white">Audio Features</h3>
                    </div>
                    <p className="text-sm text-gray-400">
                      Tempo, key, energy, danceability, and more from Spotify's audio analysis
                    </p>
                  </div>
                  <div className="glass p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">📝</span>
                      <h3 className="font-semibold text-white">Lyrics & Context</h3>
                    </div>
                    <p className="text-sm text-gray-400">
                      Song lyrics and metadata from Genius for deeper emotional context
                    </p>
                  </div>
                  <div className="glass p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-2xl">🎸</span>
                      <h3 className="font-semibold text-white">Genre Analysis</h3>
                    </div>
                    <p className="text-sm text-gray-400">
                      Genre classifications and sub-genres for mood correlation
                    </p>
                  </div>
                </div>
              </div>
            </div>
            <div className="relative order-1 md:order-2">
              <div className="absolute inset-0 bg-gradient-to-br from-spotify-green/20 to-transparent rounded-3xl blur-3xl"></div>
              <div className="glass rounded-3xl p-8 relative">
                <pre className="text-sm font-mono text-gray-300 overflow-x-auto">
                  <code>{`{
  "track": "Dreams",
  "artist": "Fleetwood Mac",
  "features": {
    "tempo": 120,
    "energy": 0.815,
    "valence": 0.93,
    "danceability": 0.78
  },
  "genres": [
    "classic rock",
    "soft rock"
  ],
  "lyrics_sentiment": {
    "positive": 0.72,
    "neutral": 0.18,
    "negative": 0.10
  }
}`}</code>
                </pre>
              </div>
            </div>
          </div>

          {/* Step 2: AI Processing */}
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-br from-purple-500/20 to-transparent rounded-3xl blur-3xl"></div>
              <div className="glass rounded-3xl p-8 relative">
                <div className="space-y-4">
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-purple-400">🤖 AI Model</span>
                    <div className="h-px bg-purple-400/30 flex-1"></div>
                    <span className="text-purple-400">Processing</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { label: 'Audio Analysis', progress: 100 },
                      { label: 'Lyrics Processing', progress: 85 },
                      { label: 'Genre Classification', progress: 92 },
                      { label: 'Mood Mapping', progress: 78 }
                    ].map((item) => (
                      <div key={item.label}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-gray-400">{item.label}</span>
                          <span className="text-spotify-green">{item.progress}%</span>
                        </div>
                        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-spotify-green to-spotify-green-light"
                            style={{ width: `${item.progress}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="glass rounded-3xl p-8">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-3 text-spotify-green">
                  <span className="text-xl font-bold">Step 2</span>
                  <div className="h-px bg-spotify-green flex-1 opacity-30"></div>
                </div>
                <h2 className="text-4xl font-bold mb-6">AI Processing</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  Our advanced AI models analyze multiple data points to understand your music's emotional context:
                </p>
                <div className="space-y-4">
                  <div className="glass p-4 rounded-xl">
                    <h3 className="font-semibold text-white mb-2">VADER Sentiment Analysis</h3>
                    <p className="text-sm text-gray-400">
                      Processes lyrics to detect emotional intensity, context, and linguistic nuances
                    </p>
                  </div>
                  <div className="glass p-4 rounded-xl">
                    <h3 className="font-semibold text-white mb-2">Genre-Mood Correlation</h3>
                    <p className="text-sm text-gray-400">
                      Maps musical genres to emotional states using our extensive classification system
                    </p>
                  </div>
                  <div className="glass p-4 rounded-xl">
                    <h3 className="font-semibold text-white mb-2">Feature Analysis</h3>
                    <p className="text-sm text-gray-400">
                      Evaluates audio characteristics to determine energy, valence, and overall mood
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Step 3: Results */}
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="glass rounded-3xl p-8 order-2 md:order-1">
              <div className="space-y-6">
                <div className="inline-flex items-center gap-3 text-spotify-green">
                  <span className="text-xl font-bold">Step 3</span>
                  <div className="h-px bg-spotify-green flex-1 opacity-30"></div>
                </div>
                <h2 className="text-4xl font-bold mb-6">Mood Profile</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  Your playlist's emotional fingerprint is revealed through:
                </p>
                <div className="space-y-6">
                  <div className="glass p-6 rounded-xl">
                    <h3 className="font-semibold text-white mb-4">Primary Mood</h3>
                    <div className="flex items-center gap-4">
                      <div className="w-16 h-16 bg-gradient-to-br from-yellow-400 to-yellow-500 rounded-2xl flex items-center justify-center text-3xl">
                        😊
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-white mb-1">Happy</div>
                        <div className="text-sm text-gray-400">92% Confidence</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="glass p-6 rounded-xl">
                    <h3 className="font-semibold text-white mb-4">Mood Distribution</h3>
                    <div className="space-y-3">
                      {[
                        { mood: 'Happy', percent: 45, color: 'from-yellow-400' },
                        { mood: 'Energetic', percent: 30, color: 'from-red-400' },
                        { mood: 'Romantic', percent: 15, color: 'from-pink-400' },
                        { mood: 'Calm', percent: 10, color: 'from-blue-400' }
                      ].map((item) => (
                        <div key={item.mood}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="text-gray-300">{item.mood}</span>
                            <span className="text-gray-400">{item.percent}%</span>
                          </div>
                          <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                            <div 
                              className={`h-full bg-gradient-to-r ${item.color} to-transparent`}
                              style={{ width: `${item.percent}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="relative order-1 md:order-2">
              <div className="absolute inset-0 bg-gradient-to-br from-yellow-500/20 to-transparent rounded-3xl blur-3xl"></div>
              <div className="glass rounded-3xl p-8 relative">
                <div className="text-center">
                  <div className="inline-flex items-center justify-center w-24 h-24 bg-gradient-to-br from-yellow-400 to-yellow-500 rounded-3xl mb-6">
                    <span className="text-5xl">😊</span>
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">Happy & Uplifting</h3>
                  <p className="text-gray-400 mb-6">Your playlist radiates positive energy!</p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="glass p-3 rounded-xl">
                      <div className="text-spotify-green font-semibold mb-1">Energy</div>
                      <div className="text-gray-300">High (85%)</div>
                    </div>
                    <div className="glass p-3 rounded-xl">
                      <div className="text-spotify-green font-semibold mb-1">Valence</div>
                      <div className="text-gray-300">Positive (92%)</div>
                    </div>
                    <div className="glass p-3 rounded-xl">
                      <div className="text-spotify-green font-semibold mb-1">Tempo</div>
                      <div className="text-gray-300">Upbeat (128 BPM)</div>
                    </div>
                    <div className="glass p-3 rounded-xl">
                      <div className="text-spotify-green font-semibold mb-1">Dance</div>
                      <div className="text-gray-300">Very High (88%)</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Final CTA */}
        <div className="text-center">
          <div className="glass rounded-3xl p-12 max-w-3xl mx-auto">
            <h2 className="text-4xl font-bold mb-6">Ready to Analyze Your Music?</h2>
            <p className="text-xl text-gray-300 mb-8">
              Connect your Spotify account and discover the emotional journey hidden in your playlists.
            </p>
            <button 
              onClick={() => window.location.href = '/dashboard'}
              className="bg-spotify-green hover:bg-spotify-green-dark text-black font-bold py-4 px-8 rounded-xl text-lg transition-all"
            >
              Start Analyzing
            </button>
          </div>
        </div>
      </div>
    </main>
  )
} 