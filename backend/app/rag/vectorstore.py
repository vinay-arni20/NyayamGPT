"""
NyayamGPT - Vector Store Module
===============================
Vector database operations using ChromaDB or FAISS for semantic search.
"""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.rag.embeddings import get_embedding_service


class DocumentMetadata:
    """
    Metadata for a legal document in the vector store.
    
    Attributes:
        law: Name of the law (e.g., IPC, CrPC)
        section: Section number/identifier
        title: Section title
        source_url: Official source URL
        doc_id: Database document ID
    """
    
    def __init__(
        self,
        law: str,
        section: str,
        title: str,
        source_url: Optional[str] = None,
        doc_id: Optional[str] = None
    ) -> None:
        self.law = law
        self.section = section
        self.title = title
        self.source_url = source_url
        self.doc_id = doc_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "law": self.law,
            "section": self.section,
            "title": self.title,
            "source_url": self.source_url or "",
            "doc_id": self.doc_id or ""
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DocumentMetadata":
        """Create from dictionary."""
        return cls(
            law=data.get("law", ""),
            section=data.get("section", ""),
            title=data.get("title", ""),
            source_url=data.get("source_url"),
            doc_id=data.get("doc_id")
        )


class SearchResult:
    """
    Result from a vector search.
    
    Attributes:
        text: Document text content
        metadata: Document metadata
        score: Similarity score
        embedding_id: Vector store ID
    """
    
    def __init__(
        self,
        text: str,
        metadata: DocumentMetadata,
        score: float,
        embedding_id: str
    ) -> None:
        self.text = text
        self.metadata = metadata
        self.score = score
        self.embedding_id = embedding_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "metadata": self.metadata.to_dict(),
            "score": self.score,
            "embedding_id": self.embedding_id
        }


class VectorStoreBase(ABC):
    """Abstract base class for vector stores."""
    
    @abstractmethod
    def add_documents(
        self,
        texts: list[str],
        metadatas: list[DocumentMetadata],
        ids: Optional[list[str]] = None
    ) -> list[str]:
        """Add documents to the vector store."""
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def delete(self, ids: list[str]) -> bool:
        """Delete documents by ID."""
        pass
    
    @abstractmethod
    def get_collection_stats(self) -> dict[str, Any]:
        """Get collection statistics."""
        pass


class ChromaVectorStore(VectorStoreBase):
    """
    ChromaDB vector store implementation.
    
    ChromaDB is the default vector store for NyayamGPT, providing
    persistent storage and efficient similarity search.
    """
    
    def __init__(
        self,
        collection_name: str = "legal_documents",
        persist_directory: Optional[str] = None
    ) -> None:
        """
        Initialize ChromaDB vector store.
        
        Args:
            collection_name: Name of the collection
            persist_directory: Directory for persistent storage
        """
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory or settings.vector_db_path
        
        # Ensure directory exists
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Embedding service
        self.embedding_service = get_embedding_service()
        
        logger.info(
            "ChromaDB initialized",
            collection=collection_name,
            path=self.persist_directory,
            count=self.collection.count()
        )
    
    def add_documents(
        self,
        texts: list[str],
        metadatas: list[DocumentMetadata],
        ids: Optional[list[str]] = None
    ) -> list[str]:
        """
        Add documents to ChromaDB.
        
        Args:
            texts: List of document texts
            metadatas: List of document metadata
            ids: Optional list of document IDs
            
        Returns:
            list[str]: List of document IDs
        """
        if not texts:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Generate embeddings
        embeddings = self.embedding_service.embed_documents(texts)
        
        # Convert metadata to dicts
        metadata_dicts = [m.to_dict() for m in metadatas]
        
        # Add to collection
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadata_dicts
        )
        
        logger.info(
            "Documents added to ChromaDB",
            count=len(texts)
        )
        
        return ids
    
    def search(
        self,
        query: str,
        k: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return (default increased to 10 for better context)
            filter_metadata: Optional metadata filter
            
        Returns:
            list[SearchResult]: Search results
        """
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Build where clause for filtering
        where = None
        if filter_metadata:
            where = filter_metadata
        
        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Convert to SearchResult objects
        search_results = []
        
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                text = results["documents"][0][i] if results["documents"] else ""
                metadata_dict = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                
                # Convert distance to similarity score (ChromaDB returns L2 distance)
                score = 1 - (distance / 2)  # Approximate conversion for cosine
                
                search_results.append(SearchResult(
                    text=text,
                    metadata=DocumentMetadata.from_dict(metadata_dict),
                    score=score,
                    embedding_id=doc_id
                ))
        
        logger.debug(
            "Vector search completed",
            query_length=len(query),
            results_count=len(search_results)
        )
        
        return search_results
    
    def delete(self, ids: list[str]) -> bool:
        """
        Delete documents by ID.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            bool: Success status
        """
        try:
            self.collection.delete(ids=ids)
            logger.info("Documents deleted from ChromaDB", count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to delete documents", error=str(e))
            return False
    
    def get_collection_stats(self) -> dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            dict[str, Any]: Collection statistics
        """
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def reset(self) -> None:
        """Reset/clear the collection."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("ChromaDB collection reset", collection=self.collection_name)


class FAISSVectorStore(VectorStoreBase):
    """
    FAISS vector store implementation.
    
    FAISS is an alternative to ChromaDB, optimized for
    large-scale similarity search.
    """
    
    def __init__(
        self,
        index_path: Optional[str] = None,
        dimension: Optional[int] = None
    ) -> None:
        """
        Initialize FAISS vector store.
        
        Args:
            index_path: Path to save/load the index
            dimension: Embedding dimension
        """
        import faiss
        
        self.dimension = dimension or settings.embedding_dimension
        self.index_path = index_path or os.path.join(
            settings.vector_db_path, 
            "faiss_index"
        )
        
        # Ensure directory exists
        Path(os.path.dirname(self.index_path)).mkdir(parents=True, exist_ok=True)
        
        # Initialize or load index
        if os.path.exists(f"{self.index_path}.index"):
            self.index = faiss.read_index(f"{self.index_path}.index")
            self._load_metadata()
            logger.info("FAISS index loaded", path=self.index_path)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine
            self.documents: list[str] = []
            self.metadatas: list[dict] = []
            self.ids: list[str] = []
            logger.info("New FAISS index created", dimension=self.dimension)
        
        self.embedding_service = get_embedding_service()
    
    def _save_metadata(self) -> None:
        """Save metadata to disk."""
        import json
        
        metadata = {
            "documents": self.documents,
            "metadatas": self.metadatas,
            "ids": self.ids
        }
        
        with open(f"{self.index_path}.meta.json", "w") as f:
            json.dump(metadata, f)
    
    def _load_metadata(self) -> None:
        """Load metadata from disk."""
        import json
        
        try:
            with open(f"{self.index_path}.meta.json", "r") as f:
                metadata = json.load(f)
            
            self.documents = metadata.get("documents", [])
            self.metadatas = metadata.get("metadatas", [])
            self.ids = metadata.get("ids", [])
        except FileNotFoundError:
            self.documents = []
            self.metadatas = []
            self.ids = []
    
    def add_documents(
        self,
        texts: list[str],
        metadatas: list[DocumentMetadata],
        ids: Optional[list[str]] = None
    ) -> list[str]:
        """
        Add documents to FAISS.
        
        Args:
            texts: List of document texts
            metadatas: List of document metadata
            ids: Optional list of document IDs
            
        Returns:
            list[str]: List of document IDs
        """
        import faiss
        import numpy as np
        
        if not texts:
            return []
        
        # Generate IDs if not provided
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Generate embeddings
        embeddings = self.embedding_service.embed_documents(texts)
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Add to index
        self.index.add(embeddings_array)
        
        # Store metadata
        self.documents.extend(texts)
        self.metadatas.extend([m.to_dict() for m in metadatas])
        self.ids.extend(ids)
        
        # Save to disk
        faiss.write_index(self.index, f"{self.index_path}.index")
        self._save_metadata()
        
        logger.info("Documents added to FAISS", count=len(texts))
        
        return ids
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None
    ) -> list[SearchResult]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Optional metadata filter (post-filtering)
            
        Returns:
            list[SearchResult]: Search results
        """
        import faiss
        import numpy as np
        
        if self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_array)
        
        # Search (get more results for post-filtering)
        search_k = k * 3 if filter_metadata else k
        search_k = min(search_k, self.index.ntotal)
        
        scores, indices = self.index.search(query_array, search_k)
        
        # Convert to SearchResult objects with filtering
        search_results = []
        
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            
            metadata_dict = self.metadatas[idx]
            
            # Apply filter if provided
            if filter_metadata:
                match = all(
                    metadata_dict.get(key) == value 
                    for key, value in filter_metadata.items()
                )
                if not match:
                    continue
            
            search_results.append(SearchResult(
                text=self.documents[idx],
                metadata=DocumentMetadata.from_dict(metadata_dict),
                score=float(scores[0][i]),
                embedding_id=self.ids[idx]
            ))
            
            if len(search_results) >= k:
                break
        
        return search_results
    
    def delete(self, ids: list[str]) -> bool:
        """
        Delete documents by ID (FAISS doesn't support direct deletion).
        Rebuilds the index without the specified documents.
        
        Args:
            ids: List of document IDs to delete
            
        Returns:
            bool: Success status
        """
        import faiss
        import numpy as np
        
        try:
            # Find indices to keep
            ids_set = set(ids)
            keep_indices = [
                i for i, doc_id in enumerate(self.ids) 
                if doc_id not in ids_set
            ]
            
            if not keep_indices:
                # Delete all
                self.index = faiss.IndexFlatIP(self.dimension)
                self.documents = []
                self.metadatas = []
                self.ids = []
            else:
                # Rebuild index
                # Get embeddings for documents to keep
                texts_to_keep = [self.documents[i] for i in keep_indices]
                embeddings = self.embedding_service.embed_documents(texts_to_keep)
                embeddings_array = np.array(embeddings, dtype=np.float32)
                faiss.normalize_L2(embeddings_array)
                
                # Create new index
                new_index = faiss.IndexFlatIP(self.dimension)
                new_index.add(embeddings_array)
                
                # Update state
                self.index = new_index
                self.documents = texts_to_keep
                self.metadatas = [self.metadatas[i] for i in keep_indices]
                self.ids = [self.ids[i] for i in keep_indices]
            
            # Save to disk
            faiss.write_index(self.index, f"{self.index_path}.index")
            self._save_metadata()
            
            logger.info("Documents deleted from FAISS", count=len(ids))
            return True
        except Exception as e:
            logger.error("Failed to delete documents from FAISS", error=str(e))
            return False
    
    def get_collection_stats(self) -> dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            dict[str, Any]: Collection statistics
        """
        return {
            "count": self.index.ntotal,
            "dimension": self.dimension,
            "index_path": self.index_path
        }


# Factory function
def get_vector_store(
    store_type: Optional[str] = None,
    **kwargs
) -> VectorStoreBase:
    """
    Get a vector store instance based on configuration.
    
    Args:
        store_type: Type of vector store (chroma or faiss)
        **kwargs: Additional arguments for the vector store
        
    Returns:
        VectorStoreBase: Vector store instance
    """
    store_type = store_type or settings.vector_store_type
    
    if store_type == "chroma":
        return ChromaVectorStore(**kwargs)
    elif store_type == "faiss":
        return FAISSVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")


# Default vector store instance
_default_store: Optional[VectorStoreBase] = None


def get_default_vector_store() -> VectorStoreBase:
    """
    Get the default vector store singleton.
    
    Returns:
        VectorStoreBase: Default vector store instance
    """
    global _default_store
    
    if _default_store is None:
        _default_store = get_vector_store()
    
    return _default_store


def search_vectorstore(
    query: str,
    k: int = 5,
    filter_metadata: Optional[dict[str, Any]] = None
) -> list[SearchResult]:
    """
    Search the default vector store.
    
    Args:
        query: Search query
        k: Number of results
        filter_metadata: Optional metadata filter
        
    Returns:
        list[SearchResult]: Search results
    """
    return get_default_vector_store().search(query, k, filter_metadata)
