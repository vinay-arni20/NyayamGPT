"""
Export 2023 Criminal Codes (BNS, BNSS, BSA) PDFs to JSON format.

This script uses intelligent parsing for each code's unique format.
"""

import json
import re
import sys
from pathlib import Path

try:
    import pypdf
except ImportError:
    print("ERROR: pypdf not installed. Install with: pip install pypdf")
    sys.exit(1)


# ============ CHAPTER MAPPINGS ============

def get_bns_chapter(section_num: int) -> tuple[int, str]:
    """BNS: Bharatiya Nyaya Sanhita, 2023 - 20 Chapters"""
    chapters = [
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
    for start, end, ch, title in chapters:
        if start <= section_num <= end:
            return ch, title
    return 0, "Unknown"


def get_bnss_chapter(section_num: int) -> tuple[int, str]:
    """BNSS: Bharatiya Nagarik Suraksha Sanhita, 2023"""
    chapters = [
        (1, 6, 1, "Preliminary"),
        (7, 17, 2, "Constitution of Criminal Courts and Offices"),
        (18, 20, 3, "Public Prosecutors"),
        (21, 34, 4, "Powers of Courts"),
        (35, 61, 5, "General Provisions"),
        (62, 72, 6, "Aid to Magistrates and Police"),
        (73, 83, 7, "Arrest of Persons"),
        (84, 109, 8, "Processes to Compel Appearance"),
        (110, 134, 9, "Search and Seizure"),
        (135, 153, 10, "Security for Keeping Peace"),
        (154, 161, 11, "Unlawful Assemblies"),
        (162, 169, 12, "Public Nuisances"),
        (170, 173, 13, "Preventive Action of Police"),
        (174, 196, 14, "Information to Police and Investigation"),
        (197, 226, 15, "Jurisdiction of Courts"),
        (227, 243, 16, "Complaints to Magistrates"),
        (244, 261, 17, "Commencement of Proceedings"),
        (262, 284, 18, "Trial before Court of Session"),
        (285, 305, 19, "Trial before Magistrates"),
        (306, 353, 20, "Judgment"),
        (354, 395, 21, "General Provisions as to Inquiries and Trials"),
        (396, 429, 22, "Bail and Bonds"),
        (430, 450, 23, "Appeals"),
        (451, 481, 24, "Execution, Reference and Revision"),
        (482, 507, 25, "Disposal of Property and Irregular Proceedings"),
        (508, 521, 26, "Limitation"),
        (522, 533, 27, "Miscellaneous"),
    ]
    for start, end, ch, title in chapters:
        if start <= section_num <= end:
            return ch, title
    return 0, "Unknown"


def get_bsa_chapter(section_num: int) -> tuple[int, str]:
    """BSA: Bharatiya Sakshya Adhiniyam, 2023"""
    chapters = [
        (1, 2, 1, "Preliminary"),
        (3, 43, 2, "Relevancy of Facts"),
        (44, 55, 3, "Facts which Need Not Be Proved"),
        (56, 58, 4, "Oral Evidence"),
        (59, 90, 5, "Documentary Evidence"),
        (91, 100, 6, "Exclusion of Oral by Documentary Evidence"),
        (101, 120, 7, "Burden of Proof and Presumptions"),
        (121, 123, 8, "Estoppel"),
        (124, 139, 9, "Of Witnesses"),
        (140, 168, 10, "Examination of Witnesses"),
        (169, 170, 11, "Miscellaneous"),
    ]
    for start, end, ch, title in chapters:
        if start <= section_num <= end:
            return ch, title
    return 0, "Unknown"


def extract_toc_sections(full_text: str, max_section: int) -> dict:
    """Extract section titles from Table of Contents."""
    sections = {}
    
    # Multiple patterns for TOC entries
    patterns = [
        # Standard: "123. Title here"
        r'(\d{1,3})\.\s+([A-Za-z][^.0-9\n]{5,80}?)(?:\.|$)',
        # Short titles: "10. Mens rea"
        r'(\d{1,3})\.\s+([A-Za-z][^\n]{3,50})$',
        # With page numbers: "10. Title ....... 45"
        r'(\d{1,3})\.\s+([A-Za-z][^\n\.]{3,50})\s*\.{2,}',
    ]
    
    for pattern in patterns:
        for match in re.finditer(pattern, full_text, re.MULTILINE):
            sec_num = int(match.group(1))
            title = match.group(2).strip()
            
            # Skip if we already have this section or invalid
            if sec_num in sections or sec_num > max_section or sec_num < 1:
                continue
                
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            title = re.sub(r'\.{2,}.*$', '', title)  # Remove trailing dots
            title = title.strip()
            
            if len(title) >= 3:
                sections[sec_num] = title
    
    return sections


def extract_content_for_section(full_text: str, section_num: int, next_section: int) -> str:
    """Extract content for a specific section."""
    # Find section start - look for "N. " or "N." at start of line
    pattern = re.compile(rf'^{section_num}\.\s', re.MULTILINE)
    match = pattern.search(full_text)
    
    if not match:
        return ""
    
    start_pos = match.start()
    
    # Find next section
    if next_section:
        next_pattern = re.compile(rf'^{next_section}\.\s', re.MULTILINE)
        next_match = next_pattern.search(full_text, start_pos + 10)
        if next_match:
            end_pos = next_match.start()
        else:
            end_pos = min(start_pos + 10000, len(full_text))
    else:
        end_pos = min(start_pos + 10000, len(full_text))
    
    content = full_text[start_pos:end_pos].strip()
    
    # Remove the section number prefix
    content = re.sub(rf'^{section_num}\.\s*', '', content)
    
    return content[:8000]  # Limit content size


def extract_bns_sections(pdf_path: str) -> list[dict]:
    """Extract BNS sections using ALL CAPS title pattern."""
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text = text.replace('\x00', '')
            text = re.sub(r'[^\S\n]+', ' ', text)
            text = re.sub(r' ?\n ?', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            full_text += text + "\n"
    
    # Multiple patterns for BNS sections
    patterns = [
        # ALL CAPS: "58. TITLE IN ALL CAPS"
        r'^(\d{1,3})\.\s+([A-Z][A-Z\s,\-–—\'\"()]+)',
        # Mixed case with period: "58. Title here."
        r'^(\d{1,3})\.\s+([A-Z][a-zA-Z\s,\-–—\'\"()]+?)\.?\n',
    ]
    
    section_data = []
    seen = set()
    
    for pattern in patterns:
        for match in re.finditer(pattern, full_text, re.MULTILINE):
            section_num = int(match.group(1))
            if section_num not in seen and 1 <= section_num <= 358:
                title = match.group(2).strip()
                title = re.sub(r'\d{1,3}$', '', title).strip()
                title = re.sub(r'[.\s]+$', '', title)
                
                # Convert to title case if all caps
                if title.isupper():
                    title = title.title()
                
                section_data.append({
                    "section": section_num,
                    "title": title,
                    "start_pos": match.start()
                })
                seen.add(section_num)
    
    # Add missing sections from TOC
    toc_sections = extract_toc_sections(full_text[:50000], 358)  # First 50k chars for TOC
    for sec_num, title in toc_sections.items():
        if sec_num not in seen:
            # Find position in text
            pos_match = re.search(rf'^{sec_num}\.\s', full_text, re.MULTILINE)
            pos = pos_match.start() if pos_match else 0
            section_data.append({
                "section": sec_num,
                "title": title,
                "start_pos": pos
            })
            seen.add(sec_num)
    
    # Sort by section number
    section_data.sort(key=lambda x: x["section"])
    
    # Extract content
    sections = []
    for i, sec in enumerate(section_data):
        next_pos = section_data[i + 1]["start_pos"] if i + 1 < len(section_data) else len(full_text)
        content = full_text[sec["start_pos"]:next_pos].strip()
        
        # Remove first line (section header)
        lines = content.split('\n')
        if lines:
            content = '\n'.join(lines[1:]).strip()
        
        chapter_num, chapter_title = get_bns_chapter(sec["section"])
        
        sections.append({
            "chapter": chapter_num,
            "chapter_title": chapter_title,
            "Section": sec["section"],
            "section_title": sec["title"],
            "section_desc": content
        })
    
    return sections


def extract_bnss_sections(pdf_path: str) -> list[dict]:
    """Extract BNSS sections using TOC + content matching."""
    reader = pypdf.PdfReader(pdf_path)
    
    # Get TOC from first 20 pages
    toc_text = ""
    for i in range(min(20, len(reader.pages))):
        toc_text += reader.pages[i].extract_text() + "\n"
    
    # Get full text for content
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text = text.replace('\x00', '')
            text = re.sub(r'[^\S\n]+', ' ', text)
            full_text += text + "\n"
    
    # Extract section titles from TOC
    toc_sections = extract_toc_sections(toc_text, 533)
    print(f"   Found {len(toc_sections)} sections in TOC")
    
    # Fill in any missing sections with generic titles
    for i in range(1, 534):
        if i not in toc_sections:
            chapter_num, chapter_title = get_bnss_chapter(i)
            toc_sections[i] = f"Section {i}"
    
    # Build sections with content
    sections = []
    section_nums = sorted(toc_sections.keys())
    
    for i, sec_num in enumerate(section_nums):
        if sec_num > 533:
            continue
        next_sec = section_nums[i + 1] if i + 1 < len(section_nums) else None
        content = extract_content_for_section(full_text, sec_num, next_sec)
        
        chapter_num, chapter_title = get_bnss_chapter(sec_num)
        
        sections.append({
            "chapter": chapter_num,
            "chapter_title": chapter_title,
            "Section": sec_num,
            "section_title": toc_sections[sec_num],
            "section_desc": content if content else f"Section {sec_num} of BNSS"
        })
    
    return sections


def extract_bsa_sections(pdf_path: str) -> list[dict]:
    """Extract BSA sections using TOC + content matching."""
    reader = pypdf.PdfReader(pdf_path)
    
    # Get TOC from first 10 pages
    toc_text = ""
    for i in range(min(10, len(reader.pages))):
        toc_text += reader.pages[i].extract_text() + "\n"
    
    # Get full text for content
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text = text.replace('\x00', '')
            text = re.sub(r'[^\S\n]+', ' ', text)
            full_text += text + "\n"
    
    # Extract section titles from TOC
    toc_sections = extract_toc_sections(toc_text, 170)
    print(f"   Found {len(toc_sections)} sections in TOC")
    
    # Fill in any missing sections with generic titles
    for i in range(1, 171):
        if i not in toc_sections:
            chapter_num, chapter_title = get_bsa_chapter(i)
            toc_sections[i] = f"Section {i}"
    
    # Build sections with content
    sections = []
    section_nums = sorted(toc_sections.keys())
    
    for i, sec_num in enumerate(section_nums):
        if sec_num > 170:
            continue
        next_sec = section_nums[i + 1] if i + 1 < len(section_nums) else None
        content = extract_content_for_section(full_text, sec_num, next_sec)
        
        chapter_num, chapter_title = get_bsa_chapter(sec_num)
        
        sections.append({
            "chapter": chapter_num,
            "chapter_title": chapter_title,
            "Section": sec_num,
            "section_title": toc_sections[sec_num],
            "section_desc": content if content else f"Section {sec_num} of BSA"
        })
    
    return sections


def export_code(pdf_name: str, law_code: str, law_full_name: str, expected_sections: int):
    """Export a single code to JSON."""
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"
    pdf_path = data_dir / pdf_name
    output_path = data_dir / f"{law_code.lower()}.json"
    
    if not pdf_path.exists():
        print(f"❌ {pdf_name} not found, skipping...")
        return False
    
    print()
    print("=" * 60)
    print(f"📚 {law_full_name}")
    print("=" * 60)
    print(f"📄 Reading {pdf_path}...")
    
    # Use appropriate extractor
    if law_code == "BNS":
        sections = extract_bns_sections(str(pdf_path))
    elif law_code == "BNSS":
        sections = extract_bnss_sections(str(pdf_path))
    elif law_code == "BSA":
        sections = extract_bsa_sections(str(pdf_path))
    else:
        print(f"❌ Unknown code: {law_code}")
        return False
    
    if not sections:
        print(f"❌ No sections extracted from {pdf_name}")
        return False
    
    # Statistics
    chapters = {}
    for sec in sections:
        ch = sec["chapter"]
        if ch not in chapters:
            chapters[ch] = {"title": sec["chapter_title"], "count": 0}
        chapters[ch]["count"] += 1
    
    print()
    print("📊 Statistics:")
    print(f"   Sections: {len(sections)}/{expected_sections}")
    print(f"   Chapters: {len(chapters)}")
    
    # Save
    print(f"💾 Saving to {output_path.name}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)
    
    file_size = output_path.stat().st_size / 1024
    print(f"   File size: {file_size:.1f} KB")
    print("✅ Done!")
    
    return True


def main():
    print()
    print("=" * 60)
    print("🇮🇳 2023 Indian Criminal Codes - PDF to JSON Exporter")
    print("=" * 60)
    
    codes = [
        ("BNS.pdf", "BNS", "Bharatiya Nyaya Sanhita, 2023 (replaces IPC)", 358),
        ("BNSS.pdf", "BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023 (replaces CrPC)", 531),
        ("BSA.pdf", "BSA", "Bharatiya Sakshya Adhiniyam, 2023 (replaces IEA)", 170),
    ]
    
    success = 0
    for pdf_name, code, full_name, expected in codes:
        if export_code(pdf_name, code, full_name, expected):
            success += 1
    
    print()
    print("=" * 60)
    print(f"✅ Exported {success}/{len(codes)} codes!")
    print("=" * 60)


if __name__ == "__main__":
    main()
