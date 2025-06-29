'use client'

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <div className="text-center mb-16 fade-in">
          <div className="inline-flex items-center gap-4 mb-6">
            <div className="w-20 h-20 bg-gradient-to-br from-spotify-green to-spotify-green-light rounded-3xl flex items-center justify-center text-4xl shadow-2xl shadow-spotify-green/30">
              🧠
            </div>
          </div>
          <h1 className="text-6xl font-extrabold gradient-text mb-6">
            How Mood Analysis Works
          </h1>
          <p className="text-2xl text-gray-300 font-light leading-relaxed max-w-3xl mx-auto">
            Understanding the advanced AI technology behind your playlist mood classification system
          </p>
        </div>

        {/* Analysis Methods */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-16">
          {/* Standard Analysis */}
          <div className="glass rounded-2xl p-8 border border-white/10 card-hover">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center text-3xl shadow-lg">
                📊
              </div>
              <h2 className="text-3xl font-bold text-white">Standard Analysis</h2>
            </div>
            <p className="text-gray-300 mb-4">
              Fast analysis using genre classification and track metadata
            </p>
            
            <h3 className="font-semibold mb-2 text-spotify-green">Data Sources:</h3>
            <ul className="space-y-1 text-sm text-gray-400 mb-4">
              <li>• Genre classification (50+ genres mapped to moods)</li>
              <li>• Track duration and popularity</li>
              <li>• Release year and explicit content</li>
              <li>• Artist and album metadata</li>
            </ul>

            <h3 className="font-semibold mb-2 text-spotify-green">Processing Time:</h3>
            <p className="text-sm text-gray-400 mb-4">~1-2 seconds per playlist</p>

            <h3 className="font-semibold mb-2 text-spotify-green">Best For:</h3>
            <p className="text-sm text-gray-400">
              Quick analysis, instrumental music, large playlists
            </p>
          </div>

          {/* Enhanced Analysis */}
          <div className="glass rounded-2xl p-8 border-2 border-spotify-green card-hover shadow-2xl shadow-spotify-green/20">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-16 h-16 bg-gradient-to-br from-spotify-green to-spotify-green-light rounded-2xl flex items-center justify-center text-3xl shadow-lg">
                🎵
              </div>
              <div className="flex-1">
                <h2 className="text-3xl font-bold gradient-text">Enhanced Analysis</h2>
                <span className="bg-gradient-to-r from-spotify-green to-spotify-green-light text-black px-4 py-2 rounded-full text-sm font-bold shadow-lg mt-2 inline-block">
                  POWERED BY GENIUS API
                </span>
              </div>
            </div>
            <p className="text-gray-300 mb-4">
              Deep analysis combining metadata with lyrics sentiment analysis
            </p>
            
            <h3 className="font-semibold mb-2 text-spotify-green">Data Sources:</h3>
            <ul className="space-y-1 text-sm text-gray-400 mb-4">
              <li>• Everything from Standard Analysis (60% weight)</li>
              <li>• Lyrics sentiment analysis via VADER (40% weight)</li>
              <li>• 300+ mood-specific keywords</li>
              <li>• Emotional intensity and negation handling</li>
              <li>• Language detection and filtering</li>
            </ul>

            <h3 className="font-semibold mb-2 text-spotify-green">Processing Time:</h3>
            <p className="text-sm text-gray-400 mb-4">~5-10 seconds per playlist</p>

            <h3 className="font-semibold mb-2 text-spotify-green">Best For:</h3>
            <p className="text-sm text-gray-400">
              Vocal music, emotional analysis, maximum accuracy
            </p>
          </div>
        </div>

        {/* Mood Categories */}
        <div className="glass rounded-2xl p-8 mb-12 border border-white/10">
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center text-3xl mx-auto mb-4 shadow-lg">
              🎭
            </div>
            <h2 className="text-3xl font-bold gradient-text">Mood Categories</h2>
            <p className="text-gray-400 mt-2">8 distinct emotional classifications powered by AI</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { mood: 'happy', emoji: '😊', color: 'from-yellow-400 to-yellow-500' },
              { mood: 'sad', emoji: '😢', color: 'from-blue-400 to-blue-500' },
              { mood: 'energetic', emoji: '⚡', color: 'from-red-400 to-red-500' },
              { mood: 'calm', emoji: '😌', color: 'from-green-400 to-green-500' },
              { mood: 'angry', emoji: '😡', color: 'from-red-600 to-red-700' },
              { mood: 'romantic', emoji: '💕', color: 'from-pink-400 to-pink-500' },
              { mood: 'melancholic', emoji: '😔', color: 'from-purple-400 to-purple-500' },
              { mood: 'upbeat', emoji: '🎉', color: 'from-orange-400 to-orange-500' }
            ].map(({ mood, emoji, color }, index) => (
              <div key={mood} className="card-hover bg-gradient-to-br from-spotify-dark-gray/80 to-spotify-dark-gray/40 rounded-2xl p-5 text-center border border-white/10 fade-in" style={{ animationDelay: `${index * 0.1}s` }}>
                <div className={`w-14 h-14 bg-gradient-to-br ${color} rounded-2xl flex items-center justify-center text-2xl mx-auto mb-4 shadow-lg`}>
                  {emoji}
                </div>
                <p className="text-lg font-bold capitalize text-white">{mood}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Technical Details */}
        <div className="space-y-10">
          {/* Genre Mapping */}
          <div className="glass rounded-2xl p-8 border border-white/10 card-hover">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center text-2xl shadow-lg">
                🎼
              </div>
              <h2 className="text-2xl font-bold text-white">Genre-to-Mood Mapping</h2>
            </div>
            <p className="text-gray-300 mb-4">
              Our system maps over 50 music genres to emotional characteristics:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h3 className="font-semibold text-spotify-green mb-2">Example Mappings:</h3>
                <ul className="space-y-1 text-gray-400">
                  <li>• <strong>Jazz, Blues:</strong> Sophisticated, Romantic</li>
                  <li>• <strong>EDM, Techno:</strong> Energetic, Upbeat</li>
                  <li>• <strong>Classical, Ambient:</strong> Calm, Contemplative</li>
                  <li>• <strong>Metal, Punk:</strong> Angry, Energetic</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-spotify-green mb-2">Weighting Factors:</h3>
                <ul className="space-y-1 text-gray-400">
                  <li>• Primary genre: 70% influence</li>
                  <li>• Secondary genres: 30% influence</li>
                  <li>• Track popularity: Confidence modifier</li>
                  <li>• Release era: Contextual adjustment</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Lyrics Analysis */}
          <div className="glass rounded-2xl p-8 border border-white/10 card-hover">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 bg-gradient-to-br from-orange-500 to-orange-600 rounded-2xl flex items-center justify-center text-2xl shadow-lg">
                📝
              </div>
              <h2 className="text-2xl font-bold text-white">Lyrics Sentiment Analysis</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-semibold text-spotify-green mb-3">VADER Sentiment Analysis:</h3>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li>• <strong>Compound Score:</strong> Overall sentiment (-1 to +1)</li>
                  <li>• <strong>Positive:</strong> Joy, excitement, love keywords</li>
                  <li>• <strong>Negative:</strong> Sadness, anger, fear keywords</li>
                  <li>• <strong>Neutral:</strong> Descriptive, non-emotional content</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-spotify-green mb-3">Advanced Processing:</h3>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li>• <strong>Intensifiers:</strong> "very", "extremely" boost scores</li>
                  <li>• <strong>Negation:</strong> "not happy" flips sentiment</li>
                  <li>• <strong>Mood Keywords:</strong> 300+ emotion-specific terms</li>
                  <li>• <strong>Language Filter:</strong> English lyrics only</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Confidence Scoring */}
          <div className="glass rounded-2xl p-8 border border-white/10 card-hover">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center text-2xl shadow-lg">
                🎯
              </div>
              <h2 className="text-2xl font-bold text-white">Confidence Scoring</h2>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div className="text-center p-3 bg-red-900/30 rounded">
                  <div className="text-red-400 font-bold">LOW (0-40%)</div>
                  <p className="text-gray-400 mt-1">Mixed genres, unclear sentiment</p>
                </div>
                <div className="text-center p-3 bg-yellow-900/30 rounded">
                  <div className="text-yellow-400 font-bold">MEDIUM (40-70%)</div>
                  <p className="text-gray-400 mt-1">Consistent patterns, some ambiguity</p>
                </div>
                <div className="text-center p-3 bg-green-900/30 rounded">
                  <div className="text-green-400 font-bold">HIGH (70-100%)</div>
                  <p className="text-gray-400 mt-1">Clear mood signals, strong consensus</p>
                </div>
              </div>
              <p className="text-gray-300 text-sm">
                <strong>Enhanced Analysis</strong> typically achieves 20-30% higher confidence scores 
                due to lyrics providing additional emotional context.
              </p>
            </div>
          </div>

          {/* Technical Stack */}
          <div className="glass rounded-2xl p-8 border border-white/10 card-hover">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-14 h-14 bg-gradient-to-br from-cyan-500 to-cyan-600 rounded-2xl flex items-center justify-center text-2xl shadow-lg">
                ⚙️
              </div>
              <h2 className="text-2xl font-bold text-white">Technical Implementation</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div>
                <h3 className="font-semibold text-spotify-green mb-3">Backend Technologies:</h3>
                <ul className="space-y-1 text-gray-400">
                  <li>• <strong>FastAPI:</strong> High-performance async API</li>
                  <li>• <strong>SQLAlchemy:</strong> Database ORM with PostgreSQL</li>
                  <li>• <strong>Redis:</strong> Caching for lyrics and results</li>
                  <li>• <strong>NLTK:</strong> Natural language processing</li>
                  <li>• <strong>scikit-learn:</strong> Machine learning pipeline</li>
                </ul>
              </div>
              <div>
                <h3 className="font-semibold text-spotify-green mb-3">External APIs:</h3>
                <ul className="space-y-1 text-gray-400">
                  <li>• <strong>Spotify Web API:</strong> Track and playlist data</li>
                  <li>• <strong>Genius API:</strong> Lyrics and metadata</li>
                  <li>• <strong>OAuth 2.0:</strong> Secure authentication</li>
                  <li>• <strong>Rate Limiting:</strong> API usage optimization</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="text-center mt-16">
          <a 
            href="/dashboard" 
            className="btn-primary text-black font-bold py-4 px-12 rounded-2xl text-lg transition-all duration-300 inline-flex items-center gap-3 hover:shadow-2xl hover:shadow-spotify-green/50"
          >
            <span>←</span>
            Back to Dashboard
          </a>
        </div>
      </div>
    </main>
  )
} 