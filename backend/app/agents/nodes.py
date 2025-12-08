"""
NyayamGPT - LangGraph Node Functions
====================================
Individual node functions for the LangGraph workflow with tracing.
"""

from typing import Any, TypedDict
import traceback

from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger
from app.agents.reasoning import (
    classify_intent,
    generate_clarification,
    rewrite_query,
    generate_draft_answer,
    simplify_answer,
    extract_citations,
    translate_query,
    expand_query,
    generate_legal_draft,
)
from app.agents.validator import validate_and_refine
from app.rag.vectorstore import search_vectorstore, SearchResult

# Get tracer for this module
tracer = trace.get_tracer(__name__)


class GraphState(TypedDict, total=False):
    """
    State object passed between LangGraph nodes.
    
    Attributes:
        query: Original user query
        clarified_query: Query after clarification/rewriting
        intent: Classified intent of the query
        needs_clarification: Whether clarification is needed
        clarification_question: Question to ask for clarification
        retrieved_docs: List of retrieved documents
        context: Formatted context string from retrieved docs
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
    """
    query: str
    clarified_query: str
    intent: str
    intent_confidence: float
    needs_clarification: bool
    clarification_question: str
    retrieved_docs: list[dict[str, Any]]
    context: str
    draft_answer: str
    final_answer: str
    citations: list[dict[str, Any]]
    related_cases: list[dict[str, Any]]
    is_valid: bool
    validation_attempts: int
    issues: list[str]
    error: str
    language: str
    mode: str
    original_query: str
    awaiting_search_approval: bool
    search_approved: bool
    chat_history: list[dict[str, str]]
    expanded_queries: list[str]
    local_docs_sufficient: bool


# Minimum relevance score threshold (0-1, higher = more relevant)
MIN_RELEVANCE_SCORE = 0.3


def _format_docs_as_context(docs: list[SearchResult]) -> str:
    """Format retrieved documents as context string with relevance filtering."""
    if not docs:
        return "No relevant documents found."
    
    # Filter documents by relevance score
    relevant_docs = [doc for doc in docs if doc.score >= MIN_RELEVANCE_SCORE]
    
    if not relevant_docs:
        return "No relevant documents found matching the query."
    
    context_parts = []
    for i, doc in enumerate(relevant_docs, 1):
        metadata = doc.metadata
        # Include relevance score to help the LLM prioritize
        context_parts.append(
            f"[Document {i}] (Relevance: {doc.score:.2f})\n"
            f"Law: {metadata.law}\n"
            f"Section: {metadata.section}\n"
            f"Title: {metadata.title}\n"
            f"Content: {doc.text}\n"
            f"Source: {metadata.source_url or 'N/A'}\n"
        )
    
    return "\n---\n".join(context_parts)


def _docs_to_dict_list(docs: list[SearchResult]) -> list[dict[str, Any]]:
    """Convert SearchResult list to dict list for state storage."""
    return [
        {
            "text": doc.text,
            "law": doc.metadata.law,
            "section": doc.metadata.section,
            "title": doc.metadata.title,
            "source_url": doc.metadata.source_url,
            "score": doc.score,
            "embedding_id": doc.embedding_id
        }
        for doc in docs
    ]


@tracer.start_as_current_span("node_classify_intent")
async def node_classify_intent(state: GraphState) -> GraphState:
    """
    Classify the user's intent and translate if necessary.
    """
    span = trace.get_current_span()
    query = state["query"]
    span.set_attribute("query", query[:100])
    
    try:
        # 1. Translate Query First
        translation_result = await translate_query(query)
        english_query = translation_result.get("translated_query", query)
        detected_lang = translation_result.get("original_language", "English")
        
        # If user didn't specify a language preference in the UI, use the detected one
        target_language = state.get("language")
        if not target_language or target_language == "en":
            target_language = detected_lang

        # LOGGING FOR DEBUGGING
        print(f"\n[LANGUAGE DETECTION] Input: '{query}'")
        print(f"[LANGUAGE DETECTION] Detected: '{detected_lang}'")
        print(f"[LANGUAGE DETECTION] Target: '{target_language}'")
        print(f"[LANGUAGE DETECTION] Translated: '{english_query}'\n")

        span.set_attribute("detected_language", detected_lang)
        span.set_attribute("english_query", english_query)
        
        # 2. Classify Intent using English Query
        result = await classify_intent(english_query)
        
        intent = result.get("intent", "LEGAL_QUERY")
        confidence = result.get("confidence", 0.5)
        needs_clarification = result.get("needs_clarification", False)
        clarification_question = result.get("clarification_question", "")
        
        span.set_attribute("intent", intent)
        span.set_attribute("confidence", confidence)
        span.set_attribute("needs_clarification", needs_clarification)
        
        logger.info(
            "Intent classified",
            intent=intent,
            confidence=confidence,
            language=detected_lang
        )
        
        return {
            **state,
            "query": english_query,  # Update state with English query for downstream nodes
            "original_query": query, # Keep original for reference
            "language": target_language, # Ensure response is in user's language
            "intent": intent,
            "intent_confidence": confidence,
            "needs_clarification": needs_clarification and intent == "CLARIFICATION_NEEDED",
            "clarification_question": clarification_question
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Intent classification failed", error=str(e))
        return {
            **state,
            "intent": "LEGAL_QUERY",
            "intent_confidence": 0.5,
            "needs_clarification": False,
            "error": str(e)
        }


@tracer.start_as_current_span("node_collect_missing_details")
async def node_collect_missing_details(state: GraphState) -> GraphState:
    """
    Generate clarifying questions when query is unclear.
    """
    span = trace.get_current_span()
    query = state["query"]
    
    try:
        clarification = await generate_clarification(query)
        
        span.set_attribute("clarification_generated", True)
        
        return {
            **state,
            "clarification_question": clarification,
            "needs_clarification": True
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Clarification generation failed", error=str(e))
        return {
            **state,
            "needs_clarification": False,
            "error": str(e)
        }


@tracer.start_as_current_span("node_rewrite_query")
async def node_rewrite_query(state: GraphState) -> GraphState:
    """
    Rewrite the query for optimal legal document search.
    """
    span = trace.get_current_span()
    query = state["query"]
    
    try:
        rewritten = await rewrite_query(query)
        
        span.set_attribute("original_length", len(query))
        span.set_attribute("rewritten_length", len(rewritten))
        
        logger.debug(
            "Query rewritten",
            original=query[:50],
            rewritten=rewritten[:50]
        )
        
        return {
            **state,
            "clarified_query": rewritten
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Query rewrite failed", error=str(e))
        # Use original query if rewrite fails
        return {
            **state,
            "clarified_query": query
        }



@tracer.start_as_current_span("node_expand_query")
async def node_expand_query(state: GraphState) -> GraphState:
    """
    Expand the query into multiple search queries.
    """
    span = trace.get_current_span()
    query = state.get("clarified_query") or state["query"]
    
    try:
        expanded = await expand_query(query)
        span.set_attribute("expanded_count", len(expanded))
        
        return {
            **state,
            "expanded_queries": expanded
        }
    except Exception as e:
        logger.error("Query expansion failed", error=str(e))
        return {
            **state,
            "expanded_queries": [query]
        }


@tracer.start_as_current_span("node_retrieve_docs")
def node_retrieve_docs(state: GraphState) -> GraphState:
    """
    Retrieve relevant legal documents from vector store.
    """
    span = trace.get_current_span()
    query = state.get("clarified_query") or state["query"]
    expanded_queries = state.get("expanded_queries", [query])
    
    try:
        all_docs = []
        seen_ids = set()
        
        # Search for each query
        for q in expanded_queries:
            docs = search_vectorstore(q, k=settings.retrieval_top_k)
            for doc in docs:
                # Deduplicate
                doc_id = f"{doc.metadata.law}-{doc.metadata.section}"
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
        
        # Sort by score and take top K
        all_docs.sort(key=lambda x: x.score, reverse=True)
        docs = all_docs[:settings.retrieval_top_k]
        
        # Log retrieved documents with scores for debugging
        print(f"\n[RETRIEVAL] Query: {query}")
        print(f"[RETRIEVAL] Found {len(docs)} documents:")
        for i, doc in enumerate(docs):
            print(f"  [{i+1}] Score: {doc.score:.3f} | {doc.metadata.law} {doc.metadata.section}: {doc.metadata.title[:50]}...")
        
        # Filter by relevance score
        relevant_docs = [doc for doc in docs if doc.score >= MIN_RELEVANCE_SCORE]
        print(f"[RETRIEVAL] After filtering (>={MIN_RELEVANCE_SCORE}): {len(relevant_docs)} documents\n")
        
        span.set_attribute("docs_retrieved", len(docs))
        span.set_attribute("docs_relevant", len(relevant_docs))
        span.set_attribute("query_used", query[:100])
        
        # Format context
        context = _format_docs_as_context(docs)
        docs_list = _docs_to_dict_list(docs)
        
        logger.info(
            "Documents retrieved",
            count=len(docs),
            relevant=len(relevant_docs),
            query=query[:50]
        )
        
        return {
            **state,
            "retrieved_docs": docs_list,
            "context": context,
            "local_docs_sufficient": len(relevant_docs) > 0
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Document retrieval failed", error=str(e))
        return {
            **state,
            "retrieved_docs": [],
            "context": "No documents retrieved due to an error.",
            "error": str(e)
        }


from app.services.kanoon_client import get_kanoon_client
from app.services.web_search import WebSearchService
import asyncio

@tracer.start_as_current_span("node_search_case_law")
async def node_search_case_law(state: GraphState) -> GraphState:
    """
    Search for related case laws and legal articles from trusted sources.
    Uses WebSearchService to find information from multiple trusted Indian legal sites.
    """
    span = trace.get_current_span()
    query = state.get("clarified_query") or state["query"]
    
    logger.info(f"Starting web search for query: {query}")
    
    try:
        # Use WebSearchService for broader coverage (Perplexity-like)
        service = WebSearchService()
        
        # Run sync search in executor
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, 
            service.search_legal_sources, 
            query
        )
        
        logger.debug(f"Web search returned {len(results)} results")
        
        related_cases = []
        for res in results:
            related_cases.append({
                "title": res.get("title", "Unknown Title"),
                "url": res.get("url", ""),
                "snippet": res.get("snippet", ""),
                "source": res.get("source", "Web")
            })
            
        span.set_attribute("cases_found", len(related_cases))
        logger.info("Related legal info found", count=len(related_cases))
        
        return {
            **state,
            "related_cases": related_cases
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        error_msg = str(e)
        tb = traceback.format_exc()
        logger.error(f"Legal web search failed: {error_msg}\n{tb}")
        return {
            **state,
            "related_cases": []
        }


@tracer.start_as_current_span("node_draft_answer")
async def node_draft_answer(state: GraphState) -> GraphState:
    """
    Generate initial draft answer based on retrieved documents.
    """
    span = trace.get_current_span()
    query = state["query"]
    context = state.get("context", "")
    language = state.get("language", "English")
    related_cases = state.get("related_cases", [])
    
    try:
        # Check if we have any context (local or web)
        has_local_context = context and "No relevant documents found" not in context
        has_web_context = len(related_cases) > 0
        
        if not has_local_context and not has_web_context:
            from app.agents.prompts import NO_CONTEXT_RESPONSE
            return {
                **state,
                "draft_answer": NO_CONTEXT_RESPONSE,
                "final_answer": NO_CONTEXT_RESPONSE,
                "is_valid": True,  # Skip validation for no-context response
                "awaiting_search_approval": True  # Ask user if they want internet search
            }
        
        # Format cases for prompt
        cases_context = ""
        if related_cases:
            cases_context = "\n\nRelated Legal Sources (Cases/Articles):\n" + "\n".join(
                [f"- [{c['source']}] {c['title']}: {c['snippet']} ({c['url']})" for c in related_cases]
            )
        
        # If no local context but we have web context, use a generic header
        if not has_local_context:
            context = "No specific local documents found, but related online cases are available."
            
        full_context = context + cases_context
        
        draft = await generate_draft_answer(
            query, 
            full_context, 
            language,
            chat_history=state.get("chat_history")
        )
        
        span.set_attribute("draft_length", len(draft))
        
        logger.info("Draft answer generated", length=len(draft))
        
        return {
            **state,
            "draft_answer": draft,
            "context": full_context, # Update context for validation
            "awaiting_search_approval": False
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Draft generation failed", error=str(e))
        return {
            **state,
            "draft_answer": "I apologize, but I encountered an error generating a response.",
            "error": str(e)
        }


@tracer.start_as_current_span("node_draft_document")
async def node_draft_document(state: GraphState) -> GraphState:
    """
    Generate a legal document draft.
    """
    span = trace.get_current_span()
    query = state["query"]
    context = state.get("context", "")
    
    try:
        draft = await generate_legal_draft(query, context)
        
        return {
            **state,
            "draft_answer": draft,
            "final_answer": draft,
            "is_valid": True 
        }
    except Exception as e:
        logger.error("Draft generation failed", error=str(e))
        return {
            **state,
            "error": "Failed to generate draft."
        }


@tracer.start_as_current_span("node_validate_answer")
async def node_validate_answer(state: GraphState) -> GraphState:
    """
    Validate and refine the draft answer using the validation loop.
    """
    span = trace.get_current_span()
    query = state["query"]
    context = state.get("context", "")
    draft = state.get("draft_answer", "")
    
    # Skip validation if already valid (e.g., no-context response)
    if state.get("is_valid"):
        return state
    
    try:
        final_answer, is_valid, history = await validate_and_refine(
            query=query,
            context=context,
            answer=draft
        )
        
        span.set_attribute("is_valid", is_valid)
        span.set_attribute("attempts", len(history))
        
        # Collect issues from validation history
        all_issues = []
        for validation in history:
            all_issues.extend(validation.problems)
        
        logger.info(
            "Validation completed",
            is_valid=is_valid,
            attempts=len(history)
        )
        
        return {
            **state,
            "final_answer": final_answer,
            "is_valid": is_valid,
            "validation_attempts": len(history),
            "issues": all_issues
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Validation failed", error=str(e))
        # Use draft as final if validation fails
        return {
            **state,
            "final_answer": draft,
            "is_valid": False,
            "error": str(e)
        }


@tracer.start_as_current_span("node_simplify_output")
async def node_simplify_output(state: GraphState) -> GraphState:
    """
    Simplify the legal language in the answer.
    """
    span = trace.get_current_span()
    answer = state.get("final_answer", state.get("draft_answer", ""))
    
    try:
        simplified = await simplify_answer(answer)
        
        span.set_attribute("original_length", len(answer))
        span.set_attribute("simplified_length", len(simplified))
        
        logger.debug("Answer simplified")
        
        return {
            **state,
            "final_answer": simplified
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Simplification failed", error=str(e))
        # Keep original if simplification fails
        return state


@tracer.start_as_current_span("node_extract_citations")
async def node_extract_citations(state: GraphState) -> GraphState:
    """
    Extract legal citations from the final answer.
    """
    span = trace.get_current_span()
    answer = state.get("final_answer", "")
    retrieved_docs = state.get("retrieved_docs", [])
    related_cases = state.get("related_cases", [])
    
    try:
        # Extract citations from answer
        citations = await extract_citations(answer)
        
        # Enrich with source URLs from retrieved docs AND web search results
        for citation in citations:
            found = False
            
            # 1. Check local retrieved docs
            for doc in retrieved_docs:
                if (
                    doc.get("law") == citation.get("law") and
                    doc.get("section") == citation.get("section")
                ):
                    citation["source_url"] = doc.get("source_url")
                    citation["verified"] = True
                    found = True
                    break
            
            # 2. If not found, check web search results (related_cases)
            if not found:
                # Simple heuristic: check if law/section or case name appears in title/snippet
                # This is fuzzy matching because web results don't have structured law/section fields
                search_term = f"{citation.get('law')} {citation.get('section')}"
                for case in related_cases:
                    if search_term.lower() in (case.get("title", "") + case.get("snippet", "")).lower():
                        citation["source_url"] = case.get("url")
                        citation["verified"] = True
                        found = True
                        break
            
            if not found:
                citation["verified"] = False
        
        span.set_attribute("citations_count", len(citations))
        
        logger.info("Citations extracted", count=len(citations))
        
        return {
            **state,
            "citations": citations
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Citation extraction failed", error=str(e))
        return {
            **state,
            "citations": []
        }


@tracer.start_as_current_span("node_resolve_citations")
def node_resolve_citations(state: GraphState) -> GraphState:
    """
    Resolve citations to official government URLs using internet search.
    
    This node searches for official URLs from:
    - Indian Kanoon API (primary)
    - indiacode.nic.in
    - legislative.gov.in
    - egazette.nic.in
    - prsindia.org
    """
    import asyncio
    
    span = trace.get_current_span()
    citations = state.get("citations", [])
    
    if not citations:
        return state
    
    try:
        from app.agents.citation_resolver import resolve_citations
        
        # Run async resolution in sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            # If already in async context, create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, resolve_citations(citations))
                resolved_citations = future.result()
        else:
            # No running loop, safe to use asyncio.run
            resolved_citations = asyncio.run(resolve_citations(citations))
        
        verified_count = sum(1 for c in resolved_citations if c.get("verified"))
        span.set_attribute("citations_resolved", len(resolved_citations))
        span.set_attribute("citations_verified", verified_count)
        
        logger.info(
            "Citations resolved to URLs",
            total=len(resolved_citations),
            verified=verified_count
        )
        
        return {
            **state,
            "citations": resolved_citations
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Citation resolution failed", error=str(e))
        # Keep original citations if resolution fails
        return state


@tracer.start_as_current_span("node_finalize_response")
def node_finalize_response(state: GraphState) -> GraphState:
    """
    Finalize the response with formatting and metadata.
    """
    span = trace.get_current_span()
    
    final_answer = state.get("final_answer", "")
    citations = state.get("citations", [])
    is_valid = state.get("is_valid", False)
    
    # Add rephrased query confirmation if applicable
    original_query = state.get("original_query", "")
    clarified_query = state.get("clarified_query", "")
    
    # Only add if we have a clarified query and it's not a clarification request itself
    if clarified_query and not state.get("needs_clarification"):
        # Clean up the query for display
        display_query = clarified_query.strip('"').strip("'")
        
        # Add the "Understanding" section ONLY if language is English
        # For other languages, we skip this to avoid mixed-language output
        if state.get("language", "English") == "English":
            preamble = f"I interpreted your question as \"{display_query}\".\n\n"
            final_answer = preamble + final_answer.lstrip()

    # Log final state
    span.set_attribute("final_answer_length", len(final_answer))
    span.set_attribute("citations_count", len(citations))
    span.set_attribute("is_valid", is_valid)
    
    logger.info(
        "Response finalized",
        answer_length=len(final_answer),
        citations=len(citations),
        valid=is_valid
    )
    
    return {
        **state,
        "final_answer": final_answer
    }


# Conditional edge functions

def should_clarify(state: GraphState) -> str:
    """Determine next step based on intent."""
    if state.get("needs_clarification"):
        return "clarify"
    
    intent = state.get("intent")
    if intent == "LEGAL_DRAFTING":
        return "draft"
        
    return "continue"


def should_validate(state: GraphState) -> str:
    """Determine if validation should be skipped."""
    if state.get("is_valid"):
        return "skip_validation"
    return "validate"


def is_out_of_scope(state: GraphState) -> str:
    """Check if query is out of scope."""
    intent = state.get("intent", "")
    if intent == "OUT_OF_SCOPE":
        return "out_of_scope"
    return "continue"


def should_search_web(state: GraphState) -> str:
    """Determine if web search is needed (Stage 2)."""
    # If local docs are sufficient (Stage 1), skip web search
    if state.get("local_docs_sufficient", False):
        return "draft"
    # Otherwise, trigger web search (Stage 2)
    return "search"

    return "in_scope"
