"""
NyayamGPT - Agent System (v2.0)
===============================
Production-grade agentic legal research assistant.

This module provides the core AI agent functionality:
- LangGraph workflow orchestration
- Gemini LLM integration with structured prompts
- Answer validation and refinement loop
- Citation extraction and resolution

Architecture:
    prompts.py    -> Modular prompt templates
    types.py      -> Shared type definitions
    reasoning.py  -> LLM integration layer
    nodes.py      -> Individual workflow nodes
    graph.py      -> LangGraph workflow definition
    validator.py  -> Answer validation logic

Usage:
    from app.agents import process_legal_query
    
    response = await process_legal_query(
        query="What is the punishment for theft?",
        language="en",
        mode="normal"
    )
"""

from app.agents.types import (
    Intent,
    Mode,
    ModeType,
    GraphState,
    QueryRequest,
    QueryResponse,
    Citation,
    DocumentMetadata,
    SearchResult,
    create_initial_state,
)

from app.agents.graph import (
    process_legal_query,
    get_assistant_service,
    LegalAssistantService,
)

from app.agents.reasoning import (
    get_gemini_service,
    gemini_generate,
)

from app.agents.validator import (
    validate_and_refine,
    ValidationResult,
    ValidatorAgent,
)

__all__ = [
    # Types
    "Intent",
    "Mode",
    "ModeType",
    "GraphState",
    "QueryRequest",
    "QueryResponse",
    "Citation",
    "DocumentMetadata",
    "SearchResult",
    "create_initial_state",
    # Services
    "process_legal_query",
    "get_assistant_service",
    "LegalAssistantService",
    "get_gemini_service",
    "gemini_generate",
    # Validation
    "validate_and_refine",
    "ValidationResult",
    "ValidatorAgent",
]
