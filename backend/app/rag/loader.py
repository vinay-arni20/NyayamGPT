"""
NyayamGPT - Document Loader Module
==================================
Load and parse legal documents from various sources.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from app.core.logging import logger
from app.rag.vectorstore import DocumentMetadata


class LegalDocument:
    """
    Represents a parsed legal document.
    
    Attributes:
        law_name: Name of the law (e.g., IPC, CrPC)
        section: Section number/identifier
        title: Section title
        content: Full text content
        source_url: Official source URL
        metadata: Additional metadata
    """
    
    def __init__(
        self,
        law_name: str,
        section: str,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> None:
        self.law_name = law_name
        self.section = section
        self.title = title
        self.content = content
        self.source_url = source_url
        self.metadata = metadata or {}
    
    def to_text(self) -> str:
        """Convert to searchable text format."""
        return f"{self.law_name} Section {self.section}: {self.title}\n\n{self.content}"
    
    def to_vectorstore_metadata(self) -> DocumentMetadata:
        """Convert to vector store metadata."""
        return DocumentMetadata(
            law=self.law_name,
            section=self.section,
            title=self.title,
            source_url=self.source_url
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "law_name": self.law_name,
            "section": self.section,
            "title": self.title,
            "content": self.content,
            "source_url": self.source_url,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LegalDocument":
        """Create from dictionary."""
        return cls(
            law_name=data["law_name"],
            section=data["section"],
            title=data["title"],
            content=data["content"],
            source_url=data.get("source_url"),
            metadata=data.get("metadata")
        )


class DocumentLoader:
    """
    Load legal documents from various file formats.
    
    Supported formats:
    - JSON files with legal document structure
    - Text files with section markers
    - Markdown files
    """
    
    def __init__(self, data_directory: Optional[str] = None) -> None:
        """
        Initialize document loader.
        
        Args:
            data_directory: Directory containing legal documents
        """
        self.data_directory = data_directory or "./data/legal_docs"
    
    def load_json_file(self, file_path: str) -> list[LegalDocument]:
        """
        Load documents from a JSON file.
        
        Expected JSON structure:
        {
            "law_name": "IPC",
            "sections": [
                {
                    "section": "302",
                    "title": "Punishment for murder",
                    "content": "...",
                    "source_url": "..."
                }
            ]
        }
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            list[LegalDocument]: Parsed documents
        """
        documents = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            law_name = data.get("law_name", "Unknown")
            sections = data.get("sections", [])
            
            if isinstance(sections, list):
                for section in sections:
                    documents.append(LegalDocument(
                        law_name=law_name,
                        section=section.get("section", ""),
                        title=section.get("title", ""),
                        content=section.get("content", section.get("text", "")),
                        source_url=section.get("source_url"),
                        metadata=section.get("metadata", {})
                    ))
            
            # Handle single document format
            elif isinstance(data, dict) and "section" in data:
                documents.append(LegalDocument.from_dict(data))
            
            logger.info(
                "Loaded JSON documents",
                file=file_path,
                count=len(documents)
            )
            
        except Exception as e:
            logger.error(
                "Failed to load JSON file",
                file=file_path,
                error=str(e)
            )
        
        return documents
    
    def load_jsonl_file(self, file_path: str) -> list[LegalDocument]:
        """
        Load documents from a JSONL (JSON Lines) file.
        
        Each line is a separate JSON document.
        
        Args:
            file_path: Path to JSONL file
            
        Returns:
            list[LegalDocument]: Parsed documents
        """
        documents = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        documents.append(LegalDocument(
                            law_name=data.get("law", data.get("law_name", "Unknown")),
                            section=data.get("section", ""),
                            title=data.get("title", ""),
                            content=data.get("content", data.get("text", "")),
                            source_url=data.get("source_url"),
                            metadata=data.get("metadata", {})
                        ))
            
            logger.info(
                "Loaded JSONL documents",
                file=file_path,
                count=len(documents)
            )
            
        except Exception as e:
            logger.error(
                "Failed to load JSONL file",
                file=file_path,
                error=str(e)
            )
        
        return documents
    
    def load_text_file(
        self,
        file_path: str,
        law_name: str,
        section_pattern: str = r"Section\s+(\d+[A-Z]?)"
    ) -> list[LegalDocument]:
        """
        Load documents from a text file with section markers.
        
        Args:
            file_path: Path to text file
            law_name: Name of the law
            section_pattern: Regex pattern to identify sections
            
        Returns:
            list[LegalDocument]: Parsed documents
        """
        import re
        
        documents = []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by section pattern
            sections = re.split(f"({section_pattern})", content, flags=re.IGNORECASE)
            
            current_section = None
            current_content = []
            
            for part in sections:
                match = re.match(section_pattern, part, re.IGNORECASE)
                if match:
                    # Save previous section
                    if current_section:
                        documents.append(LegalDocument(
                            law_name=law_name,
                            section=current_section,
                            title="",  # Extract from content if possible
                            content="\n".join(current_content).strip()
                        ))
                    
                    current_section = match.group(1)
                    current_content = []
                else:
                    current_content.append(part)
            
            # Save last section
            if current_section:
                documents.append(LegalDocument(
                    law_name=law_name,
                    section=current_section,
                    title="",
                    content="\n".join(current_content).strip()
                ))
            
            logger.info(
                "Loaded text documents",
                file=file_path,
                count=len(documents)
            )
            
        except Exception as e:
            logger.error(
                "Failed to load text file",
                file=file_path,
                error=str(e)
            )
        
        return documents

    def load_pdf_file(self, file_path: str, law_name: str = "") -> list[LegalDocument]:
        """
        Load documents from a PDF file with optimized parsing for Indian legal texts.
        
        Specifically optimized for:
        - Bharatiya Nyaya Sanhita (BNS)
        - Bharatiya Nagarik Suraksha Sanhita (BNSS)
        - Bharatiya Sakshya Adhiniyam (BSA)
        - Other Indian legal acts in standard format
        
        Args:
            file_path: Path to PDF file
            law_name: Name of the law (optional, inferred from filename if empty)
            
        Returns:
            list[LegalDocument]: Parsed documents matching JSON structure
        """
        import pypdf
        import re
        
        documents = []
        if not law_name:
            law_name = Path(file_path).stem.upper()
        
        # Law name mappings for official names
        law_full_names = {
            "BNS": "Bharatiya Nyaya Sanhita",
            "BNSS": "Bharatiya Nagarik Suraksha Sanhita",
            "BSA": "Bharatiya Sakshya Adhiniyam",
        }
        
        # Base URLs for new codes
        base_urls = {
            "BNS": "https://www.indiacode.nic.in/handle/123456789/20086",
            "BNSS": "https://www.indiacode.nic.in/handle/123456789/20087",
            "BSA": "https://www.indiacode.nic.in/handle/123456789/20088",
        }
        
        base_url = base_urls.get(law_name, "https://indiankanoon.org/search/")
            
        try:
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            
            # Extract text from all pages with page tracking
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
            
            # Check for empty text (scanned PDF)
            if not full_text.strip():
                logger.warning(
                    "PDF appears to be empty or scanned (no text extracted)",
                    file=file_path
                )
                return []

            # ============ BNS/BNSS/BSA SPECIFIC PARSING ============
            # These 2023 codes have format: "58. TITLE IN ALL CAPS" at start of line
            # Process line by line for accuracy
            
            section_pattern = re.compile(r'^(\d{1,3})\.\s+([A-Z][A-Z\s,\-–—\'\"()]+)')
            chapter_pattern = re.compile(r'^CHAPTER\s+([IVXLCDM]+|\d+)')
            
            current_chapter = ""
            current_chapter_title = ""
            section_data = []  # List of (section_num, title, start_pos, chapter)
            
            lines = full_text.split('\n')
            char_pos = 0
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Check for chapter
                chapter_match = chapter_pattern.match(stripped)
                if chapter_match:
                    current_chapter = chapter_match.group(1)
                    # Chapter title is often on next line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and not section_pattern.match(next_line) and len(next_line) < 100:
                            current_chapter_title = next_line
                
                # Check for section (must start line with "N. TITLE")
                section_match = section_pattern.match(stripped)
                if section_match:
                    section_num = section_match.group(1)
                    title = section_match.group(2).strip()
                    # Clean up title - remove trailing footnote numbers
                    title = re.sub(r'\d{1,3}$', '', title).strip()
                    title = re.sub(r'[.\s]+$', '', title)
                    
                    section_data.append({
                        "section": section_num,
                        "title": title,
                        "start_pos": char_pos,
                        "chapter": current_chapter,
                        "chapter_title": current_chapter_title
                    })
                
                char_pos += len(line) + 1  # +1 for newline
            
            # Now extract content for each section (from this section to next)
            for i, sec in enumerate(section_data):
                next_pos = section_data[i + 1]["start_pos"] if i + 1 < len(section_data) else len(full_text)
                content = full_text[sec["start_pos"]:next_pos].strip()
                
                # Skip duplicate sections (keep first occurrence only)
                if any(d.section == sec["section"] for d in documents):
                    continue
                
                # Generate source URL
                source_url = f"{base_url}?searchTerm=Section%20{sec['section']}"
                
                documents.append(LegalDocument(
                    law_name=law_name,
                    section=sec["section"],
                    title=sec["title"],
                    content=content,
                    source_url=source_url,
                    metadata={
                        "source_type": "pdf",
                        "chapter": sec["chapter"],
                        "chapter_title": sec["chapter_title"]
                    }
                ))

            # Fallback: If no sections found, split by paragraphs for chunking
            if not documents and full_text.strip():
                # Split into paragraph-sized chunks for better vector search
                paragraphs = re.split(r'\n\s*\n', full_text.strip())
                for idx, para in enumerate(paragraphs):
                    para = para.strip()
                    if len(para) > 50:  # Skip very short paragraphs
                        documents.append(LegalDocument(
                            law_name=law_name,
                            section=f"Para-{idx+1}",
                            title=f"{law_name} Paragraph {idx+1}",
                            content=para,
                            source_url=base_url,
                            metadata={"source_type": "pdf", "fallback": True}
                        ))
                
                logger.warning(
                    "No sections found in PDF, using paragraph-based chunking",
                    file=file_path,
                    paragraphs=len(documents)
                )
            else:
                # Count unique chapters
                chapters = set(d.metadata.get("chapter", "") for d in documents if d.metadata.get("chapter"))
                logger.info(
                    "Loaded PDF documents with section parsing",
                    file=file_path,
                    law=law_name,
                    sections_found=len(documents),
                    chapters_found=len(chapters)
                )
            
        except ImportError:
            logger.error(
                "pypdf not installed. Install with: pip install pypdf",
                file=file_path
            )
        except Exception as e:
            logger.error(
                "Failed to load PDF file",
                file=file_path,
                error=str(e),
                error_type=type(e).__name__
            )
        
        return documents

    
    def load_directory(self, directory: Optional[str] = None) -> list[LegalDocument]:
        """
        Load all documents from a directory.
        
        Args:
            directory: Directory path (uses default if not provided)
            
        Returns:
            list[LegalDocument]: All parsed documents
        """
        directory = directory or self.data_directory
        documents = []
        
        if not os.path.exists(directory):
            logger.warning("Data directory does not exist", directory=directory)
            return documents
        
        for file_path in Path(directory).rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                
                if ext == ".json":
                    documents.extend(self.load_json_file(str(file_path)))
                elif ext == ".jsonl":
                    documents.extend(self.load_jsonl_file(str(file_path)))
                elif ext == ".txt":
                    # Try to infer law name from filename
                    law_name = file_path.stem.upper()
                    documents.extend(self.load_text_file(str(file_path), law_name))
                elif ext == ".pdf":
                    # Try to infer law name from filename
                    law_name = file_path.stem.upper()
                    documents.extend(self.load_pdf_file(str(file_path), law_name))
        
        logger.info(
            "Loaded documents from directory",
            directory=directory,
            total_count=len(documents)
        )
        
        return documents


def load_legal_json_files(data_dir: str = "./data") -> list[LegalDocument]:
    """
    Load legal documents from JSON files in the data directory.
    
    Supports the format:
    [
        {
            "chapter": 1,
            "chapter_title": "...",
            "Section": 302,
            "section_title": "Punishment for murder",
            "section_desc": "..."
        },
        ...
    ]
    
    Args:
        data_dir: Directory containing JSON files
        
    Returns:
        list[LegalDocument]: All loaded documents
    """
    from pathlib import Path
    
    documents = []

    data_path = Path(data_dir)
    
    # Map filenames to law names (includes new 2023 codes)
    # Note: nia.json contains Negotiable Instruments Act, 1881 (not National Investigation Agency)
    law_name_map = {
        "ipc.json": "IPC",  # Indian Penal Code, 1860 (Sections 1-511)
        "crpc.json": "CrPC",  # Code of Criminal Procedure, 1973 (Sections 1-484)
        "cpc.json": "CPC",  # Code of Civil Procedure, 1908 (Sections 1-158)
        "hma.json": "Hindu Marriage Act",  # Hindu Marriage Act, 1955 (Sections 1-30)
        "ida.json": "Industrial Disputes Act",  # Industrial Disputes Act, 1947 (Sections 1-40, amended to 62)
        "iea.json": "Indian Evidence Act",  # Indian Evidence Act, 1872 (Sections 1-167)
        "mva.json": "Motor Vehicles Act",  # Motor Vehicles Act, 1988 (Sections 1-217)
        "nia.json": "Negotiable Instruments Act",  # Negotiable Instruments Act, 1881 (Sections 1-148)
        # New 2023 Criminal Law Codes (replace IPC, CrPC, IEA)
        "bns.json": "BNS",  # Bharatiya Nyaya Sanhita, 2023 (Sections 1-358, replaces IPC)
        "bnss.json": "BNSS",  # Bharatiya Nagarik Suraksha Sanhita, 2023 (Sections 1-531, replaces CrPC)
        "bsa.json": "BSA",  # Bharatiya Sakshya Adhiniyam, 2023 (Sections 1-170, replaces IEA)
    }
    
    # Base URLs for each act (official India Code portal)
    base_urls = {
        "IPC": "https://www.indiacode.nic.in/handle/123456789/2263",
        "CrPC": "https://www.indiacode.nic.in/handle/123456789/1611",
        "CPC": "https://www.indiacode.nic.in/handle/123456789/2191",
        "Hindu Marriage Act": "https://www.indiacode.nic.in/handle/123456789/1560",
        "Industrial Disputes Act": "https://www.indiacode.nic.in/handle/123456789/1459",
        "Indian Evidence Act": "https://www.indiacode.nic.in/handle/123456789/1364",
        "Motor Vehicles Act": "https://www.indiacode.nic.in/handle/123456789/1798",
        "Negotiable Instruments Act": "https://www.indiacode.nic.in/handle/123456789/2190",
        # New 2023 Criminal Law Codes
        "BNS": "https://www.indiacode.nic.in/handle/123456789/20086",
        "BNSS": "https://www.indiacode.nic.in/handle/123456789/20087",
        "BSA": "https://www.indiacode.nic.in/handle/123456789/20088",
    }
    
    if not data_path.exists():
        logger.warning(f"Data directory not found: {data_dir}")
        return documents
    
    for json_file in data_path.glob("*.json"):
        filename = json_file.name.lower()
        law_name = law_name_map.get(filename)
        
        if not law_name:
            # Try to infer from filename
            law_name = json_file.stem.upper()
        
        base_url = base_urls.get(law_name, "https://indiankanoon.org/search/")
        
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    # Handle malformed CSV-like JSON (e.g., hma.json)
                    # Format: {"chapter,section,section_title,section_desc": "1,1,Title,Description"}
                    if len(item) == 1 and "chapter,section,section_title,section_desc" in item:
                        csv_value = item.get("chapter,section,section_title,section_desc", "")
                        if csv_value and "," in csv_value:
                            parts = csv_value.split(",", 3)  # Split into max 4 parts
                            if len(parts) >= 4:
                                chapter = parts[0].strip()
                                section = parts[1].strip()
                                section_title = parts[2].strip()
                                section_desc = parts[3].strip().strip('"')
                                
                                if section:
                                    source_url = f"{base_url}?searchTerm=Section%20{section}"
                                    documents.append(LegalDocument(
                                        law_name=law_name,
                                        section=section,
                                        title=section_title,
                                        content=f"Chapter {chapter}\n\n{section_desc}" if chapter else section_desc,
                                        source_url=source_url,
                                        metadata={"chapter": chapter}
                                    ))
                        continue
                    
                    # Handle standard JSON format
                    # Support multiple field name variations
                    section = str(item.get("Section", item.get("section", "")))
                    section_title = item.get("section_title", item.get("title", ""))
                    section_desc = item.get("section_desc", item.get("content", item.get("description", "")))
                    chapter = item.get("chapter", item.get("Chapter", ""))
                    chapter_title = item.get("chapter_title", item.get("Chapter_title", ""))
                    
                    # Build full content with chapter context
                    content = section_desc
                    if chapter and chapter_title:
                        content = f"Chapter {chapter}: {chapter_title}\n\n{section_desc}"
                    
                    # Generate source URL
                    source_url = f"{base_url}?searchTerm=Section%20{section}"
                    
                    if section:  # Only add if section exists
                        documents.append(LegalDocument(
                            law_name=law_name,
                            section=section,
                            title=section_title,
                            content=content,
                            source_url=source_url,
                            metadata={
                                "chapter": chapter,
                                "chapter_title": chapter_title
                            }
                        ))
            
            logger.info(
                f"Loaded {law_name} from {json_file.name}",
                sections_count=len([d for d in documents if d.law_name == law_name])
            )
            
        except Exception as e:
            logger.error(f"Failed to load {json_file}: {e}")
    
    logger.info(f"Total documents loaded from JSON files: {len(documents)}")
    return documents


def get_all_legal_data(use_json_files: bool = True) -> list[LegalDocument]:
    """
    Get all legal data - from JSON files and PDFs in data directory.
    
    Loads all datasets for vector database indexing:
    - JSON files: IPC, CrPC, CPC, HMA, IDA, IEA, MVA, NIA
    - PDF files: BNS, BNSS, BSA (and any other PDFs)
    
    Args:
        use_json_files: If True, load from files in data/; 
                        if False, return empty (no hardcoded data)
        
    Returns:
        list[LegalDocument]: All legal documents ready for indexing
    """
    documents = []
    stats = {"json": 0, "pdf": 0, "by_law": {}}
    
    if not use_json_files:
        return documents
    
    # Load JSON files
    json_docs = load_legal_json_files("./data")
    documents.extend(json_docs)
    stats["json"] = len(json_docs)
    
    # Load PDF files from the data directory
    data_path = Path("./data")
    if data_path.exists():
        loader = DocumentLoader("./data")
        for pdf_file in data_path.glob("*.pdf"):
            try:
                # Infer law name from filename (e.g. "BNS.pdf" -> "BNS")
                law_name = pdf_file.stem.upper()
                pdf_docs = loader.load_pdf_file(str(pdf_file), law_name)
                documents.extend(pdf_docs)
                stats["pdf"] += len(pdf_docs)
                stats["by_law"][law_name] = len(pdf_docs)
                logger.info(
                    f"PDF loaded successfully",
                    file=pdf_file.name,
                    law=law_name,
                    sections=len(pdf_docs)
                )
            except Exception as e:
                logger.error(
                    f"Error loading PDF",
                    file=pdf_file.name,
                    error=str(e)
                )
    
    # Count documents by law for JSON
    for doc in json_docs:
        if doc.law_name not in stats["by_law"]:
            stats["by_law"][doc.law_name] = 0
        stats["by_law"][doc.law_name] += 1
    
    if documents:
        logger.info(
            "All legal data loaded for vector indexing",
            total_documents=len(documents),
            json_sections=stats["json"],
            pdf_sections=stats["pdf"],
            laws_loaded=list(stats["by_law"].keys()),
            breakdown=stats["by_law"]
        )
        return documents
    
    logger.warning("No legal documents found in data directory")
    return []

