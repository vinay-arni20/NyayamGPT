"""
Export BNS (Bharatiya Nyaya Sanhita) PDF to JSON format.

This script extracts all sections from BNS.pdf and saves them in a structured
JSON format matching other law data files (ipc.json, crpc.json, etc.).

Usage:
    cd backend
    python scripts/export_bns_to_json.py

Output:
    data/bns.json - Structured JSON file with all BNS sections
"""

import json
import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pypdf
except ImportError:
    print("ERROR: pypdf not installed. Install with: pip install pypdf")
    sys.exit(1)


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    total = 0
    prev = 0
    for char in reversed(roman.upper()):
        current = values.get(char, 0)
        if current < prev:
            total -= current
        else:
            total += current
        prev = current
    return total


def get_chapter_for_section(section_num: int) -> tuple[int, str]:
    """
    Get chapter number and title for a given section number.
    Based on official BNS (Bharatiya Nyaya Sanhita, 2023) structure.
    Source: https://www.indiacode.nic.in/handle/123456789/20086
    
    BNS has 20 Chapters and 358 Sections.
    """
    # Official BNS Chapter structure (section ranges)
    section_to_chapter = [
        (1, 3, 1, "Preliminary"),
        (4, 13, 2, "Of Punishments"),
        (14, 44, 3, "General Exceptions"),
        (45, 62, 4, "Of Abetment, Criminal Conspiracy and Attempt"),
        (63, 99, 5, "Of Offences against Woman and Child"),
        (100, 113, 6, "Of Offences affecting Life"),
        (114, 124, 7, "Of Hurt"),
        (125, 130, 8, "Of Wrongful Restraint and Wrongful Confinement"),
        (131, 138, 9, "Of Criminal Force and Assault"),
        (139, 146, 10, "Of Kidnapping, Abduction, Slavery and Forced Labour"),
        (147, 158, 11, "Of Sexual Offences"),
        (159, 175, 12, "Of Offences against the State"),
        (176, 190, 13, "Of Offences relating to Elections"),
        (191, 202, 14, "Of Offences relating to Coins and Government Stamps"),
        (203, 219, 15, "Of Offences relating to Weights and Measures"),
        (220, 240, 16, "Of Offences affecting Public Health, Safety and Convenience"),
        (241, 256, 17, "Of Offences relating to Religion"),
        (257, 302, 18, "Of Offences against Public Tranquility"),
        (303, 351, 19, "Of Offences against Property"),
        (352, 358, 20, "Miscellaneous"),
    ]
    
    for start, end, chapter, title in section_to_chapter:
        if start <= section_num <= end:
            return chapter, title
    
    # Default fallback
    return 0, "Unknown Chapter"


def extract_bns_sections(pdf_path: str) -> list[dict]:
    """
    Extract sections from BNS PDF.
    
    Args:
        pdf_path: Path to BNS.pdf
        
    Returns:
        List of section dictionaries matching JSON format
    """
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    
    print(f"📄 Reading {pdf_path}...")
    print(f"   Total pages: {len(reader.pages)}")
    
    # Extract text from all pages
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            # Clean up common PDF extraction issues
            text = text.replace('\x00', '')  # Remove null bytes
            # Normalize horizontal whitespace only (preserve newlines for parsing)
            text = re.sub(r'[^\S\n]+', ' ', text)  # Multiple spaces/tabs -> single space
            text = re.sub(r' ?\n ?', '\n', text)  # Clean line breaks
            text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
            full_text += text + "\n"
    
    if not full_text.strip():
        print("ERROR: PDF appears to be empty or scanned (no text extracted)")
        return []
    
    # Parse sections - BNS format: "58. TITLE IN ALL CAPS" at start of line
    section_pattern = re.compile(r'^(\d{1,3})\.\s+([A-Z][A-Z\s,\-–—\'\"()]+)')
    
    section_data = []
    
    lines = full_text.split('\n')
    char_pos = 0
    
    print("🔍 Parsing sections...")
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for section (must start line with "N. TITLE")
        section_match = section_pattern.match(stripped)
        if section_match:
            section_num = int(section_match.group(1))
            title = section_match.group(2).strip()
            # Clean up title - remove trailing footnote numbers
            title = re.sub(r'\d{1,3}$', '', title).strip()
            title = re.sub(r'[.\s]+$', '', title)
            # Convert to title case for readability
            title = title.title()
            
            section_data.append({
                "section": section_num,
                "title": title,
                "start_pos": char_pos
            })
        
        char_pos += len(line) + 1  # +1 for newline
    
    # Remove duplicates - keep first occurrence
    seen_sections = set()
    unique_sections = []
    for sec in section_data:
        if sec["section"] not in seen_sections:
            seen_sections.add(sec["section"])
            unique_sections.append(sec)
    
    section_data = unique_sections
    
    print(f"   Found {len(section_data)} unique sections")
    
    # Extract content for each section
    sections = []
    for i, sec in enumerate(section_data):
        next_pos = section_data[i + 1]["start_pos"] if i + 1 < len(section_data) else len(full_text)
        content = full_text[sec["start_pos"]:next_pos].strip()
        
        # Remove the section header from content (first line)
        content_lines = content.split('\n')
        if content_lines:
            content = '\n'.join(content_lines[1:]).strip()
        
        # Get proper chapter info based on section number
        chapter_num, chapter_title = get_chapter_for_section(sec["section"])
        
        sections.append({
            "chapter": chapter_num,
            "chapter_title": chapter_title,
            "Section": sec["section"],
            "section_title": sec["title"],
            "section_desc": content
        })
    
    return sections


def main():
    """Main function to export BNS PDF to JSON."""
    
    # Paths
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    pdf_path = data_dir / "BNS.pdf"
    output_path = data_dir / "bns.json"
    
    print("=" * 60)
    print("📚 BNS (Bharatiya Nyaya Sanhita, 2023) to JSON Exporter")
    print("=" * 60)
    print()
    
    # Check if PDF exists
    if not pdf_path.exists():
        print(f"❌ ERROR: BNS.pdf not found at {pdf_path}")
        sys.exit(1)
    
    # Extract sections
    sections = extract_bns_sections(str(pdf_path))
    
    if not sections:
        print("❌ ERROR: No sections extracted from PDF")
        sys.exit(1)
    
    # Get chapter statistics
    chapters = {}
    for sec in sections:
        ch = sec["chapter"]
        if ch not in chapters:
            chapters[ch] = {"title": sec["chapter_title"], "count": 0}
        chapters[ch]["count"] += 1
    
    print()
    print("📊 Statistics:")
    print(f"   Total Sections: {len(sections)}")
    print(f"   Total Chapters: {len(chapters)}")
    print()
    
    # Show chapter breakdown
    print("📑 Chapter Breakdown:")
    for ch_num in sorted(chapters.keys()):
        ch = chapters[ch_num]
        title = ch['title'][:45] + "..." if len(ch['title']) > 45 else ch['title']
        print(f"   Chapter {ch_num:2d}: {title} ({ch['count']} sections)")
    
    print()
    
    # Save to JSON
    print(f"💾 Saving to {output_path}...")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    
    # Verify the output
    file_size = output_path.stat().st_size / 1024  # KB
    print(f"   File size: {file_size:.1f} KB")
    
    print()
    print("=" * 60)
    print("✅ Export complete!")
    print("=" * 60)
    print()
    print(f"📁 Output file: {output_path}")
    print()
    print("📋 JSON Structure (matching IPC, CrPC, etc.):")
    print("   [")
    print("     {")
    print('       "chapter": 1,')
    print('       "chapter_title": "Preliminary",')
    print('       "Section": 1,')
    print('       "section_title": "Short Title, Commencement And Application",')
    print('       "section_desc": "..."')
    print("     },")
    print("     ...")
    print("   ]")
    print()
    
    # Show sample entries
    print("📝 Sample entries:")
    for sample in sections[:2]:
        print(f"\n   Section {sample['Section']}: {sample['section_title']}")
        desc = sample['section_desc'][:150] + "..." if len(sample['section_desc']) > 150 else sample['section_desc']
        print(f"   Chapter {sample['chapter']}: {sample['chapter_title']}")
        print(f"   Content: {desc}")
    

if __name__ == "__main__":
    main()
