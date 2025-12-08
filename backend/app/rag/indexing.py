"""
NyayamGPT - Document Indexing Module
====================================
Index legal documents into the vector store for retrieval.
"""

import asyncio
from typing import Optional

from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db_context
from app.db import crud
from app.rag.loader import (
    DocumentLoader,
    LegalDocument,
    get_all_sample_data,
    get_all_legal_data,
)
from app.rag.vectorstore import (
    DocumentMetadata,
    get_default_vector_store,
    VectorStoreBase,
)


class TextChunker:
    """
    Split documents into smaller chunks for better retrieval.
    
    Attributes:
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> None:
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Maximum characters per chunk
            chunk_overlap: Overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split
            
        Returns:
            list[str]: List of text chunks
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to find a natural break point
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + self.chunk_size // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    for sep in [". ", ".\n", "? ", "! "]:
                        sent_break = text.rfind(sep, start, end)
                        if sent_break > start + self.chunk_size // 2:
                            end = sent_break + len(sep)
                            break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def chunk_document(
        self,
        document: LegalDocument
    ) -> list[tuple[str, DocumentMetadata]]:
        """
        Chunk a legal document.
        
        Args:
            document: Document to chunk
            
        Returns:
            list[tuple[str, DocumentMetadata]]: List of (chunk_text, metadata) tuples
        """
        # Create full document text with context
        full_text = document.to_text()
        
        # Chunk the text
        chunks = self.chunk_text(full_text)
        
        # Create metadata for each chunk
        result = []
        for i, chunk in enumerate(chunks):
            metadata = DocumentMetadata(
                law=document.law_name,
                section=document.section,
                title=document.title,
                source_url=document.source_url
            )
            
            # Add chunk prefix for context if multiple chunks
            if len(chunks) > 1:
                prefix = f"[{document.law_name} Section {document.section}] "
                if not chunk.startswith(prefix):
                    chunk = prefix + chunk
            
            result.append((chunk, metadata))
        
        return result


class IndexingService:
    """
    Service for indexing documents into the vector store.
    
    Handles:
    - Loading documents from files
    - Chunking documents
    - Adding to vector store
    - Storing in database
    """
    
    def __init__(
        self,
        vector_store: Optional[VectorStoreBase] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> None:
        """
        Initialize indexing service.
        
        Args:
            vector_store: Vector store instance
            chunk_size: Chunk size for text splitting
            chunk_overlap: Overlap between chunks
        """
        self.vector_store = vector_store or get_default_vector_store()
        self.chunker = TextChunker(
            chunk_size=chunk_size or settings.chunk_size,
            chunk_overlap=chunk_overlap or settings.chunk_overlap
        )
        self.loader = DocumentLoader()
    
    def index_documents(
        self,
        documents: list[LegalDocument],
        batch_size: int = 50
    ) -> int:
        """
        Index a list of documents.
        
        Args:
            documents: Documents to index
            batch_size: Batch size for adding to vector store
            
        Returns:
            int: Number of chunks indexed
        """
        all_chunks = []
        all_metadatas = []
        
        # Chunk all documents
        for doc in documents:
            chunks = self.chunker.chunk_document(doc)
            for chunk_text, metadata in chunks:
                all_chunks.append(chunk_text)
                all_metadatas.append(metadata)
        
        # Add to vector store in batches
        total_indexed = 0
        
        for i in range(0, len(all_chunks), batch_size):
            batch_chunks = all_chunks[i:i + batch_size]
            batch_metadatas = all_metadatas[i:i + batch_size]
            
            self.vector_store.add_documents(batch_chunks, batch_metadatas)
            total_indexed += len(batch_chunks)
            
            logger.info(
                "Indexed batch",
                batch_start=i,
                batch_size=len(batch_chunks),
                total_indexed=total_indexed
            )
        
        return total_indexed
    
    def index_from_directory(
        self,
        directory: Optional[str] = None
    ) -> int:
        """
        Index documents from a directory.
        
        Args:
            directory: Directory path
            
        Returns:
            int: Number of chunks indexed
        """
        documents = self.loader.load_directory(directory)
        return self.index_documents(documents)
    
    def index_sample_data(self) -> int:
        """
        Index sample legal data for testing.
        
        Returns:
            int: Number of chunks indexed
        """
        # Try to load from JSON files first, fall back to sample data
        documents = get_all_legal_data(use_json_files=True)
        return self.index_documents(documents)
    
    async def index_and_store(
        self,
        documents: list[LegalDocument]
    ) -> tuple[int, int]:
        """
        Index documents and store in database.
        
        Args:
            documents: Documents to index and store
            
        Returns:
            tuple[int, int]: (chunks_indexed, documents_stored)
        """
        chunks_indexed = self.index_documents(documents)
        documents_stored = 0
        
        async with get_db_context() as db:
            for doc in documents:
                await crud.create_legal_document(
                    db=db,
                    law_name=doc.law_name,
                    section=doc.section,
                    title=doc.title,
                    content=doc.content,
                    source_url=doc.source_url,
                    metadata=doc.metadata
                )
                documents_stored += 1
        
        logger.info(
            "Documents indexed and stored",
            chunks_indexed=chunks_indexed,
            documents_stored=documents_stored
        )
        
        return chunks_indexed, documents_stored
    
    def get_stats(self) -> dict:
        """
        Get indexing statistics.
        
        Returns:
            dict: Vector store statistics
        """
        return self.vector_store.get_collection_stats()


# Convenience functions
def get_indexing_service() -> IndexingService:
    """
    Get an indexing service instance.
    
    Returns:
        IndexingService: Indexing service
    """
    return IndexingService()


def index_sample_data() -> int:
    """
    Index sample legal data.
    
    Returns:
        int: Number of chunks indexed
    """
    service = get_indexing_service()
    return service.index_sample_data()


async def initialize_vector_store(force_reindex: bool = False) -> int:
    """
    Initialize vector store with legal data from JSON files.
    
    Args:
        force_reindex: If True, reindex even if data exists
    
    Returns:
        int: Number of documents indexed (0 if already populated)
    """
    service = get_indexing_service()
    stats = service.get_stats()
    current_count = stats.get("count", 0)
    
    # Load documents to see how many we should have
    documents = get_all_legal_data(use_json_files=True)
    expected_count = len(documents)
    
    # Reindex if empty, forced, or count mismatch (new data added)
    if current_count == 0 or force_reindex or (expected_count > 0 and current_count < expected_count // 2):
        if current_count > 0:
            logger.info(
                "Reindexing vector store",
                current_count=current_count,
                expected_count=expected_count
            )
        else:
            logger.info("Vector store empty, indexing legal data from JSON files...")
        
        return service.index_documents(documents)
    
    logger.info(
        "Vector store already populated",
        count=current_count,
        expected=expected_count
    )
    return 0
