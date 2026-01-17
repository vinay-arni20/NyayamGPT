"""
NyayamGPT - Enhanced Vector Store Reset with Constrained RAG
=============================================================
Creates a vector store with enriched legal metadata for better
retrieval filtering and hallucination prevention.

This script:
1. Runs the data enrichment (if not already done)
2. Creates embeddings with rich metadata
3. Enables filtering by offense_nature, severity, topics, etc.

Usage:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python scripts/reset_vectorstore_enhanced.py
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import List, Dict, Any

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

VECTOR_DB_PATH = "./data/vectorstore"
DATA_SOURCE_PATH = "./data"
ENRICHED_DATA_PATH = "./data/enriched"

# Embedding model from .env
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ChromaDB collection
COLLECTION_NAME = "legal_documents"


# =============================================================================
# STEP 1: ENSURE ENRICHED DATA EXISTS
# =============================================================================

def ensure_enriched_data(data_path: Path, enriched_path: Path) -> bool:
    """Run enrichment if enriched files don't exist."""
    print("\n" + "=" * 60)
    print("STEP 1: ENSURE ENRICHED DATA EXISTS")
    print("=" * 60)
    
    enriched_files = list(enriched_path.glob("*_enriched.json"))
    
    if len(enriched_files) >= 5:  # Expect at least 5 enriched files
        print(f"  ✓ Found {len(enriched_files)} enriched files")
        return True
    
    print("  Running data enrichment script...")
    
    # Import and run enrichment
    try:
        scripts_dir = Path(__file__).parent
        sys.path.insert(0, str(scripts_dir))
        from enrich_legal_data import main as enrich_main
        enrich_main()
        print("  ✓ Data enrichment complete")
        return True
    except Exception as e:
        print(f"  ✗ Enrichment failed: {e}")
        return False


# =============================================================================
# STEP 2: LOAD ENRICHED DOCUMENTS
# =============================================================================

def load_enriched_documents(enriched_path: Path) -> List[Dict]:
    """Load enriched JSON files with full metadata."""
    print("\n" + "=" * 60)
    print("STEP 2: LOAD ENRICHED DOCUMENTS")
    print("=" * 60)
    
    all_documents = []
    enriched_files = sorted(enriched_path.glob("*_enriched.json"))
    
    print(f"  Found {len(enriched_files)} enriched files:")
    
    for json_file in enriched_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                sections = json.load(f)
            
            for section in sections:
                # Build comprehensive embedding text
                # Include metadata in text for better semantic search
                text_parts = [
                    f"{section.get('law_code', '')} Section {section.get('section_number', '')}",
                    f"Title: {section.get('section_title', '')}",
                ]
                
                if section.get('chapter_title'):
                    text_parts.append(f"Chapter: {section.get('chapter_title', '')}")
                
                # Add topic tags for semantic matching
                topics = section.get('legal_topics', [])
                if topics:
                    text_parts.append(f"Topics: {', '.join(topics)}")
                
                # Add the actual content
                content = section.get('text_content', '')
                if content:
                    text_parts.append(f"\n{content}")
                
                full_text = "\n".join(text_parts)
                
                # Build rich metadata for filtering
                metadata = {
                    # Identifiers
                    "section_id": section.get("section_id", ""),
                    "law_code": section.get("law_code", ""),
                    "section_number": section.get("section_number", ""),
                    "section_title": section.get("section_title", ""),
                    "chapter": str(section.get("chapter", "")),
                    "chapter_title": section.get("chapter_title", ""),
                    
                    # Classification (for filtering)
                    "offense_nature": section.get("offense_nature", "other"),
                    "severity_level": section.get("severity_level", "unspecified"),
                    "involves_physical_harm": section.get("involves_physical_harm", False),
                    "involves_verbal_abuse": section.get("involves_verbal_abuse", False),
                    "involves_caste_discrimination": section.get("involves_caste_discrimination", False),
                    
                    # Punishment info
                    "max_imprisonment": section.get("max_imprisonment", "") or "",
                    "community_service": section.get("community_service", False),
                    
                    # Topics (stored as JSON string for ChromaDB)
                    "legal_topics": json.dumps(section.get("legal_topics", [])),
                    "keywords": json.dumps(section.get("keywords", [])),
                    
                    # Cross-references
                    "ipc_mapping": section.get("ipc_mapping", "") or "",
                    
                    # Source
                    "source": json_file.name
                }
                
                all_documents.append({
                    "text": full_text,
                    "metadata": metadata
                })
            
            print(f"    ✓ {json_file.name}: {len(sections)} sections")
            
        except Exception as e:
            print(f"    ✗ {json_file.name}: Error - {e}")
    
    print(f"\n  Total documents: {len(all_documents)}")
    return all_documents


# =============================================================================
# STEP 3: DELETE OLD VECTOR STORE
# =============================================================================

def delete_vector_store(vector_path: Path, auto_confirm: bool = False) -> bool:
    """Delete the vector store folder."""
    print("\n" + "=" * 60)
    print("STEP 3: DELETE EXISTING VECTOR STORE")
    print("=" * 60)
    
    if not vector_path.exists():
        print("  ✓ Nothing to delete")
        return True
    
    print(f"  Target: {vector_path.absolute()}")
    
    if not auto_confirm:
        confirm = input("  ⚠ DELETE this folder? Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            print("  ✗ Aborted by user")
            return False
    else:
        print("  Auto-confirmed deletion")
    
    try:
        shutil.rmtree(vector_path)
        print(f"  ✓ DELETED: {vector_path}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to delete: {e}")
        return False


# =============================================================================
# STEP 4: CREATE ENHANCED VECTOR STORE
# =============================================================================

def create_enhanced_vector_store(documents: List[Dict], vector_path: Path) -> int:
    """Create vector store with rich metadata for constrained retrieval."""
    print("\n" + "=" * 60)
    print("STEP 4: CREATE ENHANCED VECTOR STORE")
    print("=" * 60)
    
    if not documents:
        print("  ✗ No documents to embed!")
        return 0
    
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    
    # Initialize embeddings
    print(f"  Loading embedding model: {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True}
    )
    print(f"  ✓ Loaded: {EMBEDDING_MODEL}")
    
    # E5 models need prefix
    is_e5_model = "e5" in EMBEDDING_MODEL.lower()
    prefix = "passage: " if is_e5_model else ""
    
    print(f"  Converting {len(documents)} documents...")
    langchain_docs = [
        Document(
            page_content=f"{prefix}{doc['text']}",
            metadata=doc["metadata"]
        )
        for doc in documents
    ]
    
    # Create vector store
    print(f"  Creating ChromaDB at: {vector_path}")
    print(f"  Embedding {len(langchain_docs)} documents...")
    
    vector_path.mkdir(parents=True, exist_ok=True)
    
    vectorstore = Chroma.from_documents(
        documents=langchain_docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(vector_path)
    )
    
    final_count = vectorstore._collection.count()
    print(f"  ✓ Vector store created with {final_count} documents")
    
    # Print metadata statistics
    print_metadata_stats(documents)
    
    return final_count


def print_metadata_stats(documents: List[Dict]):
    """Print statistics about the indexed metadata."""
    print("\n  📊 Metadata Statistics:")
    
    offense_counts = {}
    severity_counts = {}
    physical_count = 0
    verbal_count = 0
    caste_count = 0
    
    for doc in documents:
        meta = doc["metadata"]
        
        nature = meta.get("offense_nature", "other")
        offense_counts[nature] = offense_counts.get(nature, 0) + 1
        
        severity = meta.get("severity_level", "unspecified")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        if meta.get("involves_physical_harm"):
            physical_count += 1
        if meta.get("involves_verbal_abuse"):
            verbal_count += 1
        if meta.get("involves_caste_discrimination"):
            caste_count += 1
    
    print(f"     Offense Natures: {offense_counts}")
    print(f"     Severity Levels: {severity_counts}")
    print(f"     Physical Harm Sections: {physical_count}")
    print(f"     Verbal Abuse Sections: {verbal_count}")
    print(f"     Caste Discrimination Sections: {caste_count}")


# =============================================================================
# MAIN
# =============================================================================

def main(auto_confirm: bool = False):
    """Run the enhanced reset pipeline."""
    print("\n" + "=" * 60)
    print("NYAYAMGPT ENHANCED VECTOR STORE RESET")
    print("(Constrained RAG with Legal Metadata)")
    print("=" * 60)
    
    # Set working directory
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    print(f"Working directory: {backend_dir.absolute()}")
    
    vector_path = Path(VECTOR_DB_PATH)
    data_path = Path(DATA_SOURCE_PATH)
    enriched_path = Path(ENRICHED_DATA_PATH)
    
    # Step 1: Ensure enriched data
    if not ensure_enriched_data(data_path, enriched_path):
        print("\n✗ Failed to prepare enriched data. Aborting.")
        return 1
    
    # Step 2: Load enriched documents
    documents = load_enriched_documents(enriched_path)
    if not documents:
        print("\n✗ No documents found. Aborting.")
        return 1
    
    # Step 3: Delete old vector store
    if not delete_vector_store(vector_path, auto_confirm):
        return 1
    
    # Step 4: Create enhanced vector store
    new_count = create_enhanced_vector_store(documents, vector_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("ENHANCED RESET COMPLETE")
    print("=" * 60)
    print(f"  Documents indexed: {new_count}")
    print(f"  Metadata fields available for filtering:")
    print(f"    - offense_nature (verbal, physical, property, etc.)")
    print(f"    - severity_level (low, medium, high, capital)")
    print(f"    - involves_physical_harm (true/false)")
    print(f"    - involves_caste_discrimination (true/false)")
    print(f"\n  ✓ Constrained RAG ready!")
    print(f"  ✓ Restart your backend server to use the new index.")
    
    return 0


if __name__ == "__main__":
    # Check for auto-confirm flag
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv
    
    try:
        sys.exit(main(auto_confirm))
    except KeyboardInterrupt:
        print("\n\n✗ Aborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
