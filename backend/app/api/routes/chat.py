"""
NyayamGPT - Chat Routes
=======================
Main chat API endpoints with tracing.
"""

import json
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.limiter import limiter
from app.db.session import get_db
from app.db import crud
from app.utils.language import detect_language, get_language_name
from app.agents.graph import process_legal_query, get_assistant_service
from app.auth.dependencies import get_current_user, get_current_active_user
from app.auth.models import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    DebugInfo,
    SessionCreate,
    SessionResponse,
    SessionWithMessages,
    MessageResponse,
    FeedbackRequest,
    FeedbackResponse,
    ErrorResponse,
)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Get tracer
tracer = trace.get_tracer(__name__)


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Server error"}
    },
    summary="Send a legal question",
    description="Process a legal question and get an answer with citations"
)
@limiter.limit("10/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> ChatResponse:
    """
    Process a legal question.
    
    Args:
        request: FastAPI request object (for rate limiting)
        chat_request: Chat request with message and optional settings
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user (optional)
        
    Returns:
        ChatResponse: Answer with citations and metadata
    """
    start_time = time.time()
    
    # Get user_id if authenticated
    user_id = str(current_user.id) if current_user else None
    
    try:
        # Create or get session
        session_id = chat_request.session_id
        if not session_id:
            session = await crud.create_chat_session(
                db=db,
                user_id=user_id,  # Associate with user
                language=chat_request.language
            )
            session_id = session.id
        else:
            # Check if session exists
            existing_session = await crud.get_chat_session(db, session_id)
            
            if existing_session:
                # If user is authenticated and session is anonymous, associate it
                if user_id and not existing_session.user_id:
                    await crud.associate_session_with_user(db, session_id, user_id)
                    logger.info(f"Associated anonymous session {session_id} with user {user_id}")
                # If session belongs to another user, create a new session instead
                elif existing_session.user_id and existing_session.user_id != user_id:
                    logger.warning(f"Session {session_id} belongs to another user, creating new session")
                    session = await crud.create_chat_session(
                        db=db,
                        user_id=user_id,
                        language=chat_request.language
                    )
                    session_id = session.id
            else:
                # Session doesn't exist in database, create a new one
                logger.info(f"Session {session_id} not found, creating new session")
                session = await crud.create_chat_session(
                    db=db,
                    user_id=user_id,
                    language=chat_request.language
                )
                session_id = session.id
        
        # Store user message
        await crud.create_chat_message(
            db=db,
            session_id=session_id,
            role="user",
            content=chat_request.message
        )
        
        # Get chat history for context
        history_messages = await crud.get_session_messages(db, session_id, limit=10)
        
        # Update title if this is the first message
        if len(history_messages) == 1:
            new_title = chat_request.message[:50] + ("..." if len(chat_request.message) > 50 else "")
            await crud.update_session_title(db, session_id, new_title)
            
        chat_history = []
        # Exclude the last message which is the current query we just added
        if len(history_messages) > 1:
            for msg in history_messages[:-1]:
                chat_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Determine target language
        # If the frontend sends "en" (default), we try to detect the actual language from the message
        target_language = chat_request.language
        if not target_language or target_language == "en":
            detected_code = detect_language(chat_request.message)
            target_language = get_language_name(detected_code)
        else:
            # If frontend sends a specific code (e.g. "hi"), get its name
            target_language = get_language_name(target_language)

        # Process query through the legal assistant
        result = await process_legal_query(
            query=chat_request.message,
            language=target_language,
            session_id=session_id,
            mode=chat_request.mode,
            chat_history=chat_history
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log completion
        print(f"[CHAT] [{chat_request.mode.upper()}] Query processed in {processing_time}ms")
        
        # Parse citations - handle both old and new format
        citations = []
        for c in result.get("citations", []):
            if isinstance(c, dict):
                # Normalize field names for Citation model - ensure no None values for required fields
                law = c.get("act") or c.get("law") or ""
                section = c.get("section") or ""
                url = c.get("url") or c.get("source_url") or ""
                
                # Skip citations without both law and section
                if not law or not section:
                    continue
                
                citation_data = {
                    "law": str(law),
                    "section": str(section),
                    "title": c.get("title") or "",
                    "url": url,
                    "context": c.get("context"),
                    "verified": c.get("verified", False)
                }
                # Ensure URL is present (use fallback if needed)
                if not citation_data["url"]:
                    from urllib.parse import quote
                    citation_data["url"] = f"https://indiankanoon.org/search/?formInput={quote(f'{law} Section {section}')}"
                
                try:
                    citations.append(Citation(**citation_data))
                except Exception as e:
                    logger.warning(f"Skipping invalid citation: {e}", citation=citation_data)
                    continue
            else:
                citations.append(c)
        
        # Build debug info if in debug mode
        debug_info = None
        if settings.debug and result.get("debug"):
            debug_info = DebugInfo(**result["debug"])
        
        # Store assistant message in background
        background_tasks.add_task(
            _store_assistant_message,
            db,
            session_id,
            result.get("answer", ""),
            citations,
            result.get("validation_attempts", 0),
            processing_time
        )
        
        # Update session title if it's a new session
        if not chat_request.session_id:
            background_tasks.add_task(
                _update_session_title,
                db,
                session_id,
                chat_request.message
            )
        
        logger.info(
            "Chat request processed",
            session_id=session_id,
            processing_time_ms=processing_time,
            citations_count=len(citations)
        )
        
        return ChatResponse(
            success=result.get("success", True),
            answer=result.get("answer", ""),
            citations=citations,
            needs_clarification=result.get("needs_clarification", False),
            clarification_question=result.get("clarification_question"),
            awaiting_search_approval=result.get("awaiting_search_approval", False),
            session_id=session_id,
            is_valid=result.get("is_valid", True),
            validation_attempts=result.get("validation_attempts", 0),
            intent=result.get("intent"),
            processing_time_ms=processing_time,
            debug=debug_info,
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error("Chat request failed", error=str(e))
        
        raise HTTPException(
            status_code=500,
            detail=f"Error processing your question: {str(e)}"
        )


@router.post(
    "/stream",
    summary="Send a legal question with streaming",
    description="Process a legal question with streaming updates"
)
@tracer.start_as_current_span("api_chat_stream")
async def chat_stream(request: ChatRequest):
    """
    Process a legal question with streaming response.
    
    Args:
        request: Chat request
        
    Returns:
        StreamingResponse: Server-sent events stream
    """
    span = trace.get_current_span()
    span.set_attribute("streaming", True)
    
    async def generate():
        service = get_assistant_service()
        
        async for chunk in service.process_query_stream(
            query=request.message,
            language=request.language
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


# =============================================================================
# Session Management
# =============================================================================

@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="Get current user's chat sessions"
)
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    limit: int = 50,
    offset: int = 0
) -> list[SessionResponse]:
    """Get all chat sessions for the current authenticated user."""
    sessions = await crud.get_user_sessions(
        db=db,
        user_id=str(current_user.id),
        limit=limit,
        offset=offset
    )
    
    return [
        SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            language=session.language,
            created_at=session.created_at,
            updated_at=session.updated_at,
            is_active=session.is_active
        )
        for session in sessions
    ]


@router.post(
    "/sessions",
    response_model=SessionResponse,
    summary="Create a new chat session"
)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> SessionResponse:
    """Create a new chat session."""
    # Use authenticated user's ID if available
    user_id = str(current_user.id) if current_user else request.user_id
    
    session = await crud.create_chat_session(
        db=db,
        user_id=user_id,
        title=request.title,
        language=request.language
    )
    
    return SessionResponse(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        language=session.language,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionWithMessages,
    summary="Get session with messages"
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> SessionWithMessages:
    """Get a chat session with its messages."""
    session = await crud.get_chat_session(
        db=db,
        session_id=session_id,
        include_messages=True
    )
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to user if authenticated
    user_id = str(current_user.id) if current_user else None
    if session.user_id and user_id and session.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this session")
    
    messages = []
    for msg in session.messages:
        citations = None
        if msg.citations:
            try:
                citations = [Citation(**c) for c in json.loads(msg.citations)]
            except:
                pass
        
        messages.append(MessageResponse(
            id=msg.id,
            session_id=msg.session_id,
            role=msg.role,
            content=msg.content,
            citations=citations,
            processing_time_ms=msg.processing_time_ms,
            created_at=msg.created_at
        ))
    
    return SessionWithMessages(
        id=session.id,
        user_id=session.user_id,
        title=session.title,
        language=session.language,
        created_at=session.created_at,
        updated_at=session.updated_at,
        is_active=session.is_active,
        messages=messages
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a chat session"
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
) -> dict:
    """Delete (soft) a chat session."""
    # Verify session exists and belongs to user
    session = await crud.get_chat_session(db, session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Verify session belongs to user if authenticated
    user_id = str(current_user.id) if current_user else None
    if session.user_id and user_id and session.user_id != user_id:
        raise HTTPException(status_code=403, detail="You don't have access to this session")
    
    success = await crud.delete_chat_session(db, session_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete session")
    
    return {"success": True, "message": "Session deleted"}


# =============================================================================
# Feedback
# =============================================================================

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit feedback on a response"
)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
) -> FeedbackResponse:
    """Submit user feedback on a response."""
    # For now, just log the feedback
    # In production, store in database
    logger.info(
        "Feedback received",
        message_id=request.message_id,
        score=request.score,
        has_comment=bool(request.comment)
    )
    
    return FeedbackResponse(
        success=True,
        message="Thank you for your feedback!"
    )


# =============================================================================
# Background Tasks
# =============================================================================

async def _store_assistant_message(
    db: AsyncSession,
    session_id: str,
    content: str,
    citations: list[Citation],
    validation_attempts: int,
    processing_time_ms: int
) -> None:
    """Store assistant message in database."""
    try:
        await crud.create_chat_message(
            db=db,
            session_id=session_id,
            role="assistant",
            content=content,
            citations=[c.model_dump() for c in citations] if citations else None,
            validation_attempts=validation_attempts,
            processing_time_ms=processing_time_ms
        )
    except Exception as e:
        logger.error("Failed to store assistant message", error=str(e))


async def _update_session_title(
    db: AsyncSession,
    session_id: str,
    first_message: str
) -> None:
    """Update session title based on first message."""
    try:
        # Create a short title from the first message
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        
        await crud.update_session_title(db, session_id, title)
    except Exception as e:
        logger.error("Failed to update session title", error=str(e))
