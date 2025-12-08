"""
NyayamGPT - API Schemas
=======================
Pydantic models for API request/response validation.
Enhanced with multi-mode support.
"""

from datetime import datetime
from typing import Any, Optional, Literal

from pydantic import BaseModel, Field


# =============================================================================
# Type Definitions
# =============================================================================

ModeType = Literal["normal", "lawyer", "qa", "web", "deep"]


# =============================================================================
# Chat Schemas
# =============================================================================

class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User's legal question or message"
    )
    mode: ModeType = Field(
        default="normal",
        description="Response mode: normal, lawyer, qa, web, deep"
    )
    language: str = Field(
        default="en",
        description="Language for response (en, hi, etc.)"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for conversation continuity"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID for authenticated requests"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is the punishment for theft under IPC?",
                "mode": "normal",
                "language": "en",
                "session_id": "abc123"
            }
        }


class Citation(BaseModel):
    """Legal citation reference with official URL."""
    
    act: str = Field(description="Name of the act (IPC, CrPC, etc.)", alias="law")
    section: str = Field(description="Section number")
    title: Optional[str] = Field(default=None, description="Section title")
    url: str = Field(description="Official government URL for this citation")
    context: Optional[str] = Field(default=None, description="Usage context")
    verified: bool = Field(default=False, description="Whether URL was verified as official source")
    relevance_score: Optional[float] = Field(default=None, description="Relevance score 0-1")
    case_name: Optional[str] = Field(default=None, description="Related case name if any")
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "act": "IPC",
                "section": "420",
                "title": "Cheating",
                "url": "https://www.indiacode.nic.in/handle/123456789/2263?searchTerm=Section%20420",
                "context": "Definition of cheating",
                "verified": True,
                "relevance_score": 0.95
            }
        }


class WebSearchResult(BaseModel):
    """Web search result for web mode."""
    
    index: int = Field(description="Result index")
    title: str = Field(description="Page title")
    url: str = Field(description="Source URL")
    snippet: str = Field(description="Content snippet")
    date: Optional[str] = Field(default=None, description="Publication date")
    source_type: Optional[str] = Field(default=None, description="Source type: official, news, legal")


class DebugInfo(BaseModel):
    """Debug information for development."""
    
    retrieved_docs_count: int = Field(description="Number of documents retrieved")
    draft_length: int = Field(description="Length of draft answer")
    final_length: int = Field(description="Length of final answer")
    issues: list[str] = Field(default_factory=list, description="Validation issues found")


class ChatResponse(BaseModel):
    """Response from chat endpoint."""
    
    success: bool = Field(description="Whether request was successful")
    answer: str = Field(description="Legal answer or clarification question")
    mode: ModeType = Field(default="normal", description="Mode used for response")
    citations: list[Citation] = Field(
        default_factory=list,
        description="Legal citations referenced"
    )
    needs_clarification: bool = Field(
        default=False,
        description="Whether more information is needed"
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Question to clarify user's query"
    )
    awaiting_search_approval: bool = Field(
        default=False,
        description="Whether AI is asking user permission to search internet"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for this conversation"
    )
    is_valid: bool = Field(
        default=True,
        description="Whether answer passed validation"
    )
    validation_attempts: int = Field(
        default=0,
        description="Number of validation attempts"
    )
    confidence_score: Optional[float] = Field(
        default=None,
        description="AI confidence score 0-1"
    )
    intent: Optional[str] = Field(
        default=None,
        description="Classified intent of the query"
    )
    processing_time_ms: int = Field(
        description="Processing time in milliseconds"
    )
    search_results: Optional[list[WebSearchResult]] = Field(
        default=None,
        description="Web search results for web mode"
    )
    limitations: Optional[str] = Field(
        default=None,
        description="Known limitations of the response (for deep mode)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    debug: Optional[DebugInfo] = Field(
        default=None,
        description="Debug information (only in debug mode)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if any"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "answer": "Under Section 378 of the Indian Penal Code (IPC), theft is defined as...",
                "citations": [
                    {
                        "law": "IPC",
                        "section": "378",
                        "title": "Theft",
                        "verified": True
                    }
                ],
                "needs_clarification": False,
                "session_id": "abc123",
                "is_valid": True,
                "validation_attempts": 1,
                "intent": "LEGAL_QUERY",
                "processing_time_ms": 2500
            }
        }


class StreamChunk(BaseModel):
    """Streaming response chunk."""
    
    type: str = Field(description="Chunk type: progress, content, complete")
    node: Optional[str] = Field(default=None, description="Current processing node")
    status: Optional[str] = Field(default=None, description="Node status")
    content: Optional[str] = Field(default=None, description="Partial content")
    response: Optional[ChatResponse] = Field(default=None, description="Final response")


# =============================================================================
# Session Schemas
# =============================================================================

class SessionCreate(BaseModel):
    """Create a new chat session."""
    
    user_id: Optional[str] = Field(default=None, description="User identifier")
    title: str = Field(default="New Conversation", description="Session title")
    language: str = Field(default="en", description="Preferred language")


class SessionResponse(BaseModel):
    """Chat session details."""
    
    id: str = Field(description="Session ID")
    user_id: Optional[str] = Field(description="User identifier")
    title: str = Field(description="Session title")
    language: str = Field(description="Preferred language")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    is_active: bool = Field(description="Whether session is active")


class MessageResponse(BaseModel):
    """Chat message details."""
    
    id: str = Field(description="Message ID")
    session_id: str = Field(description="Parent session ID")
    role: str = Field(description="Message role (user/assistant)")
    content: str = Field(description="Message content")
    citations: Optional[list[Citation]] = Field(
        default=None,
        description="Citations for this message"
    )
    processing_time_ms: Optional[int] = Field(
        default=None,
        description="Processing time for assistant messages"
    )
    created_at: datetime = Field(description="Creation timestamp")


class SessionWithMessages(SessionResponse):
    """Session with message history."""
    
    messages: list[MessageResponse] = Field(
        default_factory=list,
        description="Messages in this session"
    )


# =============================================================================
# Health Schemas
# =============================================================================

class HealthCheck(BaseModel):
    """Health check response."""
    
    status: str = Field(description="Service status")
    version: str = Field(description="Application version")
    environment: str = Field(description="Deployment environment")
    timestamp: datetime = Field(description="Current timestamp")


class ComponentHealth(BaseModel):
    """Individual component health status."""
    
    name: str = Field(description="Component name")
    status: str = Field(description="healthy, degraded, or unhealthy")
    latency_ms: Optional[float] = Field(default=None, description="Response latency")
    message: Optional[str] = Field(default=None, description="Additional info")


class DetailedHealth(HealthCheck):
    """Detailed health check with component status."""
    
    components: list[ComponentHealth] = Field(
        default_factory=list,
        description="Individual component health"
    )
    uptime_seconds: float = Field(description="Service uptime")


# =============================================================================
# Error Schemas
# =============================================================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error info")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid request body",
                "detail": "message field is required",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }


# =============================================================================
# Feedback Schemas
# =============================================================================

class FeedbackRequest(BaseModel):
    """User feedback on a response."""
    
    message_id: str = Field(description="Message ID to rate")
    score: int = Field(ge=1, le=5, description="Rating score (1-5)")
    comment: Optional[str] = Field(default=None, max_length=1000, description="Optional comment")


class FeedbackResponse(BaseModel):
    """Feedback submission response."""
    
    success: bool = Field(description="Whether feedback was recorded")
    message: str = Field(description="Confirmation message")
