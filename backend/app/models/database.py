"""
Database configuration and base models
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, String, Text, Float, Boolean, Integer, JSON, event
from datetime import datetime
from typing import Optional, Any, Dict
import structlog
import asyncpg

from app.utils.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Create asyncpg pool directly to bypass pgbouncer prepared statement issues
_asyncpg_pool = None

async def get_asyncpg_pool():
    """Get or create the global asyncpg connection pool"""
    global _asyncpg_pool
    if _asyncpg_pool is None:
        # Ensure we use clean postgresql:// format for asyncpg (not postgresql+asyncpg://)
        clean_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        _asyncpg_pool = await asyncpg.create_pool(
            clean_database_url,
            statement_cache_size=0,  # Critical: disable prepared statements for pgbouncer
            min_size=1,
            max_size=20,
            command_timeout=60,
            server_settings={
                'jit': 'off',
                'application_name': 'spotify_mood_classifier'
            }
        )
    return _asyncpg_pool

async def close_asyncpg_pool():
    """Close the asyncpg connection pool"""
    global _asyncpg_pool
    if _asyncpg_pool:
        await _asyncpg_pool.close()
        _asyncpg_pool = None

# Create simple async engine for SQLAlchemy operations
# We'll use the asyncpg pool for database initialization to avoid prepared statements issue
database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create session factory
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base model class"""
    pass


class User(Base):
    """User model for storing Spotify user information"""
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Spotify user ID
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(10))
    followers: Mapped[Optional[int]] = mapped_column(Integer)
    spotify_url: Mapped[Optional[str]] = mapped_column(String(200))
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Playlist(Base):
    """Playlist model for storing playlist information"""
    __tablename__ = "playlists"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Spotify playlist ID
    user_id: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    tracks_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    spotify_url: Mapped[str] = mapped_column(String(200))
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class Track(Base):
    """Track model for storing track information and metadata for mood analysis"""
    __tablename__ = "tracks"
    
    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # Spotify track ID
    name: Mapped[str] = mapped_column(String(200))
    artist: Mapped[str] = mapped_column(String(200))
    album: Mapped[str] = mapped_column(String(200))
    duration_ms: Mapped[int] = mapped_column(Integer)
    popularity: Mapped[Optional[int]] = mapped_column(Integer)
    explicit: Mapped[bool] = mapped_column(Boolean, default=False)
    spotify_url: Mapped[str] = mapped_column(String(200))
    preview_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Genre and metadata information for mood analysis
    genres: Mapped[Optional[str]] = mapped_column(Text)  # JSON string of genre list
    artist_popularity: Mapped[Optional[int]] = mapped_column(Integer)
    artist_followers: Mapped[Optional[int]] = mapped_column(Integer)
    release_year: Mapped[Optional[int]] = mapped_column(Integer)
    release_date: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Audio features from Spotify API (deprecated but kept for backward compatibility)
    acousticness: Mapped[Optional[float]] = mapped_column(Float)
    danceability: Mapped[Optional[float]] = mapped_column(Float)
    energy: Mapped[Optional[float]] = mapped_column(Float)
    instrumentalness: Mapped[Optional[float]] = mapped_column(Float)
    liveness: Mapped[Optional[float]] = mapped_column(Float)
    loudness: Mapped[Optional[float]] = mapped_column(Float)
    speechiness: Mapped[Optional[float]] = mapped_column(Float)
    tempo: Mapped[Optional[float]] = mapped_column(Float)
    valence: Mapped[Optional[float]] = mapped_column(Float)
    key: Mapped[Optional[int]] = mapped_column(Integer)
    mode: Mapped[Optional[int]] = mapped_column(Integer)
    time_signature: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlaylistTrack(Base):
    """Junction table for playlist-track relationships"""
    __tablename__ = "playlist_tracks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[str] = mapped_column(String(50))
    track_id: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MoodAnalysis(Base):
    """Model for storing mood analysis results using genre-metadata approach"""
    __tablename__ = "mood_analyses"
    
    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # Custom ID format
    playlist_id: Mapped[str] = mapped_column(String(50))
    user_id: Mapped[str] = mapped_column(String(50))
    
    # Mood classification results
    primary_mood: Mapped[str] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Float)  # Renamed from mood_confidence
    mood_distribution: Mapped[Optional[str]] = mapped_column(Text)  # JSON string
    
    # Analysis metadata
    tracks_analyzed: Mapped[int] = mapped_column(Integer)
    analysis_method: Mapped[str] = mapped_column(String(50))  # e.g., "genre-metadata-analysis"
    analysis_data: Mapped[Optional[str]] = mapped_column(Text)  # JSON string with analysis details
    
    # Deprecated audio features (kept for backward compatibility)
    avg_valence: Mapped[Optional[float]] = mapped_column(Float)
    avg_energy: Mapped[Optional[float]] = mapped_column(Float)
    avg_danceability: Mapped[Optional[float]] = mapped_column(Float)
    avg_acousticness: Mapped[Optional[float]] = mapped_column(Float)
    avg_tempo: Mapped[Optional[float]] = mapped_column(Float)
    
    # Legacy fields (kept for backward compatibility)
    mood_confidence: Mapped[Optional[float]] = mapped_column(Float)  # Deprecated, use 'confidence'
    model_version: Mapped[Optional[str]] = mapped_column(String(20))
    analysis_duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def get_db() -> AsyncSession:
    """Get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables using asyncpg pool to avoid prepared statements issue"""
    try:
        # Use our working asyncpg pool for everything
        pool = await get_asyncpg_pool()
        async with pool.acquire() as conn:
            # Test the connection with a simple query
            version = await conn.fetchval("SELECT version()")
            logger.info("✅ Database connection test successful", version=version[:50])
            
            # Create tables using raw SQL through our working asyncpg pool
            # This completely bypasses SQLAlchemy's prepared statements issue
            
            # Generate DDL SQL from SQLAlchemy metadata
            from sqlalchemy.schema import CreateTable
            from sqlalchemy.dialects import postgresql
            
            # Create tables one by one using raw SQL
            for table in Base.metadata.tables.values():
                # Check if table exists first
                table_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                    table.name
                )
                
                if not table_exists:
                    create_sql = str(CreateTable(table).compile(dialect=postgresql.dialect()))
                    await conn.execute(create_sql)
                    logger.info(f"✅ Created table: {table.name}")
                else:
                    logger.info(f"⏭️ Table already exists: {table.name}")
            
            logger.info("✅ Database tables created successfully")
        
        logger.info("✅ Database initialized successfully")
        
    except Exception as e:
        logger.error("❌ Database initialization failed", error=str(e))
        raise 