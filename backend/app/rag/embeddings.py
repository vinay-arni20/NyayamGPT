"""
NyayamGPT - Embeddings Module
=============================
Text embedding generation using HuggingFace models for vector search.
"""

import os
from typing import Optional, TYPE_CHECKING

import numpy as np

# Avoid Keras 3 compatibility issues by setting env var before import
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

from app.core.config import settings
from app.core.logging import logger

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """
    Service for generating text embeddings using HuggingFace models.
    
    Attributes:
        model: SentenceTransformer model instance
        model_name: Name of the embedding model
        dimension: Embedding vector dimension
    """
    
    _instance: Optional["EmbeddingService"] = None
    _model: Optional["SentenceTransformer"] = None
    
    def __new__(cls) -> "EmbeddingService":
        """Singleton pattern to avoid loading model multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize the embedding model."""
        if self._initialized:
            return
            
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._initialized = True
    
    @property
    def model(self) -> "SentenceTransformer":
        """Lazy load the SentenceTransformer model."""
        if self._model is None:
            # Import here to avoid Keras 3 issues at module load time
            from sentence_transformers import SentenceTransformer
            
            logger.info(
                "Loading embedding model",
                model=self.model_name
            )
            
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    trust_remote_code=True
                )
                
                logger.info(
                    "Embedding model loaded successfully",
                    model=self.model_name,
                    dimension=self.dimension
                )
            except Exception as e:
                logger.error(
                    "Failed to load embedding model",
                    model=self.model_name,
                    error=str(e)
                )
                raise
        return self._model
    
    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            list[float]: Embedding vector
        """
        # Add instruction prefix for e5 models
        if "e5" in self.model_name.lower():
            text = f"query: {text}"
        
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        return embedding.tolist()
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            list[list[float]]: List of embedding vectors
        """
        # Add instruction prefix for e5 models
        if "e5" in self.model_name.lower():
            texts = [f"query: {t}" for t in texts]
        
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        return embeddings.tolist()
    
    def embed_document(self, text: str) -> list[float]:
        """
        Generate embedding for a document (different prefix for e5 models).
        
        Args:
            text: Document text to embed
            
        Returns:
            list[float]: Embedding vector
        """
        # Add instruction prefix for e5 models
        if "e5" in self.model_name.lower():
            text = f"passage: {text}"
        
        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        
        return embedding.tolist()
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple documents.
        
        Args:
            texts: List of document texts
            
        Returns:
            list[list[float]]: List of embedding vectors
        """
        # Add instruction prefix for e5 models
        if "e5" in self.model_name.lower():
            texts = [f"passage: {t}" for t in texts]
        
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        return embeddings.tolist()
    
    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float]
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


def get_embedding_service() -> EmbeddingService:
    """
    Get the singleton embedding service instance.
    
    Returns:
        EmbeddingService: Embedding service instance
    """
    return EmbeddingService()


# Convenience functions
def embed_text(text: str) -> list[float]:
    """
    Embed a single text string.
    
    Args:
        text: Input text
        
    Returns:
        list[float]: Embedding vector
    """
    return get_embedding_service().embed_text(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple text strings.
    
    Args:
        texts: List of input texts
        
    Returns:
        list[list[float]]: List of embedding vectors
    """
    return get_embedding_service().embed_texts(texts)


def embed_document(text: str) -> list[float]:
    """
    Embed a document text.
    
    Args:
        text: Document text
        
    Returns:
        list[float]: Embedding vector
    """
    return get_embedding_service().embed_document(text)


def embed_documents(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple documents.
    
    Args:
        texts: List of document texts
        
    Returns:
        list[list[float]]: List of embedding vectors
    """
    return get_embedding_service().embed_documents(texts)
