"""
NyayamGPT - Agent Type Definitions (v2.0)
=========================================
Centralized type definitions for the agent system.

Following Google/Anthropic best practices:
- Use dataclasses/Pydantic for structured data
- Define clear interfaces between components
- Type hints everywhere for IDE support
- Immutable where possible
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class Intent(str, Enum):
    """User intent classification categories."""
    
    CONVERSATIONAL = "CONVERSATIONAL"
    LEGAL_QUERY = "LEGAL_QUERY"
    CASE_ANALYSIS = "CASE_ANALYSIS"
    LEGAL_DRAFTING = "LEGAL_DRAFTING"
    CASE_SEARCH = "CASE_SEARCH"
    GENERAL_INFO = "GENERAL_INFO"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    
    @classmethod
    def from_string(cls, value: str) -> "Intent":
        """Parse intent from string, with fallback."""
        try:
            return cls(value.upper())
        except ValueError:
            return cls.LEGAL_QUERY


class Mode(str, Enum):
    """Chat mode types."""
    
    NORMAL = "normal"
    LAWYER = "lawyer"
    QA = "qa"
    WEB = "web"
    DEEP = "deep"
    
    @property
    def requires_citations(self) -> int:
        """Minimum citations required for this mode."""
        requirements = {
            self.NORMAL: 1,
            self.LAWYER: 3,
            self.QA: 1,
            self.WEB: 1,
            self.DEEP: 5,
        }
        return requirements.get(self, 1)
    
    @property
    def strictness(self) -> float:
        """Validation strictness threshold for this mode."""
        thresholds = {
            self.NORMAL: 0.8,
            self.LAWYER: 0.8,
            self.QA: 0.5,
            self.WEB: 0.7,
            self.DEEP: 0.9,
        }
        return thresholds.get(self, 0.7)


# Literal type for mode (for function signatures)
ModeType = Literal["normal", "lawyer", "qa", "web", "deep"]


# =============================================================================
# GRAPH STATE (TypedDict for LangGraph)
# =============================================================================

class GraphState(TypedDict, total=False):
    """
    State object passed between LangGraph nodes.
    
    This is the central data structure that flows through the workflow.
    All nodes read from and write to this state.
    
    Attributes:
        query: Original user query (may be translated to English)
        original_query: User's original query before translation
        clarified_query: Query after rewriting for search optimization
        intent: Classified intent of the query
        intent_confidence: Confidence score for intent classification
        needs_clarification: Whether clarification is needed
        clarification_question: Question to ask for clarification
        expanded_queries: Multiple search queries for retrieval
        retrieved_docs: List of retrieved documents
        context: Formatted context string from retrieved docs
        related_cases: Web search results for case law
        local_docs_sufficient: Whether local docs are enough (vs web search)
        draft_answer: Initial generated answer
        final_answer: Final validated answer
        citations: List of extracted citations
        is_valid: Whether the answer passed validation
        validation_attempts: Number of validation attempts used
        issues: List of issues found during validation
        error: Error message if any
        language: Target language for response
        mode: Response mode (normal, lawyer, qa, web, deep)
        awaiting_search_approval: Whether waiting for user to approve internet search
        search_approved: Whether user approved internet search
        chat_history: Previous conversation history
    """
    
    # Query processing
    query: str
    original_query: str
    clarified_query: str
    expanded_queries: list[str]
    
    # Intent classification
    intent: str
    intent_confidence: float
    needs_clarification: bool
    clarification_question: str
    
    # Document retrieval
    retrieved_docs: list[dict[str, Any]]
    context: str
    related_cases: list[dict[str, Any]]
    local_docs_sufficient: bool
    
    # Answer generation
    draft_answer: str
    final_answer: str
    
    # Citations
    citations: list[dict[str, Any]]
    
    # Validation
    is_valid: bool
    validation_attempts: int
    issues: list[str]
    
    # Constrained RAG (NEW)
    query_classification: dict[str, Any]  # Pre-computed offense classification
    vector_filter: dict[str, Any]         # Metadata filter for vector store
    enhanced_query: str                   # Query enhanced with keywords
    severity_validated: bool              # Whether severity check passed
    severity_issues: list[str]            # Severity validation problems
    
    # Metadata
    error: str
    language: str
    mode: str
    
    # Web search control
    awaiting_search_approval: bool
    search_approved: bool
    
    # Conversation context
    chat_history: list[dict[str, str]]


# =============================================================================
# REQUEST/RESPONSE MODELS (Pydantic)
# =============================================================================

class QueryRequest(BaseModel):
    """Request model for legal query."""
    
    query: str = Field(..., description="User's legal question", min_length=3)
    language: str = Field(default="en", description="Target language code")
    mode: ModeType = Field(default="normal", description="Response mode")
    session_id: Optional[str] = Field(default=None, description="Session ID for tracking")
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the punishment for theft in India?",
                "language": "en",
                "mode": "normal",
                "session_id": "abc123",
                "chat_history": []
            }
        }


class Citation(BaseModel):
    """Citation model for legal references."""
    
    type: str = Field(default="section", description="Citation type (section, article, case)")
    law: str = Field(..., description="Name of the law/act")
    section: Optional[str] = Field(default=None, description="Section number")
    article: Optional[str] = Field(default=None, description="Article number (for Constitution)")
    title: Optional[str] = Field(default=None, description="Title of the section")
    source_url: Optional[str] = Field(default=None, description="URL to official source")
    verified: bool = Field(default=False, description="Whether citation was verified")
    context: Optional[str] = Field(default=None, description="How citation is used")


class QueryResponse(BaseModel):
    """Response model for legal query."""
    
    success: bool = Field(..., description="Whether query was processed successfully")
    answer: str = Field(default="", description="Generated legal answer")
    citations: list[Citation] = Field(default_factory=list)
    needs_clarification: bool = Field(default=False)
    clarification_question: Optional[str] = Field(default=None)
    awaiting_search_approval: bool = Field(default=False)
    intent: str = Field(default="")
    is_valid: bool = Field(default=False)
    validation_attempts: int = Field(default=0)
    processing_time_ms: int = Field(default=0)
    error: Optional[str] = Field(default=None)
    debug: Optional[dict[str, Any]] = Field(default=None)


# =============================================================================
# INTERMEDIATE MODELS
# =============================================================================

class IntentClassification(BaseModel):
    """Result of intent classification."""
    
    intent: Intent = Field(..., description="Classified intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    sub_topics: list[str] = Field(default_factory=list)
    needs_clarification: bool = Field(default=False)
    clarification_question: str = Field(default="")


class TranslationResult(BaseModel):
    """Result of language detection and translation."""
    
    original_language: str = Field(..., description="Detected language name")
    language_code: str = Field(..., description="ISO 639-1 language code")
    is_english: bool = Field(default=False)
    translated_query: str = Field(..., description="Translated query")


class QueryExpansion(BaseModel):
    """Result of query expansion."""
    
    expanded_queries: list[str] = Field(..., max_length=5)


class ValidationResult(BaseModel):
    """Result of answer validation."""
    
    is_valid: bool = Field(default=False)
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    grounding_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    communication_score: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    problems: list[str] = Field(default_factory=list)
    hallucinated_citations: list[str] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)


# =============================================================================
# DOCUMENT TYPES
# =============================================================================

@dataclass(frozen=True)
class DocumentMetadata:
    """Metadata for a legal document chunk."""
    
    law: str
    section: str
    title: str
    source_url: Optional[str] = None
    chapter: Optional[str] = None
    part: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "law": self.law,
            "section": self.section,
            "title": self.title,
            "source_url": self.source_url,
            "chapter": self.chapter,
            "part": self.part,
        }


@dataclass
class SearchResult:
    """Result from vector store search."""
    
    text: str
    metadata: DocumentMetadata
    score: float
    embedding_id: Optional[str] = None
    
    @property
    def is_relevant(self) -> bool:
        """Check if result is above relevance threshold."""
        return self.score >= 0.3


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_initial_state(
    query: str,
    language: str = "en",
    mode: ModeType = "normal",
    chat_history: list[dict[str, str]] | None = None
) -> GraphState:
    """
    Create initial GraphState for a new query.
    
    Args:
        query: User's query
        language: Target language
        mode: Response mode
        chat_history: Previous conversation
        
    Returns:
        Initialized GraphState
    """
    return GraphState(
        query=query,
        original_query="",
        clarified_query="",
        expanded_queries=[],
        intent="",
        intent_confidence=0.0,
        needs_clarification=False,
        clarification_question="",
        retrieved_docs=[],
        context="",
        related_cases=[],
        local_docs_sufficient=False,
        draft_answer="",
        final_answer="",
        citations=[],
        is_valid=False,
        validation_attempts=0,
        issues=[],
        error="",
        language=language,
        mode=mode,
        awaiting_search_approval=False,
        search_approved=False,
        chat_history=chat_history or [],
    )
