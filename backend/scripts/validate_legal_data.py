#!/usr/bin/env python3
"""
NyayamGPT - Legal Data Validation & Cleanup Script
===================================================
Validates and reports on legal data files accuracy against official Indian law sources.

Official Section Counts (as of 2024):
- IPC (Indian Penal Code, 1860): Sections 1-511 (23 chapters)
- CrPC (Code of Criminal Procedure, 1973): Sections 1-484 (37 chapters)
- CPC (Code of Civil Procedure, 1908): Sections 1-158 (11 parts)
- IEA (Indian Evidence Act, 1872): Sections 1-167 (3 parts)
- HMA (Hindu Marriage Act, 1955): Sections 1-30 (5 chapters)
- NIA (National Investigation Agency Act, 2008): Sections 1-25
- IDA (Industrial Disputes Act, 1947): Sections 1-40 (6 chapters)
- MVA (Motor Vehicles Act, 1988): Sections 1-217 (14 chapters)
- BNS (Bharatiya Nyaya Sanhita, 2023): Sections 1-358 (20 chapters)
- BNSS (Bharatiya Nagarik Suraksha Sanhita, 2023): Sections 1-531 (24 chapters)
- BSA (Bharatiya Sakshya Adhiniyam, 2023): Sections 1-170

Note: Many laws have sub-sections (e.g., 302A, 302B) which are legitimate entries.
"""

import json
import re
import sys
from pathlib import Path

# Official section counts for Indian laws
OFFICIAL_COUNTS = {
    "IPC": {"main_sections": 511, "chapters": 23, "allows_subsections": True},
    "CrPC": {"main_sections": 484, "chapters": 37, "allows_subsections": True},
    "CPC": {"main_sections": 158, "chapters": 11, "allows_subsections": True},
    "Indian Evidence Act": {"main_sections": 167, "chapters": 3, "allows_subsections": False},
    "Hindu Marriage Act": {"main_sections": 30, "chapters": 5, "allows_subsections": True},
    "Negotiable Instruments Act": {"main_sections": 148, "chapters": 17, "allows_subsections": False},
    "Industrial Disputes Act": {"main_sections": 40, "chapters": 6, "allows_subsections": True},
    "Motor Vehicles Act": {"main_sections": 217, "chapters": 14, "allows_subsections": True},
    "BNS": {"main_sections": 358, "chapters": 20, "allows_subsections": False},
    "BNSS": {"main_sections": 531, "chapters": 24, "allows_subsections": False},
    "BSA": {"main_sections": 170, "chapters": 0, "allows_subsections": False},
}

FILE_TO_LAW = {
    "ipc.json": "IPC",
    "crpc.json": "CrPC",
    "cpc.json": "CPC",
    "iea.json": "Indian Evidence Act",
    "hma.json": "Hindu Marriage Act",
    "nia.json": "Negotiable Instruments Act",
    "ida.json": "Industrial Disputes Act",
    "mva.json": "Motor Vehicles Act",
}


def parse_section_number(section_str: str) -> tuple[int, str]:
    """Parse section like '302A' into (302, 'A')."""
    match = re.match(r'^(\d+)([A-Za-z]*)$', str(section_str).strip())
    if match:
        return int(match.group(1)), match.group(2).upper()
    return 0, ""


def validate_json_file(filepath: Path) -> dict:
    """Validate a single JSON data file."""
    filename = filepath.name.lower()
    law_name = FILE_TO_LAW.get(filename)
    
    if not law_name:
        return {"error": f"Unknown law file: {filename}"}
    
    official = OFFICIAL_COUNTS.get(law_name, {})
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    sections = []
    main_sections = set()
    issues = []
    
    if isinstance(data, list):
        for i, item in enumerate(data):
            # Handle malformed CSV-like JSON (e.g., hma.json)
            if len(item) == 1 and "chapter,section,section_title,section_desc" in item:
                csv_value = item.get("chapter,section,section_title,section_desc", "")
                if not csv_value or "," not in csv_value:
                    continue
                # Parse CSV with proper quote handling
                parts = csv_value.split(",", 3)
                if len(parts) >= 2:
                    section_str = parts[1].strip()
                else:
                    continue
            else:
                section_str = str(item.get("Section", item.get("section", "")))
            
            if not section_str:
                continue
            
            main_num, suffix = parse_section_number(section_str)
            
            if main_num > 0:
                sections.append(section_str)
                main_sections.add(main_num)
            else:
                # Invalid section format
                if section_str.strip() and not section_str[0].isdigit():
                    issues.append(f"Invalid section format at index {i}: '{section_str[:50]}'")
    
    # Analysis
    max_section = max(main_sections) if main_sections else 0
    missing_main = set(range(1, official.get("main_sections", 0) + 1)) - main_sections
    extra_main = main_sections - set(range(1, official.get("main_sections", 0) + 1))
    
    return {
        "law": law_name,
        "file": filename,
        "total_entries": len(data) if isinstance(data, list) else 0,
        "valid_sections": len(sections),
        "unique_main_sections": len(main_sections),
        "official_main_sections": official.get("main_sections", "?"),
        "section_range": f"1-{max_section}" if max_section else "N/A",
        "missing_sections": sorted(missing_main)[:10] if missing_main else [],
        "missing_count": len(missing_main),
        "extra_sections": sorted(extra_main)[:10] if extra_main else [],
        "extra_count": len(extra_main),
        "allows_subsections": official.get("allows_subsections", False),
        "issues": issues[:5],
        "status": "✅ OK" if len(main_sections) >= official.get("main_sections", 0) * 0.9 else "⚠️ CHECK"
    }


def main():
    data_dir = Path(__file__).parent.parent / "data"
    
    print("=" * 70)
    print("NyayamGPT Legal Data Validation Report")
    print("=" * 70)
    print()
    
    for json_file in sorted(data_dir.glob("*.json")):
        result = validate_json_file(json_file)
        
        if "error" in result:
            print(f"❌ {json_file.name}: {result['error']}")
            continue
        
        print(f"{result['status']} {result['law']} ({result['file']})")
        print(f"   Entries: {result['total_entries']}, Valid: {result['valid_sections']}")
        print(f"   Unique main sections: {result['unique_main_sections']} / {result['official_main_sections']} expected")
        print(f"   Range: {result['section_range']}")
        
        if result['missing_count'] > 0:
            print(f"   ⚠️  Missing {result['missing_count']} sections: {result['missing_sections']}...")
        if result['extra_count'] > 0:
            print(f"   ℹ️  Extra {result['extra_count']} sections: {result['extra_sections']}...")
        if result['issues']:
            print(f"   ⚠️  Issues: {result['issues'][:3]}")
        print()
    
    print("=" * 70)
    print("Note: Sub-sections (e.g., 302A, 302B) are legitimate for laws that allow them.")
    print("Extra sections beyond official count may be due to amendments or sub-sections.")
    print("=" * 70)


if __name__ == "__main__":
    main()
