"""
NyayamGPT - LangGraph Workflow (v2.0)
=====================================
Main LangGraph workflow definition with conditional routing and tracing.

Architecture:
    1. Intent Classification → Clarification check
    2. Query Processing → Rewrite → Expand → Retrieve
    3. Answer Generation → Validation loop → Simplification
    4. Citation extraction → URL resolution → Finalization
"""

import time
from typing import Any, Optional

from langgraph.graph import StateGraph, END
from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger
from app.agents.types import GraphState
from app.agents.nodes import (
    node_classify_intent,
    node_collect_missing_details,
    node_rewrite_query,
    node_classify_query_for_constrained_rag,
    node_expand_query,
    node_retrieve_docs,
    node_search_case_law,
    node_draft_answer,
    node_draft_document,
    node_validate_answer,
    node_validate_severity,
    node_simplify_output,
    node_extract_citations,
    node_resolve_citations,
    node_finalize_response,
    should_clarify,
    should_validate,
    is_out_of_scope,
    should_search_web,
)

# Get tracer for this module
tracer = trace.get_tracer(__name__)


def create_legal_assistant_graph() -> StateGraph:
    """
    Create the LangGraph workflow for the legal assistant.
    
    Workflow:
    1. Classify Intent → Check if clarification needed
    2. If clarification needed → Collect details → Return question
    3. If clear → Rewrite query → Retrieve docs
    4. Generate draft → Validate (loop) → Simplify → Extract citations
    5. Resolve citations to official URLs (internet search)
    6. Finalize response
    
    Returns:
        StateGraph: Compiled LangGraph workflow
    """
    
    # Create the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("classify_intent", node_classify_intent)
    workflow.add_node("collect_missing_details", node_collect_missing_details)
    workflow.add_node("rewrite_query", node_rewrite_query)
    workflow.add_node("classify_query", node_classify_query_for_constrained_rag)  # NEW: Constrained RAG
    workflow.add_node("expand_query", node_expand_query)
    workflow.add_node("retrieve_docs", node_retrieve_docs)
    workflow.add_node("draft_answer", node_draft_answer)
    workflow.add_node("draft_document", node_draft_document)
    workflow.add_node("validate_answer", node_validate_answer)
    workflow.add_node("validate_severity", node_validate_severity)  # NEW: Severity validation
    workflow.add_node("simplify_output", node_simplify_output)
    workflow.add_node("extract_citations", node_extract_citations)
    workflow.add_node("resolve_citations", node_resolve_citations)  # NEW: Internet URL lookup
    workflow.add_node("finalize_response", node_finalize_response)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    # Add conditional edges from classify_intent
    workflow.add_conditional_edges(
        "classify_intent",
        should_clarify,
        {
            "clarify": "collect_missing_details",
            "draft": "draft_document",
            "continue": "rewrite_query"
        }
    )
    
    # Clarification path ends (returns to user for more info)
    workflow.add_edge("collect_missing_details", "finalize_response")
    
    # Drafting path
    workflow.add_edge("draft_document", "finalize_response")
    
    # Main processing path
    workflow.add_node("search_case_law", node_search_case_law)
    
    workflow.add_edge("rewrite_query", "classify_query")      # NEW: Classify before expand
    workflow.add_edge("classify_query", "expand_query")       # Then expand
    workflow.add_edge("expand_query", "retrieve_docs")
    
    # Conditional Web Search (Stage 2 Fallback)
    workflow.add_conditional_edges(
        "retrieve_docs",
        should_search_web,
        {
            "draft": "draft_answer",      # Stage 1: Local docs sufficient
            "search": "search_case_law"   # Stage 2: Web search needed
        }
    )
    
    workflow.add_edge("search_case_law", "draft_answer")
    
    # Conditional validation
    workflow.add_conditional_edges(
        "draft_answer",
        should_validate,
        {
            "validate": "validate_answer",
            "skip_validation": "simplify_output"
        }
    )
    
    workflow.add_edge("validate_answer", "validate_severity")  # NEW: Check severity match
    workflow.add_edge("validate_severity", "simplify_output")
    workflow.add_edge("simplify_output", "extract_citations")
    workflow.add_edge("extract_citations", "resolve_citations")  # NEW: Resolve to URLs
    workflow.add_edge("resolve_citations", "finalize_response")
    
    # End
    workflow.add_edge("finalize_response", END)
    
    return workflow.compile()


# Compiled graph singleton
_compiled_graph = None


def get_legal_assistant_graph() -> StateGraph:
    """
    Get the compiled legal assistant graph (singleton).
    
    Returns:
        StateGraph: Compiled graph
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_legal_assistant_graph()
        logger.info("Legal assistant graph compiled")
    return _compiled_graph


from app.core.cache import get_cache_service

class LegalAssistantService:
    """
    High-level service for running the legal assistant.
    
    Provides a simple interface for processing queries through
    the LangGraph workflow with full tracing.
    """
    
    def __init__(self) -> None:
        """Initialize the legal assistant service."""
        self.graph = get_legal_assistant_graph()
        # Cache service is retrieved asynchronously in process_query
    
    @tracer.start_as_current_span("legal_assistant_process")
    async def process_query(
        self,
        query: str,
        language: str = "en",
        session_id: Optional[str] = None,
        mode: str = "normal",
        chat_history: list[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Process a legal query through the full pipeline.
        
        Args:
            query: User's legal question
            language: Target language for response
            session_id: Optional session identifier for tracking
            mode: Response mode (normal, lawyer, qa, web, deep)
            chat_history: Previous conversation history
            
        Returns:
            dict: Response containing answer, citations, and metadata
        """
        span = trace.get_current_span()
        span.set_attribute("query", query[:100])
        span.set_attribute("language", language)
        span.set_attribute("mode", mode)
        if session_id:
            span.set_attribute("session_id", session_id)
        
        start_time = time.time()
        
        # Get cache service
        cache = await get_cache_service()
        
        # Check cache (include history in key if present to avoid stale context)
        cache_key_suffix = str(len(chat_history)) if chat_history else "0"
        cache_key = cache.generate_key("query", query, language, mode + cache_key_suffix)
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info("Cache hit", query=query)
            span.set_attribute("cache_hit", True)
            cached_result["processing_time_ms"] = int((time.time() - start_time) * 1000)
            return cached_result
            
        try:
            # Initialize state
            initial_state: GraphState = {
                "query": query,
                "language": language,
                "mode": mode,
                "clarified_query": "",
                "intent": "",
                "intent_confidence": 0.0,
                "needs_clarification": False,
                "clarification_question": "",
                "retrieved_docs": [],
                "context": "",
                "draft_answer": "",
                "final_answer": "",
                "citations": [],
                "related_cases": [],
                "is_valid": False,
                "validation_attempts": 0,
                "issues": [],
                "error": "",
                "awaiting_search_approval": False,
                "search_approved": False,
                "chat_history": chat_history or []
            }
            
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            span.set_attribute("processing_time_ms", processing_time)
            span.set_attribute("is_valid", final_state.get("is_valid", False))
            span.set_attribute("needs_clarification", final_state.get("needs_clarification", False))
            
            # Build response
            response = self._build_response(final_state, processing_time)
            
            # Cache successful responses
            if response.get("success") and not response.get("needs_clarification"):
                await cache.set(cache_key, response)
            
            logger.info(
                "Query processed successfully",
                processing_time_ms=processing_time,
                is_valid=final_state.get("is_valid"),
                citations_count=len(final_state.get("citations", []))
            )
            
            return response
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            import traceback
            logger.error(f"Query processing failed: {str(e)}\n{traceback.format_exc()}")
            
            return {
                "success": False,
                "error": str(e),
                "answer": "I apologize, but I encountered an error processing your question. Please try again.",
                "citations": [],
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
    
    def _build_response(
        self,
        state: GraphState,
        processing_time: int
    ) -> dict[str, Any]:
        """Build the response object from final state."""
        
        # Handle clarification case
        if state.get("needs_clarification"):
            return {
                "success": True,
                "needs_clarification": True,
                "clarification_question": state.get("clarification_question", ""),
                "answer": state.get("clarification_question", "Could you provide more details?"),
                "citations": [],
                "processing_time_ms": processing_time
            }
        
        # Normal response
        return {
            "success": True,
            "needs_clarification": False,
            "awaiting_search_approval": state.get("awaiting_search_approval", False),
            "answer": state.get("final_answer", ""),
            "citations": state.get("citations", []),
            "is_valid": state.get("is_valid", False),
            "validation_attempts": state.get("validation_attempts", 0),
            "intent": state.get("intent", ""),
            "processing_time_ms": processing_time,
            "debug": {
                "retrieved_docs_count": len(state.get("retrieved_docs", [])),
                "draft_length": len(state.get("draft_answer", "")),
                "final_length": len(state.get("final_answer", "")),
                "issues": state.get("issues", [])
            } if settings.debug else None
        }
    
    @tracer.start_as_current_span("legal_assistant_stream")
    async def process_query_stream(
        self,
        query: str,
        language: str = "en"
    ):
        """
        Process a query with streaming updates.
        
        Yields status updates as the query progresses through nodes.
        
        Args:
            query: User's legal question
            language: Target language
            
        Yields:
            dict: Status updates and final response
        """
        span = trace.get_current_span()
        span.set_attribute("query", query[:100])
        span.set_attribute("streaming", True)
        
        start_time = time.time()
        
        # Initialize state
        initial_state: GraphState = {
            "query": query,
            "language": language,
            "clarified_query": "",
            "intent": "",
            "intent_confidence": 0.0,
            "needs_clarification": False,
            "clarification_question": "",
            "retrieved_docs": [],
            "context": "",
            "draft_answer": "",
            "final_answer": "",
            "citations": [],
            "is_valid": False,
            "validation_attempts": 0,
            "issues": [],
            "error": ""
        }
        
        # Stream through the graph
        async for event in self.graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in event.items():
                yield {
                    "type": "progress",
                    "node": node_name,
                    "status": "completed"
                }
        
        # Get final state
        final_state = self.graph.invoke(initial_state)
        processing_time = int((time.time() - start_time) * 1000)
        
        yield {
            "type": "complete",
            "response": self._build_response(final_state, processing_time)
        }


# Convenience functions

async def process_legal_query(
    query: str,
    language: str = "en",
    session_id: Optional[str] = None,
    mode: str = "normal",
    chat_history: list[dict[str, str]] = None
) -> dict[str, Any]:
    """
    Process a legal query through the assistant.
    
    Args:
        query: User's legal question
        language: Target language
        session_id: Optional session ID
        mode: Response mode (normal, lawyer, qa, web, deep)
        chat_history: Previous conversation history
        
    Returns:
        dict: Response with answer and citations
    """
    service = LegalAssistantService()
    return await service.process_query(query, language, session_id, mode, chat_history)


def get_assistant_service() -> LegalAssistantService:
    """
    Get a legal assistant service instance.
    
    Returns:
        LegalAssistantService: Service instance
    """
    return LegalAssistantService()
