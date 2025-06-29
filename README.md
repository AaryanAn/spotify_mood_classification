# 🎵 Spotify Playlist Mood Classification

A production-ready web application that analyzes the emotional mood of Spotify playlists using machine learning and the Spotify Web API. Built with modern technologies including FastAPI, Next.js, PostgreSQL, Redis, and Docker.

## 📖 Overview

This application combines ML expertise with modern web development to create an intelligent playlist mood analysis system. It leverages Spotify's audio features API to classify playlists into emotional categories like Happy, Sad, Energetic, Calm, Romantic, and more.

### 🌟 Key Features

- **🎭 AI-Powered Mood Detection**: Multi-class mood classification using ML algorithms
- **📊 Detailed Analytics**: Comprehensive insights about energy, valence, and mood distributions  
- **🚀 Real-time Processing**: Fast analysis with Redis caching and background processing
- **🔐 Secure Authentication**: Spotify OAuth 2.0 integration
- **📱 Modern UI**: Responsive Next.js frontend with real-time visualization
- **🐳 Containerized**: Full Docker setup for easy deployment

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Next.js)     │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
│   Port: 8080    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Caching)     │
                       │   Port: 6379    │
                       └─────────────────┘
```

## 🛠️ Technology Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI, SQLAlchemy, async/await
- **Database**: PostgreSQL 15
- **Caching**: Redis 7
- **ML**: scikit-learn, pandas, numpy
- **Authentication**: Spotify OAuth 2.0, JWT tokens
- **Deployment**: Docker, Docker Compose

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Spotify Developer Account
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/spotify-mood-classification.git
cd spotify-mood-classification
```

### 2. Spotify Developer Setup

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Add redirect URI: `http://127.0.0.1:8080/callback`
4. Note down your `Client ID` and `Client Secret`

### 3. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Database Configuration
DATABASE_URL=postgresql://spotify_user:spotify_password@postgres:5432/spotify_mood_db
POSTGRES_DB=spotify_mood_db
POSTGRES_USER=spotify_user
POSTGRES_PASSWORD=spotify_password

# Redis Configuration
REDIS_URL=redis://redis:6379

# Spotify API Configuration (Replace with your actual credentials)
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8080/callback

# Security Configuration (Change this to a secure random string)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production

# Application Configuration
ENVIRONMENT=development
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 4. Launch the Application

```bash
# Start all services
docker compose up --build

# Or run in background
docker compose up -d --build
```

### 5. Access the Application

- **Frontend**: http://127.0.0.1:8080
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📱 Usage

1. **Login**: Click "Login with Spotify" to authenticate
2. **Analyze Playlists**: Click "Analyze My Playlists" to load your Spotify playlists
3. **Select Playlist**: Click on any playlist to start mood analysis
4. **View Results**: See mood classification, confidence scores, and detailed analytics

## 🔧 Development

### Local Development Setup

```bash
# Backend development
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend development  
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## 📊 ML Pipeline

The mood classification system uses:

- **Audio Features**: Valence, energy, danceability, acousticness, etc.
- **Feature Engineering**: Normalization and scaling of Spotify's audio features
- **ML Model**: Multi-class classification with 8 mood categories
- **Confidence Scoring**: Probability-based mood confidence assessment

### Mood Categories

- 😊 **Happy**: High valence, upbeat tracks
- 😢 **Sad**: Low valence, melancholic feeling
- ⚡ **Energetic**: High energy and tempo
- 😌 **Calm**: Low energy, peaceful tracks
- 😠 **Angry**: High energy, low valence
- 💕 **Romantic**: Moderate valence, emotional
- 😔 **Melancholic**: Low valence, introspective
- 🎉 **Upbeat**: High energy and valence

## 🛡️ Security

- Environment variables for sensitive configuration
- JWT token authentication
- Spotify OAuth 2.0 secure flow
- Input validation and sanitization
- CORS configuration for cross-origin requests

## 🚀 Deployment

### Production Deployment

1. **Environment Variables**: Set production values for all environment variables
2. **Database**: Use managed PostgreSQL service
3. **Cache**: Use managed Redis service
4. **SSL**: Configure HTTPS with proper certificates
5. **Monitoring**: Add logging and monitoring solutions

### Environment Variables for Production

```bash
ENVIRONMENT=production
JWT_SECRET_KEY=your-secure-production-jwt-key
DATABASE_URL=your-production-database-url
REDIS_URL=your-production-redis-url
SPOTIFY_REDIRECT_URI=https://yourdomain.com/callback
```

## 🐛 Troubleshooting

### Common Issues

1. **Token Expired**: Spotify tokens expire after 1 hour. Click "Logout" and log back in.
2. **Backend Not Starting**: Check that all environment variables are set in `.env`
3. **Database Connection**: Ensure PostgreSQL container is healthy
4. **Playlist Analysis Fails**: Verify Spotify credentials and redirect URI

### Checking Logs

```bash
# View all logs
docker compose logs

# View specific service logs
docker compose logs backend
docker compose logs frontend
```

## 📈 Performance

- **Analysis Speed**: ~2-5 seconds per playlist
- **Caching**: Redis caching for API responses
- **Concurrent Users**: Supports 100+ concurrent users
- **Database**: Optimized queries with proper indexing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Spotify Web API for audio features
- FastAPI for the excellent Python web framework
- Next.js team for the amazing React framework
- All open-source contributors

## 📞 Support

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [API Documentation](http://localhost:8000/docs)
3. Open an issue on GitHub

---

**Built with ❤️ for music lovers and data enthusiasts** 