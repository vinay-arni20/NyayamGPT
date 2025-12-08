"""
NyayamGPT - Database Models
===========================
SQLAlchemy ORM models for chat sessions, messages, and legal documents.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.auth.models import User


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid4())


class ChatSession(Base):
    """
    Represents a chat session/conversation.
    
    Attributes:
        id: Unique session identifier
        user_id: Optional user identifier for authenticated users
        title: Session title (auto-generated from first message)
        language: Preferred language for responses
        mode: Chat mode (normal, lawyer, qa, web, deep)
        created_at: Session creation timestamp
        updated_at: Last update timestamp
        is_active: Whether the session is active
        messages: Related chat messages
    """
    
    __tablename__ = "chat_sessions"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), 
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, 
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(255), 
        default="New Conversation"
    )
    language: Mapped[str] = mapped_column(
        String(10), 
        default="en"
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, 
        default=True
    )
    
    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="chat_sessions"
    )
    
    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, title={self.title})>"


class MessageRole(str):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(Base):
    """
    Represents a single message in a chat session.
    
    Attributes:
        id: Unique message identifier
        session_id: Parent session ID
        role: Message role (user, assistant, system)
        content: Message content
        mode: Chat mode used for this message
        citations: JSON array of legal citations
        reasoning_steps: JSON array of reasoning steps (for debugging)
        validation_attempts: Number of validation attempts used
        confidence_score: AI confidence score (0-1)
        processing_time_ms: Time taken to process in milliseconds
        created_at: Message creation timestamp
    """
    
    __tablename__ = "chat_messages"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        default="normal"
    )
    confidence_score: Mapped[Optional[Float]] = mapped_column(
        Float,
        nullable=True
    )
    citations: Mapped[Optional[str]] = mapped_column(
        Text,  # JSON stored as text for SQLite compatibility
        nullable=True
    )
    reasoning_steps: Mapped[Optional[str]] = mapped_column(
        Text,  # JSON stored as text for SQLite compatibility
        nullable=True
    )
    validation_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages"
    )
    
    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role})>"


class LegalDocument(Base):
    """
    Represents a legal document stored in the database.
    
    Attributes:
        id: Unique document identifier
        law_name: Name of the law (e.g., IPC, CrPC, Constitution)
        section: Section number or identifier
        title: Section/article title
        content: Full text content
        source_url: URL to official source
        embedding_id: Reference to vector store embedding
        metadata: Additional metadata as JSON
        created_at: Document creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "legal_documents"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    law_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True
    )
    section: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    embedding_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    doc_metadata: Mapped[Optional[str]] = mapped_column(
        Text,  # JSON stored as text for SQLite compatibility
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<LegalDocument(law={self.law_name}, section={self.section})>"


class QueryLog(Base):
    """
    Logs all queries for analytics and improvement.
    
    Attributes:
        id: Unique log identifier
        session_id: Related session ID
        query: Original user query
        clarified_query: Query after clarification
        intent: Detected intent
        retrieved_docs_count: Number of documents retrieved
        validation_passed: Whether validation passed
        validation_attempts: Number of validation attempts
        response_time_ms: Total response time
        feedback_score: Optional user feedback
        created_at: Log creation timestamp
    """
    
    __tablename__ = "query_logs"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    clarified_query: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    intent: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )
    retrieved_docs_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    validation_passed: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    validation_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    response_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    feedback_score: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<QueryLog(id={self.id}, intent={self.intent})>"


class ChatMetrics(Base):
    """
    Stores metrics for chat sessions for analytics and monitoring.
    
    Attributes:
        id: Unique metric identifier
        session_id: Related session ID
        user_id: User ID
        mode: Chat mode used (normal, lawyer, qa, web, deep)
        query_count: Number of queries in session
        avg_response_time_ms: Average response time
        total_processing_time_ms: Total processing time
        validation_success_rate: Rate of validation passes
        cache_hit_rate: Rate of cache hits
        citations_used: Total citations used
        web_searches_performed: Number of web searches
        deep_research_performed: Number of deep research queries
        tokens_used: Estimated tokens used
        created_at: Metric creation timestamp
        updated_at: Last update timestamp
    """
    
    __tablename__ = "chat_metrics"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    mode: Mapped[str] = mapped_column(
        String(20),
        default="normal",
        index=True
    )
    query_count: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    avg_response_time_ms: Mapped[Optional[Float]] = mapped_column(
        Float,
        nullable=True
    )
    total_processing_time_ms: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    validation_success_rate: Mapped[Optional[Float]] = mapped_column(
        Float,
        nullable=True
    )
    cache_hit_rate: Mapped[Optional[Float]] = mapped_column(
        Float,
        nullable=True
    )
    citations_used: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    web_searches_performed: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    deep_research_performed: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        backref="metrics"
    )
    
    def __repr__(self) -> str:
        return f"<ChatMetrics(session_id={self.session_id}, mode={self.mode})>"


class FeedbackLog(Base):
    """
    Stores user feedback for responses.
    
    Attributes:
        id: Unique feedback identifier
        message_id: Related message ID
        session_id: Related session ID
        user_id: User who provided feedback
        rating: Feedback rating (1-5)
        feedback_type: Type of feedback (helpful, not_helpful, incorrect, etc.)
        comment: Optional user comment
        created_at: Feedback creation timestamp
    """
    
    __tablename__ = "feedback_logs"
    
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    rating: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    feedback_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="general"
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    
    def __repr__(self) -> str:
        return f"<FeedbackLog(message_id={self.message_id}, rating={self.rating})>"
