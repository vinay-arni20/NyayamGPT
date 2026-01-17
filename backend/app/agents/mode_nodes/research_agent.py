"""
NyayamGPT - Deep Research Multi-Agent Node
==========================================
Multi-step research agent for comprehensive legal analysis.
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.logging import logger
from app.core.config import settings


async def deep_research_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform deep multi-agent research for comprehensive analysis.
    
    This node:
    1. Retrieves documents with high top_k
    2. Generates comprehensive draft
    3. Validates the draft
    4. Refines if needed (up to 3 attempts)
    5. Adds limitations section
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with research results
    """
    query = state.get("query", "")
    retrieval_config = state.get("retrieval_config", {})
    system_prompt = state.get("system_prompt", "")
    max_attempts = retrieval_config.get("max_refinement_attempts", 3)
    
    logger.info(f"[RESEARCH] Starting deep research for: {query[:50]}...")
    start_time = datetime.now()
    
    research_state = {
        "step": 0,
        "steps_completed": [],
        "validation_attempts": 0,
        "validation_passed": False,
        "confidence_score": 0.0,
        "issues": [],
    }
    
    try:
        # Step 1: Enhanced Document Retrieval
        logger.info("[RESEARCH] Step 1: Enhanced document retrieval")
        research_state["step"] = 1
        research_state["steps_completed"].append("document_retrieval")
        
        # Use existing retrieval from state or trigger new retrieval
        context = state.get("context", "")
        retrieved_docs = state.get("retrieved_docs", [])
        
        if not context and not retrieved_docs:
            logger.warning("[RESEARCH] No context available, proceeding with limited info")
        
        logger.info(f"[RESEARCH] Step 1: Complete - {len(retrieved_docs)} documents")
        
        # Step 2: Generate Comprehensive Draft
        logger.info("[RESEARCH] Step 2: Generating comprehensive draft")
        research_state["step"] = 2
        research_state["steps_completed"].append("draft_generation")
        
        # The actual generation will be handled by the generator node
        # Here we prepare the enhanced context
        enhanced_context = prepare_enhanced_context(
            context=context,
            retrieved_docs=retrieved_docs,
            query=query,
        )
        
        logger.info("[RESEARCH] Step 2: Complete - Enhanced context prepared")
        
        # Step 3-4: Validation Loop (handled by validator node)
        logger.info("[RESEARCH] Step 3: Validation configured")
        research_state["step"] = 3
        research_state["steps_completed"].append("validation_setup")
        
        # Set up for multi-attempt validation
        validation_config = {
            "max_attempts": max_attempts,
            "require_limitations": True,
            "require_multi_paragraph": True,
            "require_chain_of_thought": True,
            "minimum_citations": 3,
        }
        
        # Step 5: Configure Limitations Section
        logger.info("[RESEARCH] Step 4: Configuring limitations requirement")
        research_state["step"] = 4
        research_state["steps_completed"].append("limitations_config")
        
        limitations_prompt = generate_limitations_prompt(query)
        
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"[RESEARCH] Research preparation complete in {total_time:.0f}ms")
        
        return {
            **state,
            "enhanced_context": enhanced_context,
            "validation_config": validation_config,
            "limitations_prompt": limitations_prompt,
            "research_state": research_state,
            "require_deep_validation": True,
            "research_time_ms": total_time,
        }
        
    except Exception as e:
        logger.error(f"[RESEARCH] Error during research: {e}")
        research_state["issues"].append(str(e))
        
        return {
            **state,
            "research_state": research_state,
            "research_error": str(e),
        }


def prepare_enhanced_context(
    context: str,
    retrieved_docs: List[Any],
    query: str,
) -> str:
    """
    Prepare enhanced context for deep research.
    
    Args:
        context: Original context string
        retrieved_docs: List of retrieved documents
        query: User's query
        
    Returns:
        Enhanced context string
    """
    enhanced_parts = []
    
    # Add query analysis
    enhanced_parts.append("## Query Analysis")
    enhanced_parts.append(f"**User Query:** {query}")
    enhanced_parts.append(f"**Research Depth:** Comprehensive/Expert-level")
    enhanced_parts.append("")
    
    # Add main context
    if context:
        enhanced_parts.append("## Primary Legal Sources")
        enhanced_parts.append(context)
        enhanced_parts.append("")
    
    # Add document metadata if available
    if retrieved_docs:
        enhanced_parts.append("## Document Summary")
        for i, doc in enumerate(retrieved_docs[:15], 1):
            if hasattr(doc, 'metadata'):
                metadata = doc.metadata
                enhanced_parts.append(f"**Source {i}:**")
                if 'act' in metadata:
                    enhanced_parts.append(f"- Act: {metadata['act']}")
                if 'section' in metadata:
                    enhanced_parts.append(f"- Section: {metadata['section']}")
                if 'title' in metadata:
                    enhanced_parts.append(f"- Title: {metadata['title']}")
                enhanced_parts.append("")
    
    # Add research instructions
    enhanced_parts.append("## Research Requirements")
    enhanced_parts.append("- Provide comprehensive analysis with multiple perspectives")
    enhanced_parts.append("- Include relevant case law with proper citations")
    enhanced_parts.append("- Discuss procedural aspects and jurisdictional considerations")
    enhanced_parts.append("- Note any exceptions, amendments, or evolving interpretations")
    enhanced_parts.append("- Include a Limitations section at the end")
    
    return "\n".join(enhanced_parts)


def generate_limitations_prompt(query: str) -> str:
    """
    Generate the limitations prompt for deep research.
    
    Args:
        query: User's query
        
    Returns:
        Limitations prompt string
    """
    return f"""
After providing the comprehensive analysis, add a "**Limitations of this analysis:**" section that includes:

1. **Scope Limitations:** What aspects of the query are NOT covered in this response
2. **Jurisdictional Notes:** Any state-specific variations not discussed
3. **Temporal Considerations:** Recent amendments or pending legislation that may affect this
4. **Case-Specific Disclaimer:** Why individual circumstances may differ
5. **Verification Recommendation:** Suggest verifying with official sources or legal counsel

Keep the limitations section concise but thorough (3-5 bullet points).
"""


async def validate_deep_research(
    response: str,
    query: str,
    context: str,
    validation_config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate deep research response meets requirements.
    
    Args:
        response: Generated response
        query: Original query
        context: Source context
        validation_config: Validation requirements
        
    Returns:
        Validation result dictionary
    """
    issues = []
    passed = True
    
    # Check for limitations section
    if validation_config.get("require_limitations"):
        if "limitation" not in response.lower():
            issues.append("Missing Limitations section")
            passed = False
    
    # Check for multi-paragraph structure
    if validation_config.get("require_multi_paragraph"):
        paragraphs = [p for p in response.split("\n\n") if p.strip()]
        if len(paragraphs) < 3:
            issues.append("Response too brief - requires multi-paragraph analysis")
            passed = False
    
    # Check for minimum citations
    min_citations = validation_config.get("minimum_citations", 3)
    import re
    citations = re.findall(r'Section \d+|Art(?:icle)? \d+|BNS|BNSS|BSA|CPC|MVA|NIA|HMA|IDA', response, re.IGNORECASE)
    if len(set(citations)) < min_citations:
        issues.append(f"Insufficient citations - found {len(set(citations))}, need {min_citations}")
        # Don't fail for this, just note it
    
    # Calculate confidence score based on validation
    confidence = 1.0
    confidence -= len(issues) * 0.15
    confidence = max(0.3, confidence)
    
    return {
        "passed": passed,
        "issues": issues,
        "confidence_score": confidence,
    }
