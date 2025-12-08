"""
NyayamGPT - Reasoning Module
============================
Gemini API integration for LLM-powered reasoning with OpenTelemetry tracing.
"""

import json
import time
import asyncio
from collections import deque
from typing import Any, Optional, TypeVar, Type

import google.generativeai as genai
from opentelemetry import trace
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger
from app.services.gemini_client import gemini_client

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Type variable for generic response parsing
T = TypeVar("T", bound=BaseModel)


def escape_braces(text: str) -> str:
    """Escape curly braces in text to prevent format() errors."""
    if not text:
        return ""
    return text.replace("{", "{{").replace("}", "}}")


def truncate_context(text: str, max_chars: int = 15000) -> str:
    """Truncate context intelligently to reduce input tokens while keeping key info."""
    if not text or len(text) <= max_chars:
        return text
    
    # Keep first 60% and last 40% of text to preserve intro and conclusion
    first_part = int(max_chars * 0.6)
    last_part = max_chars - first_part
    
    return text[:first_part] + "\n\n[...context truncated for optimization...]\n\n" + text[-last_part:]


class GeminiService:
    """
    Service for interacting with Google Gemini API.
    
    Provides methods for generating text responses and structured JSON outputs
    with OpenTelemetry tracing for observability and aggressive caching.
    """
    
    _instance: Optional["GeminiService"] = None
    
    def __new__(cls) -> "GeminiService":
        """Singleton pattern for Gemini service."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        """Initialize Gemini API client."""
        if self._initialized:
            return
        
        self.client = gemini_client
        self._initialized = True
        logger.info("GeminiService initialized using robust GeminiClient")
    
    @tracer.start_as_current_span("gemini_generate")
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> str:
        """
        Generate a text response from Gemini with caching.
        """
        span = trace.get_current_span()
        span.set_attribute("gemini.model", settings.gemini_model)
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        try:
            # Use the robust client
            result = await self.client.generate_content(full_prompt, use_cache=use_cache)
            
            span.set_attribute("gemini.response_length", len(result))
            return result
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            logger.error(f"Gemini generation failed: {e}")
            raise

    @tracer.start_as_current_span("gemini_generate_json")
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Optional[dict] = None,
        use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Generate a JSON response from Gemini with caching.
        """
        span = trace.get_current_span()
        span.set_attribute("gemini.output_format", "json")
        
        # Add JSON instruction to prompt
        json_instruction = "\n\nRespond with valid JSON only. No markdown, no explanations, just the JSON object."
        
        try:
            response_text = await self.generate(
                system_prompt + json_instruction,
                user_prompt,
                use_cache=use_cache
            )
            
            # Clean response (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            result = json.loads(response_text)
            span.set_attribute("gemini.json_keys", list(result.keys()) if isinstance(result, dict) else "array")
            
            return result
            
        except json.JSONDecodeError as e:
            span.set_attribute("error", True)
            span.set_attribute("error.type", "json_parse_error")
            logger.error(
                "Failed to parse Gemini JSON response",
                error=str(e),
                response_preview=response_text[:200] if response_text else None
            )
            return {"error": "Failed to parse response", "raw": response_text}
    
    @tracer.start_as_current_span("gemini_generate_structured")
    async def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        use_cache: bool = True
    ) -> T:
        """
        Generate a structured response validated against a Pydantic model.
        """
        span = trace.get_current_span()
        span.set_attribute("gemini.response_model", response_model.__name__)
        
        # Generate schema hint from model
        schema_hint = f"\n\nResponse must match this schema:\n{response_model.model_json_schema()}"
        
        json_response = await self.generate_json(
            system_prompt + schema_hint,
            user_prompt,
            use_cache=use_cache
        )
        
        # Validate and parse
        result = response_model.model_validate(json_response)
        return result


# Singleton instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """
    Get the Gemini service singleton.
    
    Returns:
        GeminiService: Gemini service instance
    """
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service


# =============================================================================
# Convenience Functions with Tracing
# =============================================================================

@tracer.start_as_current_span("gemini_generate_wrapper")
async def gemini_generate(
    system_prompt: str,
    user_prompt: str,
    json_output: bool = False,
    use_cache: bool = True
) -> str | dict[str, Any]:
    """
    Generate a response from Gemini with caching.
    
    Args:
        system_prompt: System instructions
        user_prompt: User's input
        json_output: Whether to parse response as JSON
        use_cache: Whether to use cache (default: True)
        
    Returns:
        str | dict: Generated response (text or parsed JSON)
    """
    service = get_gemini_service()
    
    if json_output:
        return await service.generate_json(system_prompt, user_prompt, use_cache=use_cache)
    else:
        return await service.generate(system_prompt, user_prompt, use_cache=use_cache)


@tracer.start_as_current_span("classify_intent")
async def classify_intent(query: str) -> dict[str, Any]:
    """
    Classify the intent of a user query with caching.
    
    Args:
        query: User's query
        
    Returns:
        dict: Intent classification result
    """
    from app.agents.prompts import INTENT_CLASSIFIER_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("query", query[:100])
    
    result = await gemini_generate(
        "Classify the intent of this legal query.",
        INTENT_CLASSIFIER_PROMPT.format(query=escape_braces(query)),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        span.set_attribute("intent", result.get("intent", "unknown"))
        span.set_attribute("confidence", result.get("confidence", 0))
    
    return result


@tracer.start_as_current_span("expand_query")
async def expand_query(query: str) -> list[str]:
    """
    Generate expanded search queries for better retrieval with caching.
    
    Args:
        query: Original user query
        
    Returns:
        list[str]: List of expanded queries
    """
    from app.agents.prompts import QUERY_EXPANSION_PROMPT
    
    result = await gemini_generate(
        "Generate search queries.",
        QUERY_EXPANSION_PROMPT.format(query=escape_braces(query)),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        queries = result.get("expanded_queries", [])
        if query not in queries:
            queries.insert(0, query)
        return queries[:5]
    
    return [query]


@tracer.start_as_current_span("generate_legal_draft")
async def generate_legal_draft(query: str, context: str) -> str:
    """
    Generate a legal document draft with caching.
    
    Args:
        query: User's drafting request
        context: Any relevant context or details provided
        
    Returns:
        str: Drafted legal document
    """
    from app.agents.prompts import DRAFTING_PROMPT
    
    prompt = f"""
    USER REQUEST: {query}
    
    CONTEXT/DETAILS:
    {context}
    
    Draft the document now.
    """
    
    return await gemini_generate(
        DRAFTING_PROMPT,
        prompt,
        json_output=False,
        use_cache=False  # Don't cache drafts, they should be unique
    )


@tracer.start_as_current_span("generate_clarification")
async def generate_clarification(query: str) -> str:
    """
    Generate a clarifying question for an unclear query with caching.
    
    Args:
        query: User's unclear query
        
    Returns:
        str: Clarifying question
    """
    from app.agents.prompts import CLARIFIER_PROMPT
    
    return await gemini_generate(
        "Ask a natural clarifying question to understand the user's legal query better.",
        CLARIFIER_PROMPT.format(query=escape_braces(query)),
        use_cache=True
    )


@tracer.start_as_current_span("translate_query")
async def translate_query(query: str) -> dict[str, str]:
    """
    Translate a user query to English if needed with caching.
    
    Args:
        query: User's original query
        
    Returns:
        dict: {original_language, translated_query}
    """
    from app.agents.prompts import QUERY_TRANSLATOR_PROMPT
    
    return await gemini_generate(
        "Detect language and translate to English if needed.",
        QUERY_TRANSLATOR_PROMPT.format(query=escape_braces(query)),
        json_output=True,
        use_cache=True
    )


@tracer.start_as_current_span("rewrite_query")
async def rewrite_query(query: str, clarification_context: str = "") -> str:
    """
    Rewrite a query for optimal legal document search with caching.
    
    Args:
        query: Original query
        clarification_context: Additional context from clarification
        
    Returns:
        str: Rewritten query
    """
    from app.agents.prompts import QUERY_REWRITER_PROMPT
    
    context = f"Additional context: {clarification_context}" if clarification_context else ""
    
    return await gemini_generate(
        "Rewrite queries for optimal legal document search.",
        QUERY_REWRITER_PROMPT.format(
            query=escape_braces(query), 
            clarification_context=escape_braces(context)
        ),
        use_cache=True
    )


@tracer.start_as_current_span("generate_draft_answer")
async def generate_draft_answer(query: str, context: str, language: str = "English", chat_history: list[dict[str, str]] = None) -> str:
    """
    Generate a draft legal answer based on retrieved context with caching.
    
    Args:
        query: User's query
        context: Retrieved legal documents as text
        language: Target language for the response
        chat_history: Previous conversation history
        
    Returns:
        str: Draft answer
    """
    from app.agents.prompts import DRAFT_ANSWER_PROMPT, SYSTEM_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("context_length", len(context))
    span.set_attribute("language", language)
    
    # Truncate context to reduce input tokens (keeps first 60% + last 40%)
    context = truncate_context(context, max_chars=15000)
    span.set_attribute("truncated_context_length", len(context))
    
    # Format chat history (only last 3 messages to reduce tokens)
    history_text = ""
    if chat_history:
        history_text = "\n\nChat History:\n" + "\n".join(
            [f"{msg['role'].title()}: {msg['content']}" for msg in chat_history[-3:]]
        )
    
    return await gemini_generate(
        SYSTEM_PROMPT,
        DRAFT_ANSWER_PROMPT.format(
            query=escape_braces(query),
            context=escape_braces(context),
            language=escape_braces(language),
            chat_history=escape_braces(history_text)
        ),
        use_cache=True
    )


@tracer.start_as_current_span("validate_answer")
async def validate_answer(query: str, context: str, draft_answer: str) -> dict[str, Any]:
    """
    Validate a draft answer for accuracy and faithfulness with caching.
    
    Args:
        query: User's query
        context: Retrieved legal documents
        draft_answer: Draft answer to validate
        
    Returns:
        dict: Validation result with is_valid, problems, fixes
    """
    from app.agents.prompts import VALIDATOR_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("draft_length", len(draft_answer))
    
    # Truncate context to reduce input tokens
    context = truncate_context(context, max_chars=12000)
    
    result = await gemini_generate(
        "Validate this legal answer for accuracy, citations, and conversational tone.",
        VALIDATOR_PROMPT.format(
            query=escape_braces(query),
            context=escape_braces(context),
            draft_answer=escape_braces(draft_answer)
        ),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        span.set_attribute("is_valid", result.get("is_valid", False))
        span.set_attribute("faithfulness_score", result.get("faithfulness_score", 0))
    
    return result


@tracer.start_as_current_span("refine_answer")
async def refine_answer(
    query: str,
    context: str,
    draft_answer: str,
    issues: list[str],
    fixes: list[str]
) -> str:
    """
    Refine an answer based on validation feedback.
    
    Args:
        query: User's query
        context: Retrieved legal documents
        draft_answer: Previous draft
        issues: List of identified issues
        fixes: List of required fixes
        
    Returns:
        str: Refined answer
    """
    from app.agents.prompts import REFINER_PROMPT
    
    # Truncate context to reduce input tokens
    context = truncate_context(context, max_chars=12000)
    
    return await gemini_generate(
        "Refine this legal answer to fix issues while keeping it natural and conversational.",
        REFINER_PROMPT.format(
            query=escape_braces(query),
            context=escape_braces(context),
            draft_answer=escape_braces(draft_answer),
            issues=escape_braces("\n".join(f"- {i}" for i in issues)),
            fixes=escape_braces("\n".join(f"- {f}" for f in fixes))
        ),
        use_cache=True
    )


@tracer.start_as_current_span("simplify_answer")
async def simplify_answer(answer: str) -> str:
    """
    Simplify legal language in an answer.
    
    Args:
        answer: Answer with legal terminology
        
    Returns:
        str: Simplified answer
    """
    from app.agents.prompts import SIMPLIFIER_PROMPT
    
    return await gemini_generate(
        "Polish this response for clarity while keeping it natural and professional.",
        SIMPLIFIER_PROMPT.format(answer=escape_braces(answer)),
        use_cache=True
    )


@tracer.start_as_current_span("extract_citations")
async def extract_citations(text: str) -> list[dict[str, Any]]:
    """
    Extract legal citations from text.
    
    Args:
        text: Text containing legal citations
        
    Returns:
        list[dict]: Extracted citations
    """
    from app.agents.prompts import CITATION_EXTRACTOR_PROMPT
    
    result = await gemini_generate(
        "Extract legal citations from text.",
        CITATION_EXTRACTOR_PROMPT.format(text=escape_braces(text)),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, list):
        return result
    elif isinstance(result, dict) and "citations" in result:
        return result["citations"]
    else:
        return []
