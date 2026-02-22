"""
NyayamGPT - Core Configuration Module
=====================================
Centralized configuration management using Pydantic Settings.
All environment variables and application settings are defined here.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        app_name: Name of the application
        app_version: Current version of the application
        debug: Enable debug mode
        environment: Deployment environment (development, staging, production)
        
        # API Keys
        gemini_api_key: Google Gemini API key for LLM operations
        
        # Database
        database_url: PostgreSQL or SQLite connection string
        
        # Vector Store
        vector_db_path: Path to the vector database storage
        vector_store_type: Type of vector store (chroma or faiss)
        
        # Embedding Model
        embedding_model: HuggingFace embedding model name
        
        # Server
        host: Server host address
        port: Server port number
        
        # CORS
        cors_origins: Allowed CORS origins
        
        # RAG Settings
        retrieval_top_k: Number of documents to retrieve
        max_validation_attempts: Maximum validation loop iterations
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="NyayamGPT", description="Application name")
    app_version: str = Field(default="2.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", 
        description="Deployment environment"
    )
    
    # API Keys
    gemini_api_key: str = Field(..., validation_alias=AliasChoices("gemini_api_key", "GOOGLE_API_KEY", "GEMINI_API_KEY"), description="Google Gemini API key")
    gemini_fallback_keys: str = Field(
        default="",
        validation_alias=AliasChoices("gemini_fallback_keys", "GEMINI_FALLBACK_KEYS"),
        description="Comma-separated list of fallback Gemini API keys"
    )
    indian_kanoon_token: str = Field(
        default="",
        description="Indian Kanoon API token for legal document search"
    )
    
    # JWT / Authentication
    jwt_secret_key: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="Algorithm for JWT token signing"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    
    # Database
    database_url: str = Field(
        default="sqlite:///./nyayamgpt.db",
        description="Database connection string"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string"
    )
    
    # Vector Store
    vector_db_path: str = Field(
        default="./data/vectorstore",
        description="Path to vector database"
    )
    vector_store_type: Literal["chroma", "faiss"] = Field(
        default="chroma",
        description="Vector store type"
    )
    
    # Embedding Model
    embedding_model: str = Field(
        default="intfloat/e5-base-v2",
        description="HuggingFace embedding model"
    )
    embedding_dimension: int = Field(
        default=768,
        description="Embedding vector dimension"
    )
    
    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )
    
    # RAG Settings
    retrieval_top_k: int = Field(
        default=10,
        description="Number of documents to retrieve"
    )
    max_validation_attempts: int = Field(
        default=1,
        description="Maximum validation loop iterations (reduced from 3 for speed)"
    )
    chunk_size: int = Field(
        default=1000,
        description="Document chunk size for indexing"
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks"
    )
    
    # Gemini Model Settings (Free Tier Models)
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Primary Gemini model - gemini-2.5-flash is the latest and best free model"
    )
    gemini_fallback_models: str = Field(
        default="gemini-2.0-flash,gemini-2.5-pro,gemini-2.0-flash-lite",
        description="Comma-separated list of fallback Gemini models (all currently available)"
    )
    gemini_temperature: float = Field(
        default=0.1,
        description="Temperature for Gemini responses"
    )
    gemini_max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for Gemini responses (reduced for quota optimization)"
    )

    @property
    def all_gemini_keys(self) -> list[str]:
        """Get all configured Gemini API keys including fallbacks."""
        keys = [self.gemini_api_key]
        if self.gemini_fallback_keys:
            keys.extend([k.strip() for k in self.gemini_fallback_keys.split(",") if k.strip()])
        return keys

    @property
    def all_gemini_models(self) -> list[str]:
        """Get all configured Gemini models including fallbacks."""
        models = [self.gemini_model]
        if self.gemini_fallback_models:
            models.extend([m.strip() for m in self.gemini_fallback_models.split(",") if m.strip()])
        return models


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings singleton
    """
    return Settings()


# Global settings instance
settings = get_settings()
