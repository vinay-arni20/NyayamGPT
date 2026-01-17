"""
Query Classifier for Constrained RAG
=====================================
Pre-processes user queries to classify intent and filter retrieval.

This classifier categorizes queries BEFORE they hit the vector store,
ensuring that irrelevant sections (like murder for verbal abuse cases)
are filtered out.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re


class OffenseNature(Enum):
    """Nature of offense for filtering."""
    VERBAL = "verbal"
    PHYSICAL = "physical"
    PROPERTY = "property"
    SEXUAL = "sexual"
    CYBER = "cyber"
    PROCEDURAL = "procedural"
    OTHER = "other"
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    """Expected severity level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CAPITAL = "capital"
    UNKNOWN = "unknown"


@dataclass
class QueryClassification:
    """Classification result for a user query."""
    
    # Primary classification
    offense_nature: OffenseNature
    severity_level: SeverityLevel
    
    # Context
    involves_caste: bool = False
    involves_domestic: bool = False
    involves_minor: bool = False
    involves_woman: bool = False
    involves_death: bool = False
    
    # Retrieval filters
    must_include_keywords: List[str] = None
    must_exclude_keywords: List[str] = None
    topic_filters: List[str] = None
    
    # Confidence
    confidence: float = 0.0
    reasoning: str = ""
    
    def __post_init__(self):
        if self.must_include_keywords is None:
            self.must_include_keywords = []
        if self.must_exclude_keywords is None:
            self.must_exclude_keywords = []
        if self.topic_filters is None:
            self.topic_filters = []


# ============================================================================
# KEYWORD PATTERNS FOR CLASSIFICATION
# ============================================================================

VERBAL_PATTERNS = [
    r'\b(scold|insult|abuse|humiliat|mock|taunt|slur|defam|slander)\w*\b',
    r'\b(threat|intimidat|verbal|words?|gesture|spoke|said|called)\w*\b',
    r'\b(dignity|reputation|honor|honour|embarrass)\w*\b',
    r'\b(caste|religion|community|ethnic|racial)\s*(abuse|slur|insult|discrimination)\b',
]

PHYSICAL_PATTERNS = [
    r'\b(hit|beat|punch|kick|slap|assault|attack|injur|hurt|wound)\w*\b',
    r'\b(kill|murder|death|dead|died|stab|shot|poison)\w*\b',
    r'\b(kidnap|abduct|confine|restrain|detain|imprison)\w*\b',
    r'\b(rape|molest|sexual\s+assault|gang\s*rape)\w*\b',
    r'\b(acid\s+attack|burn|torture|maim|disfigure)\w*\b',
    r'\b(mob|lynch|riot|grievous|bodily|physical)\w*\b',
]

PROPERTY_PATTERNS = [
    r'\b(stole|steal|theft|thief|rob|loot|snatch)\w*\b',
    r'\b(cheat|fraud|deceive|scam|swindle|extort)\w*\b',
    r'\b(trespass|encroach|property|land|house)\w*\b',
    r'\b(damage|destroy|vandali[sz]e|mischief)\w*\b',
    r'\b(forge|counterfeit|fake|fraudulent|document)\w*\b',
    r'\b(misappropriat|embezzle|breach\s+of\s+trust)\w*\b',
]

SEXUAL_PATTERNS = [
    r'\b(rape|molest|sexual|modesty|indecen|obscen)\w*\b',
    r'\b(stalk|voyeur|harass|eve\s*teas)\w*\b',
    r'\b(nude|naked|disrobe|strip|pornograph)\w*\b',
    r'\b(prostitut|traffick|exploit)\w*\b',
]

CYBER_PATTERNS = [
    r'\b(online|internet|cyber|digital|computer|hack)\w*\b',
    r'\b(phish|malware|virus|data\s+breach|identity\s+theft)\w*\b',
    r'\b(social\s+media|facebook|whatsapp|instagram|twitter)\w*\b',
    r'\b(email|website|account|password)\w*\b',
]

# Context patterns
CASTE_PATTERNS = [
    r'\b(caste|dalit|schedule[d]?\s*(caste|tribe)|sc/?st)\b',
    r'\b(untouchab|brahmin|kshatriya|vaishya|shudra)\b',
    r'\b(backward\s*class|obc|minority)\b',
    r'\b(community|ethnic|racial)\s*(slur|abuse|discrimination)\b',
]

DOMESTIC_PATTERNS = [
    r'\b(husband|wife|spouse|marriage|married|domestic)\b',
    r'\b(in-?laws?|mother-?in-?law|father-?in-?law)\b',
    r'\b(dowry|cruelty|matrimonial|marital)\b',
    r'\b(divorce|maintenance|alimony)\b',
]

MINOR_PATTERNS = [
    r'\b(child|minor|juvenile|kid|infant|baby|teenager)\b',
    r'\b(school|student|teacher|guardian|parent)\b',
    r'\b(underage|below\s*18|under\s*18)\b',
    r'\b(pocso|child\s*abuse|child\s*protection)\b',
]

WOMAN_PATTERNS = [
    r'\b(woman|women|girl|female|lady|mother|daughter|sister)\b',
    r'\b(eve\s*teasing|modesty|disrobe|sexual\s*harassment)\b',
    r'\b(dowry|cruelty|acid\s*attack|honor\s*killing)\b',
]

DEATH_PATTERNS = [
    r'\b(kill|murder|death|dead|died|homicide)\b',
    r'\b(lynching|mob\s*violence)\b',
    r'\b(capital\s*punishment|death\s*penalty)\b',
]

# ============================================================================
# CLASSIFIER CLASS
# ============================================================================

class QueryClassifier:
    """Classifies legal queries for constrained retrieval."""
    
    def __init__(self):
        self.patterns = {
            OffenseNature.VERBAL: [re.compile(p, re.I) for p in VERBAL_PATTERNS],
            OffenseNature.PHYSICAL: [re.compile(p, re.I) for p in PHYSICAL_PATTERNS],
            OffenseNature.PROPERTY: [re.compile(p, re.I) for p in PROPERTY_PATTERNS],
            OffenseNature.SEXUAL: [re.compile(p, re.I) for p in SEXUAL_PATTERNS],
            OffenseNature.CYBER: [re.compile(p, re.I) for p in CYBER_PATTERNS],
        }
        
        self.context_patterns = {
            "caste": [re.compile(p, re.I) for p in CASTE_PATTERNS],
            "domestic": [re.compile(p, re.I) for p in DOMESTIC_PATTERNS],
            "minor": [re.compile(p, re.I) for p in MINOR_PATTERNS],
            "woman": [re.compile(p, re.I) for p in WOMAN_PATTERNS],
            "death": [re.compile(p, re.I) for p in DEATH_PATTERNS],
        }
    
    def classify(self, query: str) -> QueryClassification:
        """
        Classify a user query for constrained retrieval.
        
        Args:
            query: The user's question about legal matters.
            
        Returns:
            QueryClassification with filtering parameters.
        """
        query_lower = query.lower()
        
        # Score each offense nature
        scores = {}
        for nature, patterns in self.patterns.items():
            score = sum(1 for p in patterns if p.search(query))
            if score > 0:
                scores[nature] = score
        
        # Determine primary offense nature
        if not scores:
            primary_nature = OffenseNature.UNKNOWN
        else:
            primary_nature = max(scores, key=scores.get)
        
        # Detect context
        involves_caste = any(p.search(query) for p in self.context_patterns["caste"])
        involves_domestic = any(p.search(query) for p in self.context_patterns["domestic"])
        involves_minor = any(p.search(query) for p in self.context_patterns["minor"])
        involves_woman = any(p.search(query) for p in self.context_patterns["woman"])
        involves_death = any(p.search(query) for p in self.context_patterns["death"])
        
        # Determine severity
        severity = self._determine_severity(primary_nature, involves_death)
        
        # Build filters
        must_include, must_exclude, topics, reasoning = self._build_filters(
            primary_nature, involves_caste, involves_domestic, 
            involves_minor, involves_woman, involves_death
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(scores, primary_nature)
        
        return QueryClassification(
            offense_nature=primary_nature,
            severity_level=severity,
            involves_caste=involves_caste,
            involves_domestic=involves_domestic,
            involves_minor=involves_minor,
            involves_woman=involves_woman,
            involves_death=involves_death,
            must_include_keywords=must_include,
            must_exclude_keywords=must_exclude,
            topic_filters=topics,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def _determine_severity(self, nature: OffenseNature, involves_death: bool) -> SeverityLevel:
        """Determine expected severity based on nature and context."""
        if involves_death:
            return SeverityLevel.CAPITAL
        
        severity_map = {
            OffenseNature.VERBAL: SeverityLevel.LOW,
            OffenseNature.PROPERTY: SeverityLevel.MEDIUM,
            OffenseNature.PHYSICAL: SeverityLevel.HIGH,
            OffenseNature.SEXUAL: SeverityLevel.HIGH,
            OffenseNature.CYBER: SeverityLevel.MEDIUM,
            OffenseNature.PROCEDURAL: SeverityLevel.UNKNOWN,
            OffenseNature.OTHER: SeverityLevel.UNKNOWN,
            OffenseNature.UNKNOWN: SeverityLevel.UNKNOWN,
        }
        
        return severity_map.get(nature, SeverityLevel.UNKNOWN)
    
    def _build_filters(
        self, nature: OffenseNature, 
        involves_caste: bool, involves_domestic: bool,
        involves_minor: bool, involves_woman: bool, involves_death: bool
    ) -> Tuple[List[str], List[str], List[str], str]:
        """Build keyword filters based on classification."""
        
        must_include = []
        must_exclude = []
        topics = []
        reasoning_parts = []
        
        # CRITICAL: Verbal abuse should NOT return murder sections
        if nature == OffenseNature.VERBAL and not involves_death:
            must_exclude.extend(["murder", "death", "homicide", "grievous hurt", "rape"])
            must_include.extend(["insult", "defamation", "intimidation"])
            topics.append("defamation_and_insult")
            reasoning_parts.append("Query involves verbal offense without physical harm - excluding physical violence sections")
        
        # Caste discrimination
        if involves_caste:
            must_include.extend(["caste", "discrimination", "insult"])
            topics.append("defamation_and_insult")
            reasoning_parts.append("Caste-based discrimination detected - including SC/ST Act provisions")
        
        # Domestic violence
        if involves_domestic:
            must_include.extend(["cruelty", "domestic", "husband", "wife"])
            topics.append("marriage_and_family")
            reasoning_parts.append("Domestic context detected - focusing on matrimonial provisions")
        
        # Offenses involving minors
        if involves_minor:
            must_include.extend(["child", "minor", "juvenile"])
            topics.append("offences_against_children")
            reasoning_parts.append("Minor involved - including child protection provisions (POCSO may apply)")
        
        # Offenses against women
        if involves_woman and nature in [OffenseNature.SEXUAL, OffenseNature.PHYSICAL]:
            topics.append("offences_against_women")
            reasoning_parts.append("Woman victim in violence case - including women protection provisions")
        
        # Physical violence
        if nature == OffenseNature.PHYSICAL:
            topics.append("offences_against_body")
            if involves_death:
                must_include.extend(["murder", "homicide", "death"])
                reasoning_parts.append("Death/killing involved - including homicide provisions")
            else:
                must_include.extend(["hurt", "injury", "assault"])
                reasoning_parts.append("Physical violence without death - focusing on hurt/assault provisions")
        
        # Property offenses
        if nature == OffenseNature.PROPERTY:
            topics.append("offences_against_property")
            reasoning_parts.append("Property offense detected - focusing on theft/cheating provisions")
        
        # Sexual offenses
        if nature == OffenseNature.SEXUAL:
            topics.append("offences_against_women")
            if involves_minor:
                reasoning_parts.append("Sexual offense against minor - POCSO Act applies")
            else:
                reasoning_parts.append("Sexual offense detected - including modesty/assault provisions")
        
        # Cyber offenses
        if nature == OffenseNature.CYBER:
            must_include.extend(["computer", "electronic", "cyber"])
            reasoning_parts.append("Cyber offense detected - IT Act provisions apply")
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "General query - no specific filters applied"
        
        return must_include, must_exclude, topics, reasoning
    
    def _calculate_confidence(self, scores: Dict, nature: OffenseNature) -> float:
        """Calculate classification confidence."""
        if not scores:
            return 0.3  # Low confidence for unknown
        
        total_score = sum(scores.values())
        if nature == OffenseNature.UNKNOWN:
            return 0.3
        
        nature_score = scores.get(nature, 0)
        
        # High confidence if dominant pattern
        if nature_score >= 3:
            return 0.95
        elif nature_score == 2:
            return 0.85
        elif nature_score == 1:
            # Check if there's competition
            if len(scores) == 1:
                return 0.75
            else:
                return 0.6
        
        return 0.5


# ============================================================================
# QUERY FILTER BUILDER
# ============================================================================

def build_vector_filter(classification: QueryClassification) -> Dict[str, Any]:
    """
    Build a ChromaDB-compatible filter from classification.
    
    This filter is used to constrain the vector search to only
    return relevant sections.
    """
    filters = []
    
    # Filter by offense nature (if known and confident)
    if classification.offense_nature != OffenseNature.UNKNOWN and classification.confidence >= 0.7:
        # For verbal offenses, exclude physical harm sections
        if classification.offense_nature == OffenseNature.VERBAL and not classification.involves_death:
            filters.append({
                "involves_physical_harm": {"$ne": True}
            })
    
    # Include caste-related sections if applicable
    if classification.involves_caste:
        filters.append({
            "involves_caste_discrimination": {"$eq": True}
        })
    
    # Combine filters
    if len(filters) == 0:
        return {}
    elif len(filters) == 1:
        return filters[0]
    else:
        return {"$and": filters}


def build_hybrid_search_query(
    original_query: str, 
    classification: QueryClassification
) -> str:
    """
    Build an enhanced query for hybrid search by adding
    relevant legal keywords based on classification.
    """
    enhanced_parts = [original_query]
    
    # Add must-include keywords
    for keyword in classification.must_include_keywords:
        if keyword.lower() not in original_query.lower():
            enhanced_parts.append(keyword)
    
    return " ".join(enhanced_parts)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    classifier = QueryClassifier()
    
    test_queries = [
        "My neighbor scolded me using my caste name",
        "Someone murdered my brother in a mob attack",
        "My husband beats me daily",
        "Someone stole my mobile phone",
        "A girl was raped by her teacher",
        "I was cheated in an online transaction",
        "Is scolding a person based on their caste a crime?",
        "What is the punishment for murder?",
        "My colleague made derogatory remarks about my religion",
    ]
    
    print("=" * 70)
    print("QUERY CLASSIFIER TEST")
    print("=" * 70)
    
    for query in test_queries:
        result = classifier.classify(query)
        
        print(f"\n📝 Query: {query}")
        print(f"   Nature: {result.offense_nature.value}")
        print(f"   Severity: {result.severity_level.value}")
        print(f"   Confidence: {result.confidence:.0%}")
        print(f"   Contexts: caste={result.involves_caste}, death={result.involves_death}, minor={result.involves_minor}")
        print(f"   Include: {result.must_include_keywords}")
        print(f"   Exclude: {result.must_exclude_keywords}")
        print(f"   Topics: {result.topic_filters}")
        print(f"   Reasoning: {result.reasoning}")
