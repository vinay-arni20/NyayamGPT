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
        
        logger.info(
            "Loaded documents from directory",
            directory=directory,
            total_count=len(documents)
        )
        
        return documents


# Sample data generator for testing
def generate_sample_ipc_data() -> list[LegalDocument]:
    """
    Generate sample IPC (Indian Penal Code) data for testing.
    
    Returns:
        list[LegalDocument]: Sample IPC sections
    """
    sample_sections = [
        {
            "section": "302",
            "title": "Punishment for murder",
            "content": """Whoever commits murder shall be punished with death, or imprisonment for life, and shall also be liable to fine.

This section prescribes the punishment for the offence of murder as defined under Section 300. The punishment under this section is:
1. Death penalty, or
2. Imprisonment for life, and
3. Fine (mandatory in both cases)

The court has discretion to choose between death penalty and life imprisonment based on the facts and circumstances of each case. The Supreme Court has laid down that death penalty should be imposed only in the "rarest of rare cases.""",
            "source_url": "https://indiankanoon.org/doc/1560742/"
        },
        {
            "section": "304",
            "title": "Punishment for culpable homicide not amounting to murder",
            "content": """Whoever commits culpable homicide not amounting to murder shall be punished:

Part I: If the act by which the death is caused is done with the intention of causing death, or of causing such bodily injury as is likely to cause death - with imprisonment for life, or imprisonment of either description for a term which may extend to ten years, and shall also be liable to fine.

Part II: If the act is done with the knowledge that it is likely to cause death, but without any intention to cause death, or to cause such bodily injury as is likely to cause death - with imprisonment of either description for a term which may extend to ten years, or with fine, or with both.""",
            "source_url": "https://indiankanoon.org/doc/409589/"
        },
        {
            "section": "307",
            "title": "Attempt to murder",
            "content": """Whoever does any act with such intention or knowledge, and under such circumstances that, if he by that act caused death, he would be guilty of murder, shall be punished with imprisonment of either description for a term which may extend to ten years, and shall also be liable to fine.

If hurt is caused to any person by such act, the offender shall be liable either to imprisonment for life, or to such punishment as is hereinbefore mentioned.

When any person offending under this section is under sentence of imprisonment for life, he may, if hurt is caused, be punished with death.

Essential ingredients:
1. There must be an act done with intention or knowledge
2. The act must be done under circumstances that if death had been caused, it would amount to murder
3. Death should not have been caused""",
            "source_url": "https://indiankanoon.org/doc/455468/"
        },
        {
            "section": "376",
            "title": "Punishment for rape",
            "content": """Whoever commits rape shall be punished with rigorous imprisonment of either description for a term which shall not be less than ten years, but which may extend to imprisonment for life, and shall also be liable to fine.

The punishment has been enhanced by the Criminal Law (Amendment) Act, 2013 following the Nirbhaya case. The minimum punishment is now 10 years (increased from 7 years).

Aggravated forms of rape under Section 376(2) carry higher punishments:
- Rape by police officer
- Rape by public servant
- Rape during communal violence
- Rape of pregnant woman
- Gang rape
These may be punished with rigorous imprisonment for not less than 20 years extending to life imprisonment or death.""",
            "source_url": "https://indiankanoon.org/doc/1279834/"
        },
        {
            "section": "420",
            "title": "Cheating and dishonestly inducing delivery of property",
            "content": """Whoever cheats and thereby dishonestly induces the person deceived to deliver any property to any person, or to make, alter or destroy the whole or any part of a valuable security, or anything which is signed or sealed, and which is capable of being converted into a valuable security, shall be punished with imprisonment of either description for a term which may extend to seven years, and shall also be liable to fine.

Essential ingredients:
1. Cheating as defined under Section 415
2. Dishonest inducement to deliver property
3. Or to make/alter/destroy valuable security

This is a cognizable, non-bailable, and compoundable offence. It is triable by a Magistrate of the First Class.""",
            "source_url": "https://indiankanoon.org/doc/1306824/"
        },
        {
            "section": "498A",
            "title": "Husband or relative of husband of a woman subjecting her to cruelty",
            "content": """Whoever, being the husband or the relative of the husband of a woman, subjects such woman to cruelty shall be punished with imprisonment for a term which may extend to three years and shall also be liable to fine.

Explanation - For the purpose of this section, "cruelty" means:
(a) any wilful conduct which is of such a nature as is likely to drive the woman to commit suicide or to cause grave injury or danger to life, limb or health (whether mental or physical) of the woman; or
(b) harassment of the woman where such harassment is with a view to coercing her or any person related to her to meet any unlawful demand for any property or valuable security or is on account of failure by her or any person related to her to meet such demand.

This is a cognizable and non-bailable offence. The offence is non-compoundable.""",
            "source_url": "https://indiankanoon.org/doc/538436/"
        }
    ]
    
    return [
        LegalDocument(
            law_name="IPC",
            section=s["section"],
            title=s["title"],
            content=s["content"],
            source_url=s["source_url"]
        )
        for s in sample_sections
    ]


def generate_sample_crpc_data() -> list[LegalDocument]:
    """
    Generate sample CrPC (Code of Criminal Procedure) data for testing.
    
    Returns:
        list[LegalDocument]: Sample CrPC sections
    """
    sample_sections = [
        {
            "section": "41",
            "title": "When police may arrest without warrant",
            "content": """Any police officer may without an order from a Magistrate and without a warrant, arrest any person:

(a) who commits, in the presence of a police officer, a cognizable offence;
(b) against whom a reasonable complaint has been made, or credible information has been received, or a reasonable suspicion exists that he has committed a cognizable offence punishable with imprisonment for a term which may be less than seven years or which may extend to seven years whether with or without fine, if the following conditions are satisfied:
    (i) the police officer has reason to believe that such person has committed the said offence;
    (ii) the police officer is satisfied that such arrest is necessary to prevent such person from committing any further offence; or for proper investigation of the offence; or to prevent tampering with evidence; or to prevent the person from making any inducement, threat or promise to any person acquainted with the facts of the case.

The 2009 amendment introduced safeguards against arbitrary arrests.""",
            "source_url": "https://indiankanoon.org/doc/1722440/"
        },
        {
            "section": "154",
            "title": "Information in cognizable cases (FIR)",
            "content": """Every information relating to the commission of a cognizable offence, if given orally to an officer in charge of a police station, shall be reduced to writing by him or under his direction, and be read over to the informant; and every such information, whether given in writing or reduced to writing as aforesaid, shall be signed by the person giving it, and the substance thereof shall be entered in a book to be kept by such officer in such form as the State Government may prescribe in this behalf.

A copy of the information as recorded shall be given forthwith, free of cost, to the informant.

Key points:
1. FIR must be registered for cognizable offences
2. It should be in writing
3. Must be signed by the informant
4. Free copy must be provided to informant
5. Police cannot refuse to register FIR for cognizable offence""",
            "source_url": "https://indiankanoon.org/doc/1156070/"
        },
        {
            "section": "161",
            "title": "Examination of witnesses by police",
            "content": """Any police officer making an investigation under this Chapter, or any police officer not below such rank as the State Government may, by general or special order, prescribe in this behalf, acting on the requisition of such officer, may examine orally any person supposed to be acquainted with the facts and circumstances of the case.

Such person shall be bound to answer truly all questions relating to such case put to him by such officer, other than questions the answers to which would have a tendency to expose him to a criminal charge or to a penalty or forfeiture.

The police officer may reduce into writing any statement made to him in the course of an examination under this section.

Note: Statements made to police are not admissible as evidence under Section 162, except for contradiction purposes.""",
            "source_url": "https://indiankanoon.org/doc/447673/"
        },
        {
            "section": "437",
            "title": "When bail may be taken in case of non-bailable offence",
            "content": """When any person accused of, or suspected of, the commission of any non-bailable offence is arrested or detained without warrant by an officer in charge of a police station or appears or is brought before a Court other than the High Court or Court of Session, he may be released on bail:

Provided that such person shall not be so released if there appear reasonable grounds for believing that he has been guilty of an offence punishable with death or imprisonment for life.

Proviso further provides certain exceptions where bail may be granted:
1. Person is under sixteen years of age
2. Person is a woman
3. Person is sick or infirm

The court shall impose conditions it considers necessary to ensure the accused's appearance and to prevent tampering with evidence.""",
            "source_url": "https://indiankanoon.org/doc/1704163/"
        }
    ]
    
    return [
        LegalDocument(
            law_name="CrPC",
            section=s["section"],
            title=s["title"],
            content=s["content"],
            source_url=s["source_url"]
        )
        for s in sample_sections
    ]


def get_all_sample_data() -> list[LegalDocument]:
    """
    Get all sample legal data.
    
    Returns:
        list[LegalDocument]: All sample documents
    """
    documents = []
    documents.extend(generate_sample_ipc_data())
    documents.extend(generate_sample_crpc_data())
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
    
    # Map filenames to law names
    law_name_map = {
        "ipc.json": "IPC",
        "crpc.json": "CrPC", 
        "cpc.json": "CPC",
        "hma.json": "Hindu Marriage Act",
        "ida.json": "Industrial Disputes Act",
        "iea.json": "Indian Evidence Act",
        "mva.json": "Motor Vehicles Act",
        "nia.json": "NIA Act",
    }
    
    # Base URLs for each act
    base_urls = {
        "IPC": "https://www.indiacode.nic.in/handle/123456789/2263",
        "CrPC": "https://www.indiacode.nic.in/handle/123456789/1611",
        "CPC": "https://www.indiacode.nic.in/handle/123456789/2191",
        "Hindu Marriage Act": "https://www.indiacode.nic.in/handle/123456789/1560",
        "Industrial Disputes Act": "https://www.indiacode.nic.in/handle/123456789/1459",
        "Indian Evidence Act": "https://www.indiacode.nic.in/handle/123456789/1364",
        "Motor Vehicles Act": "https://www.indiacode.nic.in/handle/123456789/1798",
        "NIA Act": "https://www.indiacode.nic.in/handle/123456789/2037",
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
    Get all legal data - either from JSON files or sample data.
    
    Args:
        use_json_files: If True, load from JSON files in data/; 
                        if False, use hardcoded sample data
        
    Returns:
        list[LegalDocument]: All legal documents
    """
    if use_json_files:
        documents = load_legal_json_files("./data")
        if documents:
            return documents
        logger.warning("No JSON files found, falling back to sample data")
    
    return get_all_sample_data()
