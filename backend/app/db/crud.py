"""
NyayamGPT - CRUD Operations
===========================
Database CRUD (Create, Read, Update, Delete) operations for all models.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    ChatSession,
    ChatMessage,
    LegalDocument,
    QueryLog,
)
from app.core.logging import logger


# =============================================================================
# Chat Session CRUD
# =============================================================================

async def create_chat_session(
    db: AsyncSession,
    user_id: Optional[str] = None,
    title: str = "New Conversation",
    language: str = "en"
) -> ChatSession:
    """
    Create a new chat session.
    
    Args:
        db: Database session
        user_id: Optional user identifier
        title: Session title
        language: Preferred language
        
    Returns:
        ChatSession: Created session
    """
    session = ChatSession(
        user_id=user_id,
        title=title,
        language=language
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    await db.commit()
    
    logger.info("Chat session created", session_id=session.id)
    return session


async def get_chat_session(
    db: AsyncSession,
    session_id: str,
    include_messages: bool = False
) -> Optional[ChatSession]:
    """
    Get a chat session by ID.
    
    Args:
        db: Database session
        session_id: Session identifier
        include_messages: Whether to load messages
        
    Returns:
        Optional[ChatSession]: Session if found
    """
    query = select(ChatSession).where(ChatSession.id == session_id)
    
    if include_messages:
        query = query.options(selectinload(ChatSession.messages))
    
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_sessions(
    db: AsyncSession,
    user_id: str,
    limit: int = 50,
    offset: int = 0
) -> list[ChatSession]:
    """
    Get all sessions for a user.
    
    Args:
        db: Database session
        user_id: User identifier
        limit: Maximum number of sessions
        offset: Pagination offset
        
    Returns:
        list[ChatSession]: User's sessions
    """
    query = (
        select(ChatSession)
        .where(ChatSession.user_id == user_id)
        .where(ChatSession.is_active == True)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_session_title(
    db: AsyncSession,
    session_id: str,
    title: str
) -> bool:
    """
    Update session title.
    
    Args:
        db: Database session
        session_id: Session identifier
        title: New title
        
    Returns:
        bool: Success status
    """
    query = (
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(title=title, updated_at=datetime.utcnow())
    )
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0


async def delete_chat_session(
    db: AsyncSession,
    session_id: str
) -> bool:
    """
    Soft delete a chat session.
    
    Args:
        db: Database session
        session_id: Session identifier
        
    Returns:
        bool: Success status
    """
    query = (
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    result = await db.execute(query)
    await db.commit()
    return result.rowcount > 0


async def associate_session_with_user(
    db: AsyncSession,
    session_id: str,
    user_id: str
) -> bool:
    """
    Associate an anonymous session with a user.
    Used when a user logs in and we want to preserve their chat history.
    
    Args:
        db: Database session
        session_id: Session identifier
        user_id: User identifier to associate with
        
    Returns:
        bool: Success status
    """
    query = (
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.user_id.is_(None))  # Only update anonymous sessions
        .values(user_id=user_id, updated_at=datetime.utcnow())
    )
    result = await db.execute(query)
    await db.commit()
    
    if result.rowcount > 0:
        logger.info("Session associated with user", session_id=session_id, user_id=user_id)
        return True
    return False


# =============================================================================
# Chat Message CRUD
# =============================================================================

async def create_chat_message(
    db: AsyncSession,
    session_id: str,
    role: str,
    content: str,
    citations: Optional[list[dict]] = None,
    reasoning_steps: Optional[list[str]] = None,
    validation_attempts: int = 0,
    processing_time_ms: Optional[int] = None
) -> ChatMessage:
    """
    Create a new chat message.
    
    Args:
        db: Database session
        session_id: Parent session ID
        role: Message role (user/assistant/system)
        content: Message content
        citations: List of legal citations
        reasoning_steps: List of reasoning steps
        validation_attempts: Number of validation attempts
        processing_time_ms: Processing time in milliseconds
        
    Returns:
        ChatMessage: Created message
    """
    message = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        citations=json.dumps(citations) if citations else None,
        reasoning_steps=json.dumps(reasoning_steps) if reasoning_steps else None,
        validation_attempts=validation_attempts,
        processing_time_ms=processing_time_ms
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)
    
    # Update session's updated_at
    await db.execute(
        update(ChatSession)
        .where(ChatSession.id == session_id)
        .values(updated_at=datetime.utcnow())
    )
    await db.commit()
    
    return message


async def get_session_messages(
    db: AsyncSession,
    session_id: str,
    limit: int = 100
) -> list[ChatMessage]:
    """
    Get all messages for a session.
    
    Args:
        db: Database session
        session_id: Session identifier
        limit: Maximum number of messages
        
    Returns:
        list[ChatMessage]: Session messages
    """
    query = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


# =============================================================================
# Legal Document CRUD
# =============================================================================

async def create_legal_document(
    db: AsyncSession,
    law_name: str,
    section: str,
    title: str,
    content: str,
    source_url: Optional[str] = None,
    embedding_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> LegalDocument:
    """
    Create a new legal document.
    
    Args:
        db: Database session
        law_name: Name of the law
        section: Section number
        title: Section title
        content: Full text content
        source_url: Source URL
        embedding_id: Vector store reference
        metadata: Additional metadata
        
    Returns:
        LegalDocument: Created document
    """
    doc = LegalDocument(
        law_name=law_name,
        section=section,
        title=title,
        content=content,
        source_url=source_url,
        embedding_id=embedding_id,
        metadata=json.dumps(metadata) if metadata else None
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    
    logger.info(
        "Legal document created",
        law=law_name,
        section=section
    )
    return doc


async def get_legal_document(
    db: AsyncSession,
    doc_id: str
) -> Optional[LegalDocument]:
    """
    Get a legal document by ID.
    
    Args:
        db: Database session
        doc_id: Document identifier
        
    Returns:
        Optional[LegalDocument]: Document if found
    """
    query = select(LegalDocument).where(LegalDocument.id == doc_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_documents_by_law(
    db: AsyncSession,
    law_name: str
) -> list[LegalDocument]:
    """
    Get all documents for a specific law.
    
    Args:
        db: Database session
        law_name: Name of the law
        
    Returns:
        list[LegalDocument]: Documents for the law
    """
    query = (
        select(LegalDocument)
        .where(LegalDocument.law_name == law_name)
        .order_by(LegalDocument.section)
    )
    
    result = await db.execute(query)
    return list(result.scalars().all())


async def search_documents(
    db: AsyncSession,
    search_term: str,
    law_name: Optional[str] = None,
    limit: int = 20
) -> list[LegalDocument]:
    """
    Search legal documents by content or title.
    
    Args:
        db: Database session
        search_term: Search term
        law_name: Optional law filter
        limit: Maximum results
        
    Returns:
        list[LegalDocument]: Matching documents
    """
    query = select(LegalDocument)
    
    # Add search conditions
    search_pattern = f"%{search_term}%"
    query = query.where(
        (LegalDocument.title.ilike(search_pattern)) |
        (LegalDocument.content.ilike(search_pattern)) |
        (LegalDocument.section.ilike(search_pattern))
    )
    
    if law_name:
        query = query.where(LegalDocument.law_name == law_name)
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())


# =============================================================================
# Query Log CRUD
# =============================================================================

async def create_query_log(
    db: AsyncSession,
    query: str,
    session_id: Optional[str] = None,
    clarified_query: Optional[str] = None,
    intent: Optional[str] = None,
    retrieved_docs_count: int = 0,
    validation_passed: bool = False,
    validation_attempts: int = 0,
    response_time_ms: Optional[int] = None
) -> QueryLog:
    """
    Log a query for analytics.
    
    Args:
        db: Database session
        query: Original query
        session_id: Related session
        clarified_query: Clarified query
        intent: Detected intent
        retrieved_docs_count: Number of retrieved documents
        validation_passed: Whether validation passed
        validation_attempts: Number of validation attempts
        response_time_ms: Response time
        
    Returns:
        QueryLog: Created log entry
    """
    log = QueryLog(
        query=query,
        session_id=session_id,
        clarified_query=clarified_query,
        intent=intent,
        retrieved_docs_count=retrieved_docs_count,
        validation_passed=validation_passed,
        validation_attempts=validation_attempts,
        response_time_ms=response_time_ms
    )
    db.add(log)
    await db.flush()
    
    return log


async def update_query_feedback(
    db: AsyncSession,
    log_id: str,
    feedback_score: int
) -> bool:
    """
    Update feedback score for a query.
    
    Args:
        db: Database session
        log_id: Log identifier
        feedback_score: Feedback score (1-5)
        
    Returns:
        bool: Success status
    """
    query = (
        update(QueryLog)
        .where(QueryLog.id == log_id)
        .values(feedback_score=feedback_score)
    )
    result = await db.execute(query)
    return result.rowcount > 0
