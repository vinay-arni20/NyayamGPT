"""
Legal Data Enrichment Script for Constrained RAG
=================================================
This script transforms raw legal JSON data into semantically enriched 
documents with metadata for better retrieval and filtering.

Structure:
- section_id: Unique identifier (e.g., "BNS_103")
- legal_topics: List of topic categories
- offense_nature: verbal | property | physical | sexual | cyber | procedural | other
- severity_level: low | medium | high | capital
- cognizable: Whether offense is cognizable (can arrest without warrant)
- bailable: Whether offense is bailable
- keywords: Searchable keywords for hybrid search
- related_sections: Cross-references to other sections
- ipc_mapping: Old IPC section number (if applicable)
- text_content: Full section text
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# ============================================================================
# LEGAL TAXONOMY
# ============================================================================

OFFENSE_NATURE_KEYWORDS = {
    "physical": [
        "murder", "death", "kill", "hurt", "injury", "grievous", "assault", 
        "battery", "violence", "force", "bodily", "wound", "maim", "beating",
        "lynching", "mob", "dacoity", "robbery", "culpable homicide", "rape",
        "kidnapping", "abduction", "trafficking", "acid attack", "poisoning"
    ],
    "verbal": [
        "insult", "defamation", "slander", "libel", "intimidation", "threat",
        "provocation", "abuse", "word", "gesture", "outraging modesty",
        "scolding", "humiliation", "dignity", "speech", "statement", "rumor",
        "caste", "religion", "race", "community", "ethnic"
    ],
    "property": [
        "theft", "robbery", "extortion", "cheating", "fraud", "forgery",
        "mischief", "trespass", "property", "damage", "misappropriation",
        "breach of trust", "stolen", "movable", "immovable", "goods"
    ],
    "sexual": [
        "rape", "sexual", "modesty", "obscene", "voyeurism", "stalking",
        "harassment", "assault on woman", "disrobing", "nude", "pornography",
        "child abuse", "prostitution", "trafficking"
    ],
    "cyber": [
        "computer", "electronic", "digital", "online", "internet", "cyber",
        "data", "hacking", "phishing", "identity theft", "IT Act"
    ],
    "procedural": [
        "procedure", "evidence", "witness", "court", "trial", "bail",
        "arrest", "investigation", "complaint", "FIR", "magistrate",
        "jurisdiction", "limitation", "appeal"
    ]
}

SEVERITY_KEYWORDS = {
    "capital": [
        "death", "capital punishment", "death penalty", "hanging",
        "murder", "rape of child", "gang rape", "terrorism", "waging war"
    ],
    "high": [
        "life imprisonment", "imprisonment for life", "7 years", "10 years",
        "14 years", "rigorous imprisonment", "grievous", "aggravated",
        "organized crime", "dacoity", "kidnapping for ransom"
    ],
    "medium": [
        "imprisonment", "3 years", "5 years", "2 years", "cognizable",
        "non-bailable", "simple imprisonment"
    ],
    "low": [
        "fine", "community service", "1 year", "6 months", "3 months",
        "bailable", "non-cognizable", "compoundable"
    ]
}

LEGAL_TOPICS = {
    "offences_against_body": [
        "murder", "culpable homicide", "hurt", "grievous hurt", "assault",
        "force", "kidnapping", "abduction", "wrongful restraint", "confinement"
    ],
    "offences_against_women": [
        "rape", "modesty", "stalking", "voyeurism", "sexual harassment",
        "acid attack", "dowry", "cruelty by husband", "disrobing", "trafficking"
    ],
    "offences_against_children": [
        "child", "minor", "trafficking", "kidnapping", "procurement",
        "POCSO", "juvenile", "abandonment"
    ],
    "offences_against_property": [
        "theft", "extortion", "robbery", "dacoity", "cheating", "fraud",
        "mischief", "trespass", "misappropriation", "breach of trust"
    ],
    "offences_against_state": [
        "sedition", "waging war", "sovereignty", "terrorism", "unlawful assembly",
        "rioting", "promoting enmity", "public tranquility"
    ],
    "defamation_and_insult": [
        "defamation", "insult", "slander", "libel", "reputation", "dignity",
        "caste", "race", "religion", "community", "ethnic", "SC/ST"
    ],
    "public_servants": [
        "public servant", "corruption", "bribery", "official duty",
        "government", "misconduct"
    ],
    "forgery_and_documents": [
        "forgery", "counterfeiting", "false document", "stamp", "currency",
        "trademark", "fraudulent"
    ],
    "marriage_and_family": [
        "marriage", "bigamy", "adultery", "divorce", "maintenance",
        "custody", "domestic violence", "dowry"
    ]
}

# SC/ST Act and Caste-related patterns
CASTE_DISCRIMINATION_KEYWORDS = [
    "caste", "scheduled caste", "scheduled tribe", "sc/st", "dalit",
    "untouchability", "social boycott", "public place denial",
    "water source denial", "temple entry", "dignity", "humiliation",
    "slur", "derogatory", "abuse based on caste", "discrimination"
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def detect_offense_nature(text: str) -> str:
    """Detect the primary nature of offense from text."""
    text_lower = text.lower()
    scores = {}
    
    for nature, keywords in OFFENSE_NATURE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[nature] = score
    
    if not scores:
        return "other"
    
    # Return the nature with highest score
    return max(scores, key=scores.get)

def detect_severity(text: str) -> str:
    """Detect severity level from punishment clauses."""
    text_lower = text.lower()
    
    # Check in order of severity
    for kw in SEVERITY_KEYWORDS["capital"]:
        if kw in text_lower:
            return "capital"
    for kw in SEVERITY_KEYWORDS["high"]:
        if kw in text_lower:
            return "high"
    for kw in SEVERITY_KEYWORDS["medium"]:
        if kw in text_lower:
            return "medium"
    for kw in SEVERITY_KEYWORDS["low"]:
        if kw in text_lower:
            return "low"
    
    return "unspecified"

def detect_legal_topics(text: str) -> List[str]:
    """Detect all applicable legal topics."""
    text_lower = text.lower()
    topics = []
    
    for topic, keywords in LEGAL_TOPICS.items():
        if any(kw in text_lower for kw in keywords):
            topics.append(topic)
    
    return topics if topics else ["general"]

def extract_ipc_mapping(text: str) -> Optional[str]:
    """Extract IPC section mapping from comparison notes."""
    patterns = [
        r'Section\s+(\d+[A-Z]?)\s*(?:of\s+)?IPC',
        r'IPC\s+Section\s+(\d+[A-Z]?)',
        r'corresponds to Section\s+(\d+[A-Z]?)',
        r'Section\s+(\d+[A-Z]?)\s*,?\s*IPC'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return f"IPC_{matches[0]}"
    
    return None

def extract_punishment_info(text: str) -> Dict[str, Any]:
    """Extract punishment details from section text."""
    text_lower = text.lower()
    
    info = {
        "cognizable": None,
        "bailable": None,
        "max_imprisonment": None,
        "fine": None,
        "community_service": "community service" in text_lower
    }
    
    # Detect imprisonment duration
    imprisonment_patterns = [
        (r'imprisonment for life', 'life'),
        (r'death', 'death'),
        (r'(\d+)\s*years?', None),  # Will capture number
    ]
    
    for pattern, value in imprisonment_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if value:
                info["max_imprisonment"] = value
            else:
                info["max_imprisonment"] = f"{match.group(1)} years"
            break
    
    # Detect fine
    if "fine" in text_lower:
        fine_match = re.search(r'fine.*?(\d+(?:,\d+)?(?:\s*lakh)?)\s*rupees?', text_lower)
        if fine_match:
            info["fine"] = fine_match.group(1) + " rupees"
        else:
            info["fine"] = "unspecified"
    
    return info

def generate_keywords(section: Dict, text: str) -> List[str]:
    """Generate searchable keywords for hybrid search."""
    keywords = []
    text_lower = text.lower()
    
    # Add section identifier
    if "Section" in section:
        keywords.append(f"section {section['Section']}")
    
    # Add chapter info
    if "chapter_title" in section:
        keywords.extend(section["chapter_title"].lower().split())
    
    # Add section title words
    if "section_title" in section:
        keywords.extend(section["section_title"].lower().split())
    
    # Add offense nature keywords found
    for nature, kws in OFFENSE_NATURE_KEYWORDS.items():
        for kw in kws:
            if kw in text_lower and kw not in keywords:
                keywords.append(kw)
    
    # Add caste-related keywords
    for kw in CASTE_DISCRIMINATION_KEYWORDS:
        if kw in text_lower and kw not in keywords:
            keywords.append(kw)
    
    # Remove duplicates and very common words
    stopwords = {"the", "a", "an", "of", "to", "in", "for", "and", "or", "is", "be", "by"}
    keywords = [kw for kw in keywords if kw not in stopwords and len(kw) > 2]
    
    return list(set(keywords))

def is_caste_related(text: str) -> bool:
    """Check if section deals with caste-based discrimination."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in CASTE_DISCRIMINATION_KEYWORDS)

# ============================================================================
# MAIN ENRICHMENT FUNCTION
# ============================================================================

def enrich_section(section: Dict, law_code: str) -> Dict:
    """Enrich a single legal section with metadata."""
    
    # Get section number and text
    section_num = section.get("Section", section.get("section", ""))
    text = section.get("section_desc", "") or ""
    title = section.get("section_title", "") or ""
    full_text = f"{title} {text}"
    
    # Build section ID
    section_id = f"{law_code}_{section_num}"
    
    # Detect metadata
    offense_nature = detect_offense_nature(full_text)
    severity = detect_severity(full_text)
    topics = detect_legal_topics(full_text)
    ipc_mapping = extract_ipc_mapping(full_text)
    punishment = extract_punishment_info(full_text)
    keywords = generate_keywords(section, full_text)
    caste_related = is_caste_related(full_text)
    
    # Build enriched document
    enriched = {
        # Identifiers
        "section_id": section_id,
        "law_code": law_code,
        "section_number": str(section_num),
        "chapter": section.get("chapter", ""),
        "chapter_title": section.get("chapter_title", ""),
        "section_title": title,
        
        # Classification metadata
        "legal_topics": topics,
        "offense_nature": offense_nature,
        "severity_level": severity,
        "involves_physical_harm": offense_nature == "physical",
        "involves_verbal_abuse": offense_nature == "verbal",
        "involves_caste_discrimination": caste_related,
        
        # Punishment info
        "cognizable": punishment["cognizable"],
        "bailable": punishment["bailable"],
        "max_imprisonment": punishment["max_imprisonment"],
        "fine": punishment["fine"],
        "community_service": punishment["community_service"],
        
        # Searchability
        "keywords": keywords,
        "ipc_mapping": ipc_mapping,
        
        # Full content
        "text_content": text,
        "full_text_with_title": full_text
    }
    
    return enriched

def enrich_law_file(input_path: str, output_path: str, law_code: str) -> int:
    """Enrich all sections in a law file."""
    
    print(f"\n📚 Processing {law_code}...")
    
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle both array and object formats
    if isinstance(data, dict):
        sections = data.get("sections", [])
    else:
        sections = data
    
    enriched_sections = []
    for section in sections:
        enriched = enrich_section(section, law_code)
        enriched_sections.append(enriched)
    
    # Save enriched data
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched_sections, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Enriched {len(enriched_sections)} sections → {output_path}")
    return len(enriched_sections)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Enrich all legal data files."""
    
    print("=" * 60)
    print("🔧 Legal Data Enrichment for Constrained RAG")
    print("=" * 60)
    
    # Paths
    data_dir = Path(__file__).parent.parent / "data"
    enriched_dir = data_dir / "enriched"
    enriched_dir.mkdir(exist_ok=True)
    
    # Law files to process
    law_files = {
        "bns.json": "BNS",
        "bnss.json": "BNSS",
        "bsa.json": "BSA",
        "cpc.json": "CPC",
        "hma.json": "HMA",
        "ida.json": "IDA",
        "MVA.json": "MVA",
        "nia.json": "NIA"
    }
    
    total_sections = 0
    for filename, law_code in law_files.items():
        input_path = data_dir / filename
        if not input_path.exists():
            print(f"⚠️  Skipping {filename} (not found)")
            continue
        
        output_path = enriched_dir / f"{law_code.lower()}_enriched.json"
        count = enrich_law_file(str(input_path), str(output_path), law_code)
        total_sections += count
    
    print("\n" + "=" * 60)
    print(f"✅ Total: {total_sections} sections enriched")
    print(f"📁 Output: {enriched_dir}")
    print("=" * 60)
    
    # Generate metadata summary
    generate_metadata_summary(enriched_dir)

def generate_metadata_summary(enriched_dir: Path):
    """Generate a summary of the enriched data for reference."""
    
    summary = {
        "offense_nature_counts": {},
        "severity_counts": {},
        "topic_counts": {},
        "caste_related_sections": [],
        "physical_harm_sections": []
    }
    
    for enriched_file in enriched_dir.glob("*_enriched.json"):
        with open(enriched_file, "r", encoding="utf-8") as f:
            sections = json.load(f)
        
        for section in sections:
            # Count offense natures
            nature = section.get("offense_nature", "other")
            summary["offense_nature_counts"][nature] = \
                summary["offense_nature_counts"].get(nature, 0) + 1
            
            # Count severities
            severity = section.get("severity_level", "unspecified")
            summary["severity_counts"][severity] = \
                summary["severity_counts"].get(severity, 0) + 1
            
            # Count topics
            for topic in section.get("legal_topics", []):
                summary["topic_counts"][topic] = \
                    summary["topic_counts"].get(topic, 0) + 1
            
            # Track caste-related sections
            if section.get("involves_caste_discrimination"):
                summary["caste_related_sections"].append(section["section_id"])
            
            # Track physical harm sections
            if section.get("involves_physical_harm"):
                summary["physical_harm_sections"].append(section["section_id"])
    
    # Save summary
    summary_path = enriched_dir / "metadata_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n📊 Metadata Summary:")
    print(f"   - Offense Natures: {summary['offense_nature_counts']}")
    print(f"   - Severity Levels: {summary['severity_counts']}")
    print(f"   - Caste-related sections: {len(summary['caste_related_sections'])}")
    print(f"   - Physical harm sections: {len(summary['physical_harm_sections'])}")

if __name__ == "__main__":
    main()
