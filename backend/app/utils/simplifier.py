"""
NyayamGPT - Simplifier Utility
==============================
Text simplification utilities for making legal language accessible.
"""

import re
from typing import Optional

from app.core.logging import logger


# Legal term replacements for plain language
LEGAL_TERM_REPLACEMENTS = {
    "hereinafter": "from now on",
    "herein": "in this document",
    "hereof": "of this",
    "thereof": "of that",
    "whereby": "by which",
    "whereas": "while/since",
    "aforesaid": "mentioned earlier",
    "forthwith": "immediately",
    "notwithstanding": "despite/regardless of",
    "cognizable": "serious (police can arrest without warrant)",
    "non-cognizable": "less serious (needs court warrant for arrest)",
    "bailable": "can be released on bail",
    "non-bailable": "bail is not a right (judge decides)",
    "compoundable": "can be settled between parties",
    "non-compoundable": "cannot be privately settled",
    "suo motu": "on its own/by itself",
    "prima facie": "at first look/on the face of it",
    "locus standi": "right to bring a case",
    "mala fide": "in bad faith",
    "bona fide": "in good faith/genuine",
    "inter alia": "among other things",
    "mutatis mutandis": "with necessary changes",
    "ipso facto": "by that very fact",
    "ab initio": "from the beginning",
    "ad hoc": "for this specific purpose",
    "de facto": "in practice/actually",
    "de jure": "by law/legally",
    "ex parte": "one-sided/without other party",
    "in camera": "in private/closed court",
    "mandamus": "court order to do something",
    "habeas corpus": "produce the person in court",
    "certiorari": "order to review a decision",
    "injunction": "court order to stop/do something",
    "plaintiff": "person who files the case",
    "defendant": "person against whom case is filed",
    "appellant": "person who appeals",
    "respondent": "person responding to appeal",
    "petitioner": "person who files petition",
    "prosecution": "government/state bringing charges",
    "accused": "person charged with crime",
    "complainant": "person who files complaint",
    "abetment": "helping/encouraging a crime",
    "culpable homicide": "causing death with intention or knowledge",
    "grievous hurt": "serious bodily injury",
    "mens rea": "guilty mind/criminal intent",
    "actus reus": "guilty act/criminal action",
}


def simplify_legal_terms(text: str) -> str:
    """
    Replace complex legal terms with simpler explanations.
    
    Args:
        text: Text containing legal terminology
        
    Returns:
        str: Text with simplified terms
    """
    result = text
    
    for term, replacement in LEGAL_TERM_REPLACEMENTS.items():
        # Case-insensitive replacement with word boundaries
        pattern = rf"\b{re.escape(term)}\b"
        result = re.sub(
            pattern,
            f"{term} ({replacement})",
            result,
            flags=re.IGNORECASE,
            count=1  # Only replace first occurrence
        )
    
    return result


def add_section_context(text: str) -> str:
    """
    Add contextual information to section references.
    
    Args:
        text: Text with legal section references
        
    Returns:
        str: Text with added context
    """
    # Common section patterns
    section_patterns = [
        (r"Section\s+(\d+)\s+of\s+(IPC|Indian Penal Code)", 
         r"Section \1 of the \2 (criminal offences)"),
        (r"Section\s+(\d+)\s+of\s+(CrPC|Code of Criminal Procedure)",
         r"Section \1 of the \2 (criminal procedures)"),
        (r"Section\s+(\d+)\s+of\s+(CPC|Code of Civil Procedure)",
         r"Section \1 of the \2 (civil procedures)"),
        (r"Article\s+(\d+)\s+of\s+the\s+Constitution",
         r"Article \1 of the Constitution of India"),
    ]
    
    result = text
    for pattern, replacement in section_patterns:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def format_for_readability(text: str) -> str:
    """
    Format text for better readability.
    
    Args:
        text: Raw text
        
    Returns:
        str: Formatted text
    """
    # Add line breaks after periods if followed by caps
    text = re.sub(r'\.(\s+)([A-Z])', r'.\n\n\2', text)
    
    # Format numbered lists
    text = re.sub(r'(\d+)\)', r'\n\1)', text)
    
    # Format lettered lists
    text = re.sub(r'\(([a-z])\)', r'\n(\1)', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


def calculate_reading_level(text: str) -> dict:
    """
    Calculate approximate reading level metrics.
    
    Args:
        text: Text to analyze
        
    Returns:
        dict: Reading level metrics
    """
    # Count sentences
    sentences = len(re.findall(r'[.!?]+', text)) or 1
    
    # Count words
    words = len(text.split())
    
    # Count syllables (approximate)
    syllables = sum(
        max(1, len(re.findall(r'[aeiouy]+', word.lower())))
        for word in text.split()
    )
    
    # Flesch Reading Ease
    if words > 0 and sentences > 0:
        flesch = 206.835 - (1.015 * words / sentences) - (84.6 * syllables / words)
    else:
        flesch = 0
    
    # Determine level
    if flesch >= 80:
        level = "Easy"
    elif flesch >= 60:
        level = "Standard"
    elif flesch >= 40:
        level = "Difficult"
    else:
        level = "Very Difficult"
    
    return {
        "flesch_score": round(flesch, 1),
        "level": level,
        "word_count": words,
        "sentence_count": sentences,
        "avg_words_per_sentence": round(words / sentences, 1)
    }


def simplify_text(
    text: str,
    replace_terms: bool = True,
    add_context: bool = True,
    format_output: bool = True
) -> str:
    """
    Apply all simplification transformations.
    
    Args:
        text: Text to simplify
        replace_terms: Replace legal terms
        add_context: Add section context
        format_output: Format for readability
        
    Returns:
        str: Simplified text
    """
    result = text
    
    if replace_terms:
        result = simplify_legal_terms(result)
    
    if add_context:
        result = add_section_context(result)
    
    if format_output:
        result = format_for_readability(result)
    
    return result
