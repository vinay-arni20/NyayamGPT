"""
Export 2023 Criminal Codes (BNS, BNSS, BSA) PDFs to JSON format.

This script extracts all sections from the new 2023 Indian Criminal Codes
and saves them in a structured JSON format.

Laws covered:
- BNS: Bharatiya Nyaya Sanhita, 2023 (replaces IPC) - 358 sections
- BNSS: Bharatiya Nagarik Suraksha Sanhita, 2023 (replaces CrPC) - 531 sections  
- BSA: Bharatiya Sakshya Adhiniyam, 2023 (replaces IEA) - 170 sections

Usage:
    cd backend
    python scripts/export_all_2023_codes.py

Output:
    data/bns.json, data/bnss.json, data/bsa.json
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
    """BNS: Bharatiya Nyaya Sanhita, 2023 - 20 Chapters, 358 Sections"""
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
    """BNSS: Bharatiya Nagarik Suraksha Sanhita, 2023 - 531 Sections"""
    chapters = [
        (1, 6, 1, "Preliminary"),
        (7, 34, 2, "Constitution of Criminal Courts and Offices"),
        (35, 61, 3, "Power of Courts"),
        (62, 72, 4, "Aid and Information to the Magistrates, Police and Persons Making Arrest"),
        (73, 83, 5, "Arrest of Persons"),
        (84, 109, 6, "Processes to Compel Appearance"),
        (110, 134, 7, "Processes to Compel the Production of Things"),
        (135, 153, 8, "Security for Keeping Peace and for Good Behaviour"),
        (154, 161, 9, "Unlawful Assemblies"),
        (162, 169, 10, "Public Nuisances"),
        (170, 173, 11, "Preventive Action of Police"),
        (174, 196, 12, "Information to Police and Their Powers to Investigate"),
        (197, 209, 13, "Jurisdiction of Criminal Courts in Inquiries and Trials"),
        (210, 226, 14, "Conditions Requisite for Initiation of Proceedings"),
        (227, 243, 15, "Complaints to Magistrates"),
        (244, 253, 16, "Commencement of Proceedings before Magistrates"),
        (254, 261, 17, "Inquiry into Cases Triable by Court of Session"),
        (262, 284, 18, "Trial before a Court of Session"),
        (285, 292, 19, "Trial of Warrant-Cases by Magistrates"),
        (293, 300, 20, "Trial of Summons-Cases by Magistrates"),
        (301, 305, 21, "Summary Trials"),
        (306, 330, 22, "Judgment"),
        (331, 353, 23, "Submission of Death Sentences for Confirmation"),
        (354, 390, 24, "General Provisions as to Inquiries and Trials"),
        (391, 395, 25, "Provisions as to Accused Persons of Unsound Mind"),
        (396, 419, 26, "Provisions as to Bail and Bonds"),
        (420, 429, 27, "Special Provisions relating to Case Management"),
        (430, 435, 28, "Plea Bargaining"),
        (436, 450, 29, "Appeals"),
        (451, 458, 30, "Reference and Revision"),
        (459, 481, 31, "Execution of Sentences"),
        (482, 492, 32, "Miscellaneous"),
        (493, 500, 33, "Maintenance of Wives, Children and Parents"),
        (501, 515, 34, "Preventive Detention"),
        (516, 531, 35, "Repeal and Savings"),
    ]
    for start, end, ch, title in chapters:
        if start <= section_num <= end:
            return ch, title
    return 0, "Unknown"


def get_bsa_chapter(section_num: int) -> tuple[int, str]:
    """BSA: Bharatiya Sakshya Adhiniyam, 2023 - 170 Sections"""
    chapters = [
        (1, 4, 1, "Preliminary"),
        (5, 38, 2, "Of the Relevancy of Facts"),
        (39, 55, 3, "Of Facts which Need Not Be Proved"),
        (56, 58, 4, "Of Oral Evidence"),
        (59, 90, 5, "Of Documentary Evidence"),
        (91, 100, 6, "Of the Exclusion of Oral by Documentary Evidence"),
        (101, 108, 7, "Of the Burden of Proof"),
        (109, 117, 8, "Estoppel"),
        (118, 132, 9, "Of Witnesses"),
        (133, 144, 10, "Of the Examination of Witnesses"),
        (145, 163, 11, "Of Improper Admission and Rejection of Evidence"),
        (164, 170, 12, "Repeal and Savings"),
    ]
    for start, end, ch, title in chapters:
        if start <= section_num <= end:
            return ch, title
    return 0, "Unknown"


# ============ PDF EXTRACTION ============

def extract_sections_from_pdf(pdf_path: str, law_code: str) -> list[dict]:
    """
    Extract sections from a 2023 Criminal Code PDF.
    
    Args:
        pdf_path: Path to PDF file
        law_code: One of 'BNS', 'BNSS', 'BSA'
        
    Returns:
        List of section dictionaries
    """
    reader = pypdf.PdfReader(pdf_path)
    full_text = ""
    
    print(f"📄 Reading {pdf_path}...")
    print(f"   Total pages: {len(reader.pages)}")
    
    # Extract text from all pages
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text = text.replace('\x00', '')
            text = re.sub(r'[^\S\n]+', ' ', text)
            text = re.sub(r' ?\n ?', '\n', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            full_text += text + "\n"
    
    if not full_text.strip():
        print("   ERROR: PDF appears to be empty or scanned")
        return []
    
    # Different patterns for different codes
    if law_code == 'BSA':
        # BSA uses "1. Short title..." format (mixed case)
        section_pattern = re.compile(r'^(\d{1,3})\.\s+([A-Z][a-zA-Z,\s\-–—\'\"()]+?)(?:\.|$)', re.MULTILINE)
    else:
        # BNS/BNSS use "58. TITLE IN ALL CAPS" format
        section_pattern = re.compile(r'^(\d{1,3})\.\s+([A-Z][A-Z\s,\-–—\'\"()]+)')
    
    section_data = []
    lines = full_text.split('\n')
    char_pos = 0
    
    print("🔍 Parsing sections...")
    
    for line in lines:
        stripped = line.strip()
        section_match = section_pattern.match(stripped)
        if section_match:
            section_num = int(section_match.group(1))
            title = section_match.group(2).strip()
            title = re.sub(r'\d{1,3}$', '', title).strip()
            title = re.sub(r'[.\s]+$', '', title)
            
            # For BSA keep original case, for others use title case
            if law_code != 'BSA':
                title = title.title()
            
            section_data.append({
                "section": section_num,
                "title": title,
                "start_pos": char_pos
            })
        char_pos += len(line) + 1
    
    # Remove duplicates
    seen = set()
    unique = []
    for sec in section_data:
        if sec["section"] not in seen:
            seen.add(sec["section"])
            unique.append(sec)
    section_data = unique
    
    print(f"   Found {len(section_data)} unique sections")
    
    # Get chapter function
    get_chapter = {
        'BNS': get_bns_chapter,
        'BNSS': get_bnss_chapter,
        'BSA': get_bsa_chapter
    }.get(law_code, lambda x: (0, "Unknown"))
    
    # Extract content and build final structure
    sections = []
    for i, sec in enumerate(section_data):
        next_pos = section_data[i + 1]["start_pos"] if i + 1 < len(section_data) else len(full_text)
        content = full_text[sec["start_pos"]:next_pos].strip()
        
        content_lines = content.split('\n')
        if content_lines:
            content = '\n'.join(content_lines[1:]).strip()
        
        chapter_num, chapter_title = get_chapter(sec["section"])
        
        sections.append({
            "chapter": chapter_num,
            "chapter_title": chapter_title,
            "Section": sec["section"],
            "section_title": sec["title"],
            "section_desc": content
        })
    
    return sections


def export_pdf_to_json(pdf_name: str, law_code: str, law_full_name: str, expected_sections: int):
    """Export a single PDF to JSON."""
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
    
    sections = extract_sections_from_pdf(str(pdf_path), law_code)
    
    if not sections:
        print(f"❌ No sections extracted from {pdf_name}")
        return False
    
    # Chapter statistics
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
    
    # Save to JSON
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
        if export_pdf_to_json(pdf_name, code, full_name, expected):
            success += 1
    
    print()
    print("=" * 60)
    print(f"✅ Exported {success}/{len(codes)} codes successfully!")
    print("=" * 60)
    print()
    print("📁 Output files:")
    print("   - data/bns.json  (Bharatiya Nyaya Sanhita)")
    print("   - data/bnss.json (Bharatiya Nagarik Suraksha Sanhita)")
    print("   - data/bsa.json  (Bharatiya Sakshya Adhiniyam)")


if __name__ == "__main__":
    main()
