"""
NyayamGPT - LangGraph Node Functions (v2.0)
============================================
Individual node functions for the LangGraph workflow with tracing.

Each node is a pure function that:
- Takes GraphState as input
- Returns updated GraphState
- Has OpenTelemetry tracing
- Handles errors gracefully
"""

from typing import Any
import traceback

from opentelemetry import trace

from app.core.config import settings
from app.core.logging import logger
from app.agents.types import GraphState
from app.agents.reasoning import (
    classify_intent,
    generate_clarification,
    rewrite_query,
    generate_draft_answer,
    generate_constrained_answer,
    validate_severity_match,
    simplify_answer,
    extract_citations,
    extract_citations_regex,
    translate_query,
    expand_query,
    generate_legal_draft,
    translate_and_classify,
    rewrite_and_expand_query,
)
from app.agents.validator import validate_and_refine
from app.rag.vectorstore import search_vectorstore, SearchResult
from app.agents.query_classifier import (
    QueryClassifier, 
    QueryClassification,
    OffenseNature,
    SeverityLevel,
    build_vector_filter,
    build_hybrid_search_query
)

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Singleton query classifier
_query_classifier = QueryClassifier()


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
    
    OPTIMIZED: Uses a single combined LLM call for both translation + classification.
    """
    span = trace.get_current_span()
    query = state["query"]
    span.set_attribute("query", query[:100])
    
    try:
        # Single combined LLM call: translate + classify
        result = await translate_and_classify(query)
        
        english_query = result.get("translated_query", query)
        detected_lang = result.get("original_language", "English")
        intent = result.get("intent", "LEGAL_QUERY")
        confidence = result.get("confidence", 0.5)
        needs_clarification = result.get("needs_clarification", False)
        clarification_question = result.get("clarification_question", "")
        
        # If user didn't specify a language preference in the UI, use the detected one
        target_language = state.get("language")
        if not target_language or target_language == "en":
            target_language = detected_lang

        # LOGGING FOR DEBUGGING
        print(f"\n[COMBINED TRANSLATE+CLASSIFY] Input: '{query}'")
        print(f"[COMBINED TRANSLATE+CLASSIFY] Detected: '{detected_lang}' | Intent: '{intent}' | Conf: {confidence}")
        print(f"[COMBINED TRANSLATE+CLASSIFY] Translated: '{english_query}'\n")

        span.set_attribute("detected_language", detected_lang)
        span.set_attribute("english_query", english_query)
        span.set_attribute("intent", intent)
        span.set_attribute("confidence", confidence)
        span.set_attribute("needs_clarification", needs_clarification)
        
        logger.info(
            "Intent classified (combined)",
            intent=intent,
            confidence=confidence,
            language=detected_lang
        )
        
        return {
            **state,
            "query": english_query,
            "original_query": query,
            "language": target_language,
            "intent": intent,
            "intent_confidence": confidence,
            "needs_clarification": needs_clarification and intent == "CLARIFICATION_NEEDED",
            "clarification_question": clarification_question
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Combined translate+classify failed", error=str(e))
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


@tracer.start_as_current_span("node_conversational_response")
async def node_conversational_response(state: GraphState) -> GraphState:
    """
    Handle conversational queries (greetings, identity, capabilities, casual chat)
    immediately WITHOUT going through the full RAG pipeline.
    
    This node uses pattern matching for instant responses, falling back to
    LLM only for ambiguous conversational queries.
    """
    span = trace.get_current_span()
    query = state.get("query", "").strip().lower()
    original_query = state.get("original_query", state.get("query", ""))
    language = state.get("language", "English")
    
    span.set_attribute("conversational_query", query[:100])
    
    # Pattern-based instant responses (no LLM needed)
    RESPONSES = {
        "greeting": (
            ["hi", "hello", "hey", "namaste", "namaskar", "good morning", "good afternoon", 
             "good evening", "good night", "howdy", "greetings", "hola", "vanakkam",
             "namaskaram", "sat sri akal", "assalam", "pranam"],
            "Namaste! 🙏 I'm **NyayamGPT** — India's AI-powered legal expert. I can help you understand Indian laws, legal procedures, your rights, and much more.\n\nHow can I assist you today? Just describe your legal question or situation!"
        ),
        "identity": (
            ["who are you", "what are you", "what is nyayamgpt", "who is nyayamgpt", 
             "tell me about yourself", "introduce yourself", "what's your name",
             "your name", "who made you", "who created you", "who built you",
             "aap kaun ho", "tum kaun ho", "kaun ho tum", "aap kya ho"],
            "I'm **NyayamGPT** — India's most advanced AI legal expert! 🏛️\n\n**What I do:** I provide comprehensive guidance on Indian law, covering:\n- **Criminal Law** (BNS, BNSS, BSA — the new 2024 codes)\n- **Civil & Property Law** (CPC, Transfer of Property, RERA)\n- **Family Law** (Hindu Marriage Act, Divorce, Maintenance, DV Act)\n- **Constitutional Law** (Fundamental Rights, Writs, PIL)\n- **Cyber Crime** (IT Act, online fraud, data privacy)\n- **Consumer, Labour, Tax, Corporate Law** and all Special Statutes\n\nI can explain legal provisions, guide you on procedures, help draft legal documents, and help you understand your rights. Ask me anything about Indian law!"
        ),
        "capability": (
            ["what can you do", "how can you help", "what do you do", "help me",
             "what are your capabilities", "what help can you provide",
             "kya kar sakte ho", "kya help kar sakte ho", "madad karo"],
            "Here's what I can help you with:\n\n🔍 **Legal Research** — Explain any Indian law, section, or legal concept\n📋 **Case Analysis** — Analyze your situation and identify applicable laws\n📝 **Legal Drafting** — Draft complaints, notices, petitions, and affidavits\n⚖️ **Rights & Remedies** — Tell you your rights and what legal action you can take\n🏛️ **Procedures** — Guide you on how to file FIRs, complaints, and court cases\n📚 **New Laws** — Expert on BNS, BNSS, BSA (the 2024 criminal law codes)\n\nJust describe your situation or ask a legal question — I'll take it from there!"
        ),
        "thanks": (
            ["thank you", "thanks", "thank u", "thankyou", "thanks a lot", "great answer",
             "helpful", "very helpful", "nice", "awesome", "perfect", "excellent",
             "dhanyavaad", "shukriya", "bahut accha"],
            "You're welcome! 😊 I'm glad I could help.\n\nFeel free to ask if you have any more legal questions — I'm here for you!"
        ),
        "casual": (
            ["how are you", "what are you doing", "what's up", "how's it going",
             "how do you do", "kaise ho", "kya haal hai", "kya chal raha hai"],
            "I'm doing great, thank you for asking! 😊 As **NyayamGPT**, I'm always ready to help with Indian legal questions.\n\nDo you have a legal question I can help with today?"
        ),
    }
    
    # Check patterns
    response_text = None
    for category, (patterns, response) in RESPONSES.items():
        for pattern in patterns:
            if pattern in query or query.startswith(pattern.split()[0]) and len(query.split()) <= 6:
                response_text = response
                span.set_attribute("conversational_category", category)
                break
        if response_text:
            break
    
    # Fallback for unmatched conversational queries
    if not response_text:
        response_text = (
            "Hello! I'm **NyayamGPT** — your AI legal expert for Indian law. 🏛️\n\n"
            "I specialize in Indian legal matters — from criminal and civil law to constitutional rights, "
            "family disputes, property issues, cyber crime, and more.\n\n"
            "How can I help you today? Just ask any legal question!"
        )
        span.set_attribute("conversational_category", "fallback")
    
    logger.info("Conversational response generated", query=query[:50])
    
    return {
        **state,
        "final_answer": response_text,
        "draft_answer": response_text,
        "is_valid": True,
        "intent": "CONVERSATIONAL"
    }


@tracer.start_as_current_span("node_rewrite_query")
async def node_rewrite_query(state: GraphState) -> GraphState:
    """
    Rewrite AND expand the query in a single LLM call.
    
    OPTIMIZED: Combines rewrite + expand into one call, saving ~4 seconds.
    The expanded_queries are stored for downstream retrieve_docs node.
    """
    span = trace.get_current_span()
    query = state["query"]
    
    try:
        result = await rewrite_and_expand_query(query)
        
        if isinstance(result, dict):
            rewritten = result.get("rewritten_query", query)
            expanded = result.get("expanded_queries", [])
            # Ensure original query is included
            if query not in expanded:
                expanded.insert(0, query)
        else:
            rewritten = query
            expanded = [query]
        
        span.set_attribute("original_length", len(query))
        span.set_attribute("rewritten_length", len(rewritten))
        span.set_attribute("expanded_count", len(expanded))
        
        logger.debug(
            "Query rewritten+expanded (combined)",
            original=query[:50],
            rewritten=rewritten[:50],
            expanded_count=len(expanded)
        )
        
        return {
            **state,
            "clarified_query": rewritten,
            "expanded_queries": expanded[:5]
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Query rewrite+expand failed", error=str(e))
        # Use original query if rewrite fails
        return {
            **state,
            "clarified_query": query,
            "expanded_queries": [query]
        }


@tracer.start_as_current_span("node_classify_query_for_constrained_rag")
def node_classify_query_for_constrained_rag(state: GraphState) -> GraphState:
    """
    Classify the query for constrained RAG retrieval.
    
    This node runs BEFORE retrieval to:
    1. Determine offense type (verbal, physical, property, etc.)
    2. Detect context (caste, minor, woman, death)
    3. Build metadata filters for vector store
    4. Enhance the query with relevant keywords
    
    CRITICAL: This prevents citing murder sections for verbal abuse cases!
    """
    span = trace.get_current_span()
    query = state.get("clarified_query") or state["query"]
    
    try:
        # Run classifier
        classification = _query_classifier.classify(query)
        
        # Build vector store filter
        vector_filter = build_vector_filter(classification)
        
        # Build enhanced query
        enhanced_query = build_hybrid_search_query(query, classification)
        
        # Log classification for debugging
        print(f"\n{'='*60}")
        print(f"[QUERY CLASSIFIER] Constrained RAG Pre-processing")
        print(f"{'='*60}")
        print(f"  Query: {query}")
        print(f"  Offense Nature: {classification.offense_nature.value}")
        print(f"  Severity: {classification.severity_level.value}")
        print(f"  Confidence: {classification.confidence:.0%}")
        print(f"  Contexts: caste={classification.involves_caste}, death={classification.involves_death}, minor={classification.involves_minor}")
        print(f"  Include Keywords: {classification.must_include_keywords}")
        print(f"  Exclude Keywords: {classification.must_exclude_keywords}")
        print(f"  Topics: {classification.topic_filters}")
        print(f"  Vector Filter: {vector_filter}")
        print(f"  Enhanced Query: {enhanced_query}")
        print(f"  Reasoning: {classification.reasoning}")
        print(f"{'='*60}\n")
        
        span.set_attribute("offense_nature", classification.offense_nature.value)
        span.set_attribute("severity", classification.severity_level.value)
        span.set_attribute("confidence", classification.confidence)
        span.set_attribute("involves_caste", classification.involves_caste)
        
        logger.info(
            "Query classified for constrained RAG",
            offense_nature=classification.offense_nature.value,
            severity=classification.severity_level.value,
            confidence=classification.confidence
        )
        
        return {
            **state,
            "query_classification": {
                "offense_nature": classification.offense_nature.value,
                "severity_level": classification.severity_level.value,
                "involves_caste": classification.involves_caste,
                "involves_domestic": classification.involves_domestic,
                "involves_minor": classification.involves_minor,
                "involves_woman": classification.involves_woman,
                "involves_death": classification.involves_death,
                "must_include_keywords": classification.must_include_keywords,
                "must_exclude_keywords": classification.must_exclude_keywords,
                "topic_filters": classification.topic_filters,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning
            },
            "vector_filter": vector_filter,
            "enhanced_query": enhanced_query
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Query classification failed", error=str(e))
        # Proceed without classification - no filtering
        return {
            **state,
            "query_classification": None,
            "vector_filter": {},
            "enhanced_query": query
        }


@tracer.start_as_current_span("node_expand_query")
async def node_expand_query(state: GraphState) -> GraphState:
    """
    Expand the query into multiple search queries.
    
    OPTIMIZED: This is now a passthrough — expansion is done in node_rewrite_query.
    Kept for backward compatibility with the graph structure.
    """
    span = trace.get_current_span()
    
    # If already expanded by the combined rewrite+expand, just pass through
    if state.get("expanded_queries"):
        span.set_attribute("expanded_count", len(state["expanded_queries"]))
        span.set_attribute("passthrough", True)
        return state
    
    # Fallback: if somehow not expanded yet
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
    Retrieve relevant legal documents from vector store with CONSTRAINED RAG filtering.
    
    Uses pre-computed classification to:
    1. Apply metadata filters (e.g., exclude physical harm sections for verbal offenses)
    2. Use enhanced query with relevant keywords
    3. Post-filter results based on classification constraints
    """
    span = trace.get_current_span()
    query = state.get("clarified_query") or state["query"]
    expanded_queries = state.get("expanded_queries", [query])
    
    # Get classification-based filters from previous node
    vector_filter = state.get("vector_filter", {})
    enhanced_query = state.get("enhanced_query", query)
    classification = state.get("query_classification", {})
    
    # Get exclusion keywords for post-filtering
    must_exclude = classification.get("must_exclude_keywords", []) if classification else []
    
    try:
        all_docs = []
        seen_ids = set()
        
        # Use enhanced query if available, plus original expanded queries
        search_queries = [enhanced_query] if enhanced_query != query else []
        search_queries.extend(expanded_queries)
        
        # Search for each query WITH metadata filtering
        for q in search_queries:
            # Apply vector store metadata filter
            docs = search_vectorstore(q, k=settings.retrieval_top_k, filter_metadata=vector_filter if vector_filter else None)
            for doc in docs:
                # Deduplicate
                doc_id = f"{doc.metadata.law}-{doc.metadata.section}"
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_docs.append(doc)
        
        # Sort by score and take top K
        all_docs.sort(key=lambda x: x.score, reverse=True)
        docs = all_docs[:settings.retrieval_top_k]
        
        # POST-FILTERING: Apply keyword exclusions from classification
        # This catches cases where metadata filtering wasn't enough
        if must_exclude:
            filtered_docs = []
            for doc in docs:
                # Check if document contains exclusion keywords
                doc_text_lower = (doc.text + " " + doc.metadata.title).lower()
                should_exclude = any(kw.lower() in doc_text_lower for kw in must_exclude)
                
                if not should_exclude:
                    filtered_docs.append(doc)
                else:
                    print(f"  [CONSTRAINED RAG] EXCLUDED: {doc.metadata.law} {doc.metadata.section} (contains excluded term)")
            
            docs = filtered_docs
        
        # Log retrieved documents with scores for debugging
        print(f"\n[CONSTRAINED RAG RETRIEVAL]")
        print(f"  Query: {query}")
        print(f"  Enhanced Query: {enhanced_query}")
        print(f"  Metadata Filter: {vector_filter}")
        print(f"  Exclusion Keywords: {must_exclude}")
        print(f"  Results after filtering: {len(docs)} documents:")
        for i, doc in enumerate(docs[:5]):  # Show top 5
            print(f"    [{i+1}] Score: {doc.score:.3f} | {doc.metadata.law} {doc.metadata.section}: {doc.metadata.title[:50]}...")
        
        # Filter by relevance score
        relevant_docs = [doc for doc in docs if doc.score >= MIN_RELEVANCE_SCORE]
        print(f"  After relevance filtering (>={MIN_RELEVANCE_SCORE}): {len(relevant_docs)} documents\n")
        
        span.set_attribute("docs_retrieved", len(docs))
        span.set_attribute("docs_relevant", len(relevant_docs))
        span.set_attribute("query_used", query[:100])
        span.set_attribute("filter_applied", bool(vector_filter))
        
        # Format context
        context = _format_docs_as_context(docs)
        docs_list = _docs_to_dict_list(docs)
        
        logger.info(
            "Constrained RAG retrieval completed",
            count=len(docs),
            relevant=len(relevant_docs),
            filter_applied=bool(vector_filter),
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
    
    CONSTRAINED RAG: Uses pre-computed classification to generate
    a constrained answer that matches the offense type/severity.
    """
    span = trace.get_current_span()
    query = state["query"]
    context = state.get("context", "")
    language = state.get("language", "English")
    related_cases = state.get("related_cases", [])
    classification = state.get("query_classification", None)
    
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
        
        # Use CONSTRAINED generation if classification available
        if classification and classification.get("offense_nature") != "unknown":
            print(f"\n[CONSTRAINED RAG] Using constrained generation")
            print(f"  Offense Nature: {classification.get('offense_nature')}")
            print(f"  Severity: {classification.get('severity_level')}")
            print(f"  Involves Caste: {classification.get('involves_caste')}")
            
            draft = await generate_constrained_answer(
                query=query,
                context=full_context,
                classification=classification,
                language=language,
                chat_history=state.get("chat_history")
            )
            span.set_attribute("constrained_generation", True)
        else:
            # Fallback to standard generation
            print(f"\n[STANDARD RAG] Using standard generation (no classification)")
            draft = await generate_draft_answer(
                query, 
                full_context, 
                language,
                chat_history=state.get("chat_history")
            )
            span.set_attribute("constrained_generation", False)
        
        span.set_attribute("draft_length", len(draft))
        
        logger.info("Draft answer generated", length=len(draft), constrained=bool(classification))
        
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
            "draft_answer": "**Unable to process this request.** Please try rephrasing your question or try again in a moment.",
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


@tracer.start_as_current_span("node_validate_severity")
def node_validate_severity(state: GraphState) -> GraphState:
    """
    Validate that response severity matches the classified offense severity.
    
    OPTIMIZED: Uses local regex-based heuristics instead of an LLM call.
    Saves ~4 seconds per query while catching the same severity mismatches.
    
    CRITICAL: This catches hallucinations where inappropriate sections are cited.
    Example: Citing BNS Section 103 (Murder) for a verbal abuse case.
    """
    import re
    
    span = trace.get_current_span()
    
    query = state["query"]
    answer = state.get("final_answer", state.get("draft_answer", ""))
    classification = state.get("query_classification", None)
    
    # Skip if no classification or no answer
    if not classification or not answer:
        return state
    
    try:
        offense_nature = classification.get("offense_nature", "unknown")
        severity_level = classification.get("severity_level", "unknown")
        
        # Define high-severity sections that should NEVER appear in low-severity cases
        HIGH_SEVERITY_SECTIONS = {
            "103": "Murder",
            "105": "Culpable Homicide", 
            "63": "Rape",
            "64": "Rape-related",
            "65": "Rape-related",
            "66": "Rape-related",
            "310": "Dacoity",
            "311": "Robbery",
        }
        
        # Define which offense types are low-severity
        LOW_SEVERITY_OFFENSES = {"verbal", "dignity", "defamation", "insult", "verbal/dignity"}
        
        problematic_sections = []
        escalation_detected = False
        
        # Only check for escalation if offense is low-severity
        if offense_nature.lower() in LOW_SEVERITY_OFFENSES or severity_level.lower() in ("low", "minor"):
            # Find all BNS section numbers mentioned in the answer
            section_pattern = re.compile(
                r'(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)\s+(?:Section\s+)?(\d+)',
                re.IGNORECASE
            )
            section_pattern2 = re.compile(
                r'Section\s+(\d+)\s+(?:of\s+)?(?:the\s+)?(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)',
                re.IGNORECASE
            )
            
            found_sections = set()
            for m in section_pattern.finditer(answer):
                found_sections.add(m.group(1))
            for m in section_pattern2.finditer(answer):
                found_sections.add(m.group(1))
            
            for sec in found_sections:
                if sec in HIGH_SEVERITY_SECTIONS:
                    problematic_sections.append(f"BNS Section {sec} ({HIGH_SEVERITY_SECTIONS[sec]})")
                    escalation_detected = True
        
        severity_match = not escalation_detected
        
        print(f"\n[SEVERITY VALIDATION (local)]")
        print(f"  Offense: {offense_nature} | Severity: {severity_level}")
        print(f"  Severity Match: {severity_match}")
        print(f"  Escalation Detected: {escalation_detected}")
        print(f"  Problematic Sections: {problematic_sections}")
        
        span.set_attribute("severity_match", severity_match)
        span.set_attribute("escalation_detected", escalation_detected)
        
        if escalation_detected and problematic_sections:
            warning = (
                f"\n\n⚠️ **Note:** This response may contain sections that don't match "
                f"the severity of your query ({offense_nature} offense, "
                f"{severity_level} severity). "
                f"Please verify the cited sections carefully."
            )
            
            logger.warning(
                "Severity escalation detected (local)",
                offense_nature=offense_nature,
                problematic_sections=problematic_sections
            )
            
            return {
                **state,
                "final_answer": answer + warning,
                "severity_validated": False,
                "severity_issues": problematic_sections
            }
        
        logger.info("Severity validation passed (local)")
        
        return {
            **state,
            "severity_validated": True,
            "severity_issues": []
        }
        
    except Exception as e:
        span.set_attribute("error", True)
        logger.error("Severity validation failed", error=str(e))
        return {
            **state,
            "severity_validated": None,
            "severity_issues": []
        }


@tracer.start_as_current_span("node_simplify_output")
async def node_simplify_output(state: GraphState) -> GraphState:
    """
    Simplify the legal language in the answer.
    
    OPTIMIZED: Now a passthrough node. Simplification instructions are built
    into the draft_answer prompt, saving an entire LLM call (~4 seconds).
    Kept for backward compatibility with the graph structure.
    """
    span = trace.get_current_span()
    answer = state.get("final_answer", state.get("draft_answer", ""))
    
    span.set_attribute("passthrough", True)
    span.set_attribute("answer_length", len(answer))
    
    # Ensure final_answer is set even if only draft_answer exists
    if not state.get("final_answer") and state.get("draft_answer"):
        return {
            **state,
            "final_answer": state["draft_answer"]
        }
    
    return state


@tracer.start_as_current_span("node_extract_citations")
async def node_extract_citations(state: GraphState) -> GraphState:
    """
    Extract legal citations from the final answer.
    
    OPTIMIZED: Uses fast regex extraction first. Falls back to LLM only if
    regex finds nothing. This saves ~4 seconds in most cases.
    """
    span = trace.get_current_span()
    answer = state.get("final_answer", "")
    retrieved_docs = state.get("retrieved_docs", [])
    related_cases = state.get("related_cases", [])
    
    try:
        # Fast regex extraction first (no LLM needed)
        citations = extract_citations_regex(answer)
        
        # Only fall back to LLM if regex found nothing
        if not citations:
            citations = await extract_citations(answer)
        
        span.set_attribute("extraction_method", "regex" if citations else "llm_fallback")
        
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
async def node_resolve_citations(state: GraphState) -> GraphState:
    """
    Resolve citations to official government URLs using internet search.
    
    OPTIMIZED: Now async and resolves all citations in parallel via asyncio.gather.
    
    This node searches for official URLs from:
    - Indian Kanoon API (primary)
    - indiacode.nic.in
    - legislative.gov.in
    - egazette.nic.in
    - prsindia.org
    """
    span = trace.get_current_span()
    citations = state.get("citations", [])
    
    if not citations:
        return state
    
    try:
        from app.agents.citation_resolver import resolve_citations
        
        resolved_citations = await resolve_citations(citations)
        
        verified_count = sum(1 for c in resolved_citations if c.get("verified"))
        span.set_attribute("citations_resolved", len(resolved_citations))
        span.set_attribute("citations_verified", verified_count)
        
        logger.info(
            "Citations resolved to URLs (parallel)",
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
        # if state.get("language", "English") == "English":
        #     preamble = f"I interpreted your question as \"{display_query}\".\n\n"
        #     final_answer = preamble + final_answer.lstrip()

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
    if intent == "CONVERSATIONAL":
        return "conversational"
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
