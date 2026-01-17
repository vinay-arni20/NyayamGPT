"""
NyayamGPT - Validator Agent Module
==================================
Validation logic for ensuring answer quality and preventing hallucinations.
Supports mode-aware validation with different requirements per mode.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional

from opentelemetry import trace
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import logger
from app.agents.reasoning import validate_answer, refine_answer

# Get tracer for this module
tracer = trace.get_tracer(__name__)

# Mode type alias
ModeType = Literal["normal", "lawyer", "qa", "web", "deep"]

# Mode-specific validation requirements
MODE_VALIDATION_CONFIG: Dict[ModeType, Dict[str, Any]] = {
    "normal": {
        "min_citations": 1,
        "require_disclaimer": True,
        "min_paragraphs": 1,
        "require_chain_of_thought": False,
        "require_limitations": False,
        "require_web_sources": False,
        "strictness": 0.8,  # Increased strictness for Perplexity style
        "disallow_section_headings": True,
        "disallow_meta_commentary": True,
    },
    "lawyer": {
        "min_citations": 3,
        "require_disclaimer": True,
        "min_paragraphs": 2,
        "require_chain_of_thought": True,
        "require_limitations": False,
        "require_web_sources": False,
        "strictness": 0.8,  # Higher threshold
        "disallow_section_headings": True,
        "disallow_meta_commentary": True,
    },
    "qa": {
        "min_citations": 1,
        "require_disclaimer": False,
        "min_paragraphs": 1,
        "require_chain_of_thought": False,
        "require_limitations": False,
        "require_web_sources": False,
        "strictness": 0.5,  # Quick answers, lower bar
        "disallow_section_headings": True,
        "disallow_meta_commentary": True,
    },
    "web": {
        "min_citations": 1,
        "require_disclaimer": True,
        "min_paragraphs": 2,
        "require_chain_of_thought": False,
        "require_limitations": False,
        "require_web_sources": True,
        "strictness": 0.7,
        "disallow_section_headings": True,
        "disallow_meta_commentary": True,
    },
    "deep": {
        "min_citations": 5,
        "require_disclaimer": True,
        "min_paragraphs": 4,
        "require_chain_of_thought": True,
        "require_limitations": True,
        "require_web_sources": False,
        "strictness": 0.9,  # Highest threshold
        "disallow_section_headings": True,
        "disallow_meta_commentary": True,
    },
}

FORBIDDEN_SECTION_LABELS = {
    "relevant laws",
    "relevant law",
    "legal requirement",
    "legal requirements",
    "consequences",
    "detailed explanation",
    "explanation",
    "summary",
    "short summary",
    "important note",
    "practical meaning",
    "sources",
    "key takeaways",
    "key points",
    "analysis",
    "conclusion",
    "overview",
    "legal position",
    "legal analysis",
    "remedy",
    "remedies",
    "steps",
}

ALLOWED_HEADING_PREFIXES = {"note"}

META_COMMENTARY_PHRASES = [
    "in simple terms",
    "here is the simplified version",
    "here's the simplified version",
    "this is simplified",
    "simplified answer",
    "simplified explanation",
    "what this means",
    "here is the summary",
    "here's the summary",
]


def _contains_forbidden_headings(answer: str) -> bool:
    """Detect headings or section labels that violate the communication rule."""
    for raw_line in answer.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "* ", "• ")):
            # Bullet points are allowed if they stand alone
            continue
        normalized = stripped.strip("*_#> ").strip()
        if not normalized:
            continue
        normalized_no_markup = normalized.replace("**", "").replace("__", "").strip()
        lower = normalized_no_markup.lower()
        if lower.startswith("note:"):
            # Allow the standard disclaimer
            continue
        if lower in FORBIDDEN_SECTION_LABELS:
            return True
        if lower.endswith(":"):
            prefix_lower = lower[:-1].strip()
            if prefix_lower in FORBIDDEN_SECTION_LABELS and prefix_lower not in ALLOWED_HEADING_PREFIXES:
                return True
            if prefix_lower and prefix_lower not in ALLOWED_HEADING_PREFIXES:
                words = prefix_lower.split()
                if 1 <= len(words) <= 5 and all(word.isalpha() for word in words):
                    return True
        # Headings without punctuation but written as short title-case strings
        words_original = normalized_no_markup.split()
        if 1 <= len(words_original) <= 5:
            alpha_words = [word for word in words_original if word[0].isalpha()]
            if alpha_words and all(word[0].isupper() for word in alpha_words) and lower not in ALLOWED_HEADING_PREFIXES:
                return True
    return False


def _find_meta_commentary(answer: str) -> Optional[str]:
    """Return the meta commentary phrase that appears, if any."""
    lowered = answer.lower()
    for phrase in META_COMMENTARY_PHRASES:
        if phrase in lowered:
            return phrase
    return None


class ValidationResult(BaseModel):
    """Result of answer validation."""
    
    is_valid: bool = Field(description="Whether the answer passed validation")
    faithfulness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    citation_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    clarity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    problems: list[str] = Field(default_factory=list)
    hallucinated_citations: list[str] = Field(default_factory=list)
    required_fixes: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    mode_specific_issues: list[str] = Field(default_factory=list)
    
    @property
    def overall_score(self) -> float:
        """Calculate overall validation score."""
        return (
            self.faithfulness_score * 0.4 +
            self.citation_accuracy * 0.3 +
            self.completeness_score * 0.2 +
            self.clarity_score * 0.1
        )
    
    @classmethod
    def from_dict(cls, data: dict) -> "ValidationResult":
        """Create from dictionary with defaults for missing keys."""
        return cls(
            is_valid=data.get("is_valid", False),
            faithfulness_score=data.get("faithfulness_score", 0.0),
            citation_accuracy=data.get("citation_accuracy", 0.0),
            completeness_score=data.get("completeness_score", 0.0),
            clarity_score=data.get("clarity_score", 0.0),
            problems=data.get("problems", []),
            hallucinated_citations=data.get("hallucinated_citations", []),
            required_fixes=data.get("required_fixes", data.get("fixes", [])),
            missing_information=data.get("missing_information", []),
            mode_specific_issues=data.get("mode_specific_issues", [])
        )


@dataclass
class ValidatorState:
    """State for the validation loop."""
    
    query: str
    context: str
    current_answer: str
    mode: ModeType = "normal"
    attempt: int = 0
    max_attempts: int = field(default_factory=lambda: settings.max_validation_attempts)
    validation_history: list[ValidationResult] = field(default_factory=list)
    final_answer: Optional[str] = None
    is_validated: bool = False


class ValidatorAgent:
    """
    Agent for validating and improving legal answers.
    
    Implements a mode-aware validation loop that:
    1. Validates the answer for accuracy and faithfulness
    2. Applies mode-specific validation requirements
    3. If invalid, refines the answer based on feedback
    4. Repeats until valid or max attempts reached
    """
    
    def __init__(self, max_attempts: Optional[int] = None, mode: ModeType = "normal") -> None:
        """
        Initialize validator agent.
        
        Args:
            max_attempts: Maximum validation attempts
            mode: Chat mode for mode-specific validation
        """
        self.max_attempts = max_attempts or settings.max_validation_attempts
        self.mode = mode
        self.config = MODE_VALIDATION_CONFIG.get(mode, MODE_VALIDATION_CONFIG["normal"])
    
    def _validate_mode_requirements(self, answer: str, context: str) -> list[str]:
        """
        Validate mode-specific requirements.
        
        Args:
            answer: The answer to validate
            context: Source context
            
        Returns:
            List of mode-specific issues
        """
        issues = []
        
        # Check minimum citations
        min_citations = self.config.get("min_citations", 1)
        citation_patterns = [
            r'Section \d+',
            r'Art(?:icle)? \d+',
            r'BNS|BNSS|BSA|CPC|MVA|NIA|HMA|IDA',
            r'§\s*\d+',
        ]
        citations_found = set()
        for pattern in citation_patterns:
            citations_found.update(re.findall(pattern, answer, re.IGNORECASE))
        
        if len(citations_found) < min_citations:
            issues.append(f"Insufficient citations: found {len(citations_found)}, need {min_citations}")
        
        # Check minimum paragraphs
        min_paragraphs = self.config.get("min_paragraphs", 1)
        paragraphs = [p.strip() for p in answer.split("\n\n") if p.strip()]
        if len(paragraphs) < min_paragraphs:
            issues.append(f"Insufficient depth: {len(paragraphs)} paragraphs, need {min_paragraphs}")
        
        # Check for disclaimer requirement
        if self.config.get("require_disclaimer"):
            disclaimer_keywords = ["consult", "professional", "not legal advice", "disclaimer", "verification"]
            has_disclaimer = any(kw.lower() in answer.lower() for kw in disclaimer_keywords)
            if not has_disclaimer and len(answer) > 200:  # Only require for substantial answers
                issues.append("Missing appropriate disclaimer")
        
        # Check for limitations section (deep mode)
        if self.config.get("require_limitations"):
            if "limitation" not in answer.lower() and "caveat" not in answer.lower():
                issues.append("Missing Limitations section for deep research")
        
        # Check for web sources (web mode)
        if self.config.get("require_web_sources"):
            web_indicators = ["http", "www", "source:", "according to"]
            has_web = any(indicator.lower() in answer.lower() for indicator in web_indicators)
            if not has_web:
                issues.append("Missing web source references")
        
        # Check for chain of thought (lawyer/deep modes)
        if self.config.get("require_chain_of_thought"):
            reasoning_keywords = ["because", "therefore", "thus", "since", "given that", "considering"]
            reasoning_count = sum(1 for kw in reasoning_keywords if kw.lower() in answer.lower())
            if reasoning_count < 2:
                issues.append("Insufficient legal reasoning chain")

        if self.config.get("disallow_section_headings") and _contains_forbidden_headings(answer):
            issues.append("Remove headings or section labels and rewrite the answer as natural paragraphs unless the user requested structured formatting")

        if self.config.get("disallow_meta_commentary"):
            meta_phrase = _find_meta_commentary(answer)
            if meta_phrase:
                issues.append("Remove meta commentary such as 'in simple terms' or similar phrases")
        
        return issues
    
    @tracer.start_as_current_span("validator_validate")
    async def validate(
        self,
        query: str,
        context: str,
        answer: str
    ) -> ValidationResult:
        """
        Validate an answer.
        
        Args:
            query: User's query
            context: Retrieved legal documents
            answer: Answer to validate
            
        Returns:
            ValidationResult: Validation result
        """
        span = trace.get_current_span()
        span.set_attribute("answer_length", len(answer))
        span.set_attribute("mode", self.mode)
        
        try:
            # Core validation
            result_dict = await validate_answer(query, context, answer)
            result = ValidationResult.from_dict(result_dict)
            
            # Mode-specific validation
            mode_issues = self._validate_mode_requirements(answer, context)
            result.mode_specific_issues = mode_issues
            
            # Adjust is_valid based on mode strictness
            strictness = self.config.get("strictness", 0.7)
            if result.overall_score < strictness:
                result.is_valid = False
                if mode_issues:
                    result.problems.extend(mode_issues)
                    result.required_fixes.extend([f"Fix: {issue}" for issue in mode_issues])
            
            span.set_attribute("is_valid", result.is_valid)
            span.set_attribute("overall_score", result.overall_score)
            span.set_attribute("problems_count", len(result.problems))
            span.set_attribute("mode_issues_count", len(mode_issues))
            
            logger.info(
                "Validation completed",
                is_valid=result.is_valid,
                score=result.overall_score,
                problems=len(result.problems),
                mode=self.mode,
                mode_issues=len(mode_issues)
            )
            
            return result
            
        except Exception as e:
            span.set_attribute("error", True)
            span.set_attribute("error.message", str(e))
            logger.error("Validation failed", error=str(e))
            
            # Return a failed validation result
            return ValidationResult(
                is_valid=False,
                problems=[f"Validation error: {str(e)}"],
                required_fixes=["Retry validation"]
            )
    
    @tracer.start_as_current_span("validator_refine")
    async def refine(
        self,
        query: str,
        context: str,
        answer: str,
        validation: ValidationResult
    ) -> str:
        """
        Refine an answer based on validation feedback.
        
        Args:
            query: User's query
            context: Retrieved legal documents
            answer: Answer to refine
            validation: Validation result with issues
            
        Returns:
            str: Refined answer
        """
        span = trace.get_current_span()
        span.set_attribute("issues_count", len(validation.problems))
        span.set_attribute("fixes_count", len(validation.required_fixes))
        
        refined = await refine_answer(
            query=query,
            context=context,
            draft_answer=answer,
            issues=validation.problems,
            fixes=validation.required_fixes
        )
        
        span.set_attribute("refined_length", len(refined))
        
        return refined
    
    @tracer.start_as_current_span("validator_loop")
    async def run_validation_loop(
        self,
        query: str,
        context: str,
        initial_answer: str
    ) -> tuple[str, list[ValidationResult], bool]:
        """
        Run the full validation loop.
        
        Args:
            query: User's query
            context: Retrieved legal documents
            initial_answer: Initial answer to validate
            
        Returns:
            tuple[str, list[ValidationResult], bool]: 
                (final_answer, validation_history, passed_validation)
        """
        span = trace.get_current_span()
        span.set_attribute("max_attempts", self.max_attempts)
        
        state = ValidatorState(
            query=query,
            context=context,
            current_answer=initial_answer,
            max_attempts=self.max_attempts
        )
        
        while state.attempt < state.max_attempts:
            state.attempt += 1
            span.set_attribute(f"attempt_{state.attempt}_started", True)
            
            logger.info(
                "Validation attempt",
                attempt=state.attempt,
                max_attempts=state.max_attempts
            )
            
            # Validate current answer
            validation = await self.validate(
                state.query,
                state.context,
                state.current_answer
            )
            state.validation_history.append(validation)
            
            if validation.is_valid:
                state.is_validated = True
                state.final_answer = state.current_answer
                span.set_attribute("passed", True)
                span.set_attribute("attempts_used", state.attempt)
                
                logger.info(
                    "Validation passed",
                    attempt=state.attempt,
                    score=validation.overall_score
                )
                break
            
            # Check if we should continue
            if state.attempt >= state.max_attempts:
                logger.warning(
                    "Max validation attempts reached",
                    attempts=state.attempt
                )
                break
            
            # Refine the answer
            state.current_answer = await self.refine(
                state.query,
                state.context,
                state.current_answer,
                validation
            )
        
        # If not validated, use the last attempt's answer
        if not state.is_validated:
            state.final_answer = state.current_answer
            span.set_attribute("passed", False)
            span.set_attribute("attempts_used", state.attempt)
        
        return (
            state.final_answer or initial_answer,
            state.validation_history,
            state.is_validated
        )


# Convenience functions

async def validate_and_refine(
    query: str,
    context: str,
    answer: str,
    max_attempts: Optional[int] = None,
    mode: ModeType = "normal"
) -> tuple[str, bool, list[ValidationResult]]:
    """
    Validate and refine an answer using the validation loop.
    
    Args:
        query: User's query
        context: Retrieved legal documents
        answer: Initial answer
        max_attempts: Maximum validation attempts
        mode: Chat mode for mode-specific validation
        
    Returns:
        tuple[str, bool, list[ValidationResult]]:
            (final_answer, passed_validation, validation_history)
    """
    validator = ValidatorAgent(max_attempts=max_attempts, mode=mode)
    final_answer, history, passed = await validator.run_validation_loop(
        query=query,
        context=context,
        initial_answer=answer
    )
    return final_answer, passed, history


def quick_validate(
    query: str,
    context: str,
    answer: str,
    mode: ModeType = "normal"
) -> ValidationResult:
    """
    Perform a single validation without the refinement loop.
    
    Args:
        query: User's query
        context: Retrieved legal documents
        answer: Answer to validate
        mode: Chat mode for mode-specific validation
        
    Returns:
        ValidationResult: Validation result
    """
    validator = ValidatorAgent(mode=mode)
    return validator.validate(query, context, answer)


def get_mode_config(mode: ModeType) -> Dict[str, Any]:
    """
    Get validation configuration for a specific mode.
    
    Args:
        mode: Chat mode
        
    Returns:
        Validation configuration dictionary
    """
    return MODE_VALIDATION_CONFIG.get(mode, MODE_VALIDATION_CONFIG["normal"])
