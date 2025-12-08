"""
NyayamGPT - Mode Router Node
============================
Routes queries to appropriate processing paths based on mode.
"""

from typing import Any, Dict, Literal
from app.core.logging import logger
from app.agents.prompts import MODE_SYSTEM_PROMPTS

# Mode type
ModeType = Literal["normal", "lawyer", "qa", "web", "deep"]

# Retrieval configurations per mode
# Unified configuration for "Perplexity-like" behavior across all modes
UNIFIED_CONFIG = {
    "top_k": 10,
    "score_threshold": 0.65,
    "enable_web": True,
    "max_tokens": 2048,
    "temperature": 0.1,
}

RETRIEVAL_CONFIGS: Dict[ModeType, Dict[str, Any]] = {
    "normal": UNIFIED_CONFIG,
    "lawyer": UNIFIED_CONFIG,
    "qa": UNIFIED_CONFIG,
    "web": UNIFIED_CONFIG,
    "deep": UNIFIED_CONFIG,
}


async def mode_router_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route the query to appropriate processing path based on mode.
    
    Args:
        state: Current graph state containing:
            - query: User's legal question
            - mode: Selected mode (normal, lawyer, qa, web, deep)
            - language: Response language
            
    Returns:
        Updated state with:
            - retrieval_config: Configuration for retrieval
            - system_prompt: Mode-specific system prompt
            - next_node: Next node to route to
    """
    mode: ModeType = state.get("mode", "normal")
    language = state.get("language", "en")
    query = state.get("query", "")
    
    logger.info(f"[ROUTER] Mode: {mode}, Query length: {len(query)}")
    
    # Get mode configuration
    retrieval_config = RETRIEVAL_CONFIGS.get(mode, RETRIEVAL_CONFIGS["normal"])
    
    # Get mode-specific system prompt
    system_prompt_template = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["normal"])
    system_prompt = system_prompt_template.format(language=language)
    
    # Determine next node based on mode
    if mode == "web":
        next_node = "web_search"
        logger.info("[ROUTER] Routing to web_search node")
    elif mode == "deep":
        next_node = "deep_research"
        logger.info("[ROUTER] Routing to deep_research node")
    else:
        next_node = "standard_retrieval"
        logger.info(f"[ROUTER] Routing to standard_retrieval node")
    
    # Log configuration
    logger.info(f"[ROUTER] Config: top_k={retrieval_config['top_k']}, "
                f"threshold={retrieval_config['score_threshold']}, "
                f"web_enabled={retrieval_config.get('enable_web', False)}")
    
    return {
        **state,
        "retrieval_config": retrieval_config,
        "system_prompt": system_prompt,
        "next_node": next_node,
        "mode": mode,
    }


def get_retrieval_config(mode: ModeType) -> Dict[str, Any]:
    """
    Get retrieval configuration for a specific mode.
    
    Args:
        mode: The processing mode
        
    Returns:
        Retrieval configuration dictionary
    """
    return RETRIEVAL_CONFIGS.get(mode, RETRIEVAL_CONFIGS["normal"])


def get_system_prompt(mode: ModeType, language: str = "en") -> str:
    """
    Get the system prompt for a specific mode.
    
    Args:
        mode: The processing mode
        language: Response language
        
    Returns:
        Formatted system prompt
    """
    template = MODE_SYSTEM_PROMPTS.get(mode, MODE_SYSTEM_PROMPTS["normal"])
    return template.format(language=language)
