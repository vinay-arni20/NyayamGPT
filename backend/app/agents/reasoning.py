"""
NyayamGPT - Reasoning Module (v2.0)
===================================
Production-grade Gemini API integration with OpenTelemetry tracing.

Architecture follows Google/Anthropic best practices:
- Service layer abstraction
- Retry logic with exponential backoff
- Structured JSON parsing with validation
- Context window optimization
- Comprehensive tracing
"""

import json
import time
import asyncio
from collections import deque
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Type, Union

import google.generativeai as genai
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.services.gemini_client import gemini_client

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Type variable for generic response parsing
T = TypeVar("T", bound=BaseModel)

# Constants
MAX_CONTEXT_CHARS = 15000
MAX_RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY = 0.5


def escape_braces(text: str) -> str:
    """
    Escape curly braces in text to prevent format() errors.
    
    This is critical for preventing injection attacks and format string errors
    when user input contains { or } characters.
    """
    if not text:
        return ""
    return text.replace("{", "{{").replace("}", "}}")


def truncate_context(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """
    Truncate context intelligently to reduce input tokens while preserving key info.
    
    Strategy:
    - Keep 60% from the beginning (usually contains definitions/key info)
    - Keep 40% from the end (usually contains conclusions/penalties)
    - Add a clear truncation marker
    
    Args:
        text: The context text to truncate
        max_chars: Maximum characters to keep
        
    Returns:
        Truncated text with marker if shortened
    """
    if not text or len(text) <= max_chars:
        return text
    
    # Keep first 60% and last 40% of text to preserve intro and conclusion
    first_part = int(max_chars * 0.6)
    last_part = max_chars - first_part
    
    return text[:first_part] + "\n\n[...context truncated for optimization...]\n\n" + text[-last_part:]


def with_retry(max_attempts: int = MAX_RETRY_ATTEMPTS, base_delay: float = RETRY_BASE_DELAY):
    """
    Decorator for retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries (doubles each attempt)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


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
        Includes robust truncated-JSON repair.
        """
        span = trace.get_current_span()
        span.set_attribute("gemini.output_format", "json")
        
        # Add JSON instruction to prompt
        json_instruction = "\n\nRespond with valid JSON only. No markdown, no explanations, just the JSON object. Keep arrays short (max 3 items each)."
        
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
            # Attempt to repair truncated JSON
            repaired = self._repair_truncated_json(response_text)
            if repaired is not None:
                span.set_attribute("gemini.json_repaired", True)
                logger.warning("Repaired truncated JSON response")
                return repaired
            
            span.set_attribute("error", True)
            span.set_attribute("error.type", "json_parse_error")
            logger.error(
                "Failed to parse Gemini JSON response",
                error=str(e),
                response_preview=response_text[:200] if response_text else None
            )
            return {"error": "Failed to parse response", "raw": response_text}
    
    @staticmethod
    def _repair_truncated_json(text: str) -> Optional[dict]:
        """
        Attempt to repair truncated JSON by closing open brackets/braces.
        Handles common cases where Gemini output is cut off mid-response.
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # Try progressively aggressive truncation + closure
        for attempt in range(5):
            try:
                # Count open brackets/braces
                open_braces = text.count('{') - text.count('}')
                open_brackets = text.count('[') - text.count(']')
                
                repaired = text
                
                # If we're inside a string value (odd number of unescaped quotes after last key),
                # try to close the string first
                if repaired.rstrip()[-1:] not in ('}', ']', '"', ',', 'e', 'l', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                    repaired = repaired + '"'
                
                # Remove trailing comma if present
                repaired = repaired.rstrip()
                if repaired.endswith(','):
                    repaired = repaired[:-1]
                
                # Close open brackets then braces
                repaired += ']' * max(0, open_brackets)
                repaired += '}' * max(0, open_braces)
                
                result = json.loads(repaired)
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                # Truncate more aggressively: remove last partial element
                # Find last complete element (last comma before truncation)
                last_comma = text.rfind(',')
                if last_comma > 0:
                    text = text[:last_comma]
                else:
                    break
        
        return None
    
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


@tracer.start_as_current_span("translate_and_classify")
async def translate_and_classify(query: str) -> dict[str, Any]:
    """
    Translate and classify a user query in a SINGLE LLM call.
    
    Combines translate_query + classify_intent into one call for speed.
    
    Args:
        query: User's original query
        
    Returns:
        dict: Combined translation + classification result
    """
    from app.agents.prompts import COMBINED_TRANSLATE_AND_CLASSIFY_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("query", query[:100])
    
    result = await gemini_generate(
        "Detect language, translate to English if needed, and classify the legal query intent.",
        COMBINED_TRANSLATE_AND_CLASSIFY_PROMPT.format(query=escape_braces(query)),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        span.set_attribute("intent", result.get("intent", "unknown"))
        span.set_attribute("confidence", result.get("confidence", 0))
        span.set_attribute("language", result.get("original_language", "unknown"))
    
    return result


@tracer.start_as_current_span("rewrite_and_expand_query")
async def rewrite_and_expand_query(query: str, clarification_context: str = "") -> dict[str, Any]:
    """
    Rewrite and expand a query in a SINGLE LLM call.
    
    Combines rewrite_query + expand_query into one call for speed.
    
    Args:
        query: Original query
        clarification_context: Additional context from clarification
        
    Returns:
        dict: {rewritten_query, expanded_queries}
    """
    from app.agents.prompts import COMBINED_REWRITE_AND_EXPAND_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("query", query[:100])
    
    context = f"Additional context: {clarification_context}" if clarification_context else ""
    
    result = await gemini_generate(
        "Rewrite and expand this legal query for optimal search.",
        COMBINED_REWRITE_AND_EXPAND_PROMPT.format(
            query=escape_braces(query),
            clarification_context=escape_braces(context)
        ),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        span.set_attribute("rewritten_length", len(result.get("rewritten_query", "")))
        span.set_attribute("expanded_count", len(result.get("expanded_queries", [])))
    
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
    
    Uses fast regex extraction first. Falls back to LLM only if
    regex finds nothing (unlikely for well-formatted legal answers).
    
    Args:
        text: Text containing legal citations
        
    Returns:
        list[dict]: Extracted citations
    """
    # Try fast regex extraction first
    citations = extract_citations_regex(text)
    if citations:
        return citations
    
    # Fallback to LLM only if regex found nothing
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


def extract_citations_regex(text: str) -> list[dict[str, Any]]:
    """
    Extract legal citations using regex patterns (no LLM needed).
    
    This is fast and handles the vast majority of citation formats
    produced by our draft answer prompts.
    
    Args:
        text: Text containing legal citations
        
    Returns:
        list[dict]: Extracted citations
    """
    import re
    
    citations = []
    seen = set()
    
    # Act name mappings for normalization
    act_aliases = {
        "bns": "BNS", "bharatiya nyaya sanhita": "BNS",
        "bnss": "BNSS", "bharatiya nagarik suraksha sanhita": "BNSS",
        "bsa": "BSA", "bharatiya sakshya adhiniyam": "BSA",
        "cpc": "CPC", "code of civil procedure": "CPC",
        "hma": "HMA", "hindu marriage act": "HMA",
        "mva": "MVA", "motor vehicles act": "MVA",
        "nia": "NIA", "negotiable instruments act": "NIA",
        "ida": "IDA", "industrial disputes act": "IDA",
        "pocso": "POCSO", "pocso act": "POCSO",
        "it act": "IT Act", "information technology act": "IT Act",
        "ndps": "NDPS", "ndps act": "NDPS",
        "sc/st act": "SC/ST Act", "sc/st": "SC/ST Act",
        "constitution": "Constitution of India",
        "constitution of india": "Constitution of India",
        "ipc": "IPC", "indian penal code": "IPC",
        "crpc": "CrPC", "code of criminal procedure": "CrPC",
    }
    
    # Pattern 1: "Section X of/under ACT" or "Section X ACT"
    pattern1 = re.compile(
        r'[Ss]ection\s+([\d]+(?:\([^)]*\))?(?:\s*[-/]\s*[\d]+(?:\([^)]*\))?)?)\s+'
        r'(?:of\s+|under\s+)?(?:the\s+)?'
        r'(BNS|BNSS|BSA|CPC|HMA|MVA|NIA|IDA|POCSO|IT\s*Act|NDPS|SC/ST\s*(?:\(Prevention of Atrocities\))?\s*Act|'
        r'Constitution(?:\s+of\s+India)?|IPC|CrPC|'
        r'Bharatiya\s+Nyaya\s+Sanhita|Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|'
        r'Bharatiya\s+Sakshya\s+Adhiniyam|Hindu\s+Marriage\s+Act|Motor\s+Vehicles\s+Act|'
        r'Negotiable\s+Instruments\s+Act|Industrial\s+Disputes\s+Act|'
        r'Code\s+of\s+Civil\s+Procedure|Information\s+Technology\s+Act)',
        re.IGNORECASE
    )
    
    # Pattern 2: "ACT Section X" (e.g., "BNS Section 103")
    pattern2 = re.compile(
        r'(BNS|BNSS|BSA|CPC|HMA|MVA|NIA|IDA|POCSO|IT\s*Act|NDPS|SC/ST\s*Act|IPC|CrPC)\s+'
        r'[Ss]ection\s+([\d]+(?:\([^)]*\))?(?:\s*[-/]\s*[\d]+(?:\([^)]*\))?)?)',
        re.IGNORECASE
    )
    
    # Pattern 3: "Sec X ACT" or "Sec. X ACT" (abbreviated)
    pattern3 = re.compile(
        r'[Ss]ec\.?\s+([\d]+(?:\([^)]*\))?)\s+'
        r'(?:of\s+|under\s+)?(?:the\s+)?'
        r'(BNS|BNSS|BSA|CPC|HMA|MVA|NIA|IDA|POCSO|IT\s*Act|NDPS|SC/ST\s*Act|IPC|CrPC)',
        re.IGNORECASE
    )
    
    # Pattern 4: "Article X" (Constitution)
    pattern4 = re.compile(
        r'[Aa]rticle\s+([\d]+[A-Za-z]?(?:\([^)]*\))?)\s*'
        r'(?:of\s+)?(?:the\s+)?(?:Constitution(?:\s+of\s+India)?)?',
        re.IGNORECASE
    )
    
    for match in pattern1.finditer(text):
        section, act = match.group(1).strip(), match.group(2).strip()
        act_normalized = act_aliases.get(act.lower(), act.upper())
        key = f"{act_normalized}:{section}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "type": "section", "law": act_normalized,
                "section": section, "title": "", "context": ""
            })
    
    for match in pattern2.finditer(text):
        act, section = match.group(1).strip(), match.group(2).strip()
        act_normalized = act_aliases.get(act.lower(), act.upper())
        key = f"{act_normalized}:{section}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "type": "section", "law": act_normalized,
                "section": section, "title": "", "context": ""
            })
    
    for match in pattern3.finditer(text):
        section, act = match.group(1).strip(), match.group(2).strip()
        act_normalized = act_aliases.get(act.lower(), act.upper())
        key = f"{act_normalized}:{section}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "type": "section", "law": act_normalized,
                "section": section, "title": "", "context": ""
            })
    
    for match in pattern4.finditer(text):
        article = match.group(1).strip()
        key = f"Constitution:{article}"
        if key not in seen:
            seen.add(key)
            citations.append({
                "type": "article", "law": "Constitution of India",
                "article": article, "section": article, "title": "", "context": ""
            })
    
    return citations


@tracer.start_as_current_span("generate_constrained_answer")
async def generate_constrained_answer(
    query: str, 
    context: str, 
    classification: dict,
    language: str = "English", 
    chat_history: list[dict[str, str]] = None
) -> str:
    """
    Generate a CONSTRAINED legal answer using pre-computed classification.
    
    This function uses the CONSTRAINED_RAG_ANSWER_PROMPT which:
    1. Includes pre-computed offense classification
    2. Enforces strict section matching rules
    3. Prevents severity/type mismatches (e.g., citing murder for insults)
    
    Args:
        query: User's query
        context: Retrieved legal documents (already filtered)
        classification: Pre-computed query classification dict
        language: Target language for the response
        chat_history: Previous conversation history
        
    Returns:
        str: Constrained draft answer
    """
    from app.agents.prompts import CONSTRAINED_RAG_ANSWER_PROMPT, SYSTEM_PROMPT
    
    span = trace.get_current_span()
    span.set_attribute("context_length", len(context))
    span.set_attribute("language", language)
    span.set_attribute("offense_nature", classification.get("offense_nature", "unknown"))
    
    # Truncate context to reduce input tokens
    context = truncate_context(context, max_chars=15000)
    span.set_attribute("truncated_context_length", len(context))
    
    # Format chat history (only last 3 messages)
    history_text = ""
    if chat_history:
        history_text = "\n\nChat History:\n" + "\n".join(
            [f"{msg['role'].title()}: {msg['content']}" for msg in chat_history[-3:]]
        )
    
    # Extract classification fields
    offense_nature = classification.get("offense_nature", "unknown")
    severity_level = classification.get("severity_level", "unknown")
    involves_caste = classification.get("involves_caste", False)
    involves_physical = classification.get("involves_physical", False) or classification.get("involves_death", False)
    involves_minor = classification.get("involves_minor", False)
    
    logger.info(
        "Generating constrained answer",
        offense_nature=offense_nature,
        severity=severity_level,
        involves_caste=involves_caste
    )
    
    return await gemini_generate(
        SYSTEM_PROMPT,
        CONSTRAINED_RAG_ANSWER_PROMPT.format(
            query=escape_braces(query),
            context=escape_braces(context + history_text),
            language=escape_braces(language),
            offense_nature=escape_braces(offense_nature),
            severity_level=escape_braces(severity_level),
            involves_caste="Yes" if involves_caste else "No",
            involves_physical="Yes" if involves_physical else "No",
            involves_minor="Yes" if involves_minor else "No",
        ),
        use_cache=True
    )


@tracer.start_as_current_span("validate_severity_match")
async def validate_severity_match(
    query: str,
    response: str,
    classification: dict
) -> dict[str, Any]:
    """
    Validate that the response severity matches the classified offense severity.
    
    This catches hallucinations where the LLM cites inappropriate sections
    (e.g., murder sections for verbal abuse cases).
    
    Args:
        query: Original user query
        response: Generated response to validate
        classification: Pre-computed query classification
        
    Returns:
        dict: Validation result with severity_match, escalation_detected, etc.
    """
    from app.agents.prompts import OFFENSE_SEVERITY_VALIDATION_PROMPT
    
    span = trace.get_current_span()
    
    offense_nature = classification.get("offense_nature", "unknown")
    severity_level = classification.get("severity_level", "unknown")
    
    result = await gemini_generate(
        "Validate response severity matches offense classification.",
        OFFENSE_SEVERITY_VALIDATION_PROMPT.format(
            query=escape_braces(query),
            response=escape_braces(response),
            offense_nature=escape_braces(offense_nature),
            severity_level=escape_braces(severity_level)
        ),
        json_output=True,
        use_cache=True
    )
    
    if isinstance(result, dict):
        span.set_attribute("severity_match", result.get("severity_match", False))
        span.set_attribute("escalation_detected", result.get("escalation_detected", False))
    
    return result
