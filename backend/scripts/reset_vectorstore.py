"""
NyayamGPT - Vector Store Hard Reset Script (LangChain + ChromaDB)
=================================================================
Force a complete reset of the vector database when source files change.

Problem: Deleted JSON files (ipc.json, crpc.json) still have embeddings
in the vector store, causing hallucinations.

Solution: Wipe the vector store completely and re-embed from current files.

Usage:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python scripts/reset_vectorstore.py
"""

import json
import os
import shutil
import sys
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Load .env file if it exists
from dotenv import load_dotenv
load_dotenv()

# Paths (relative to backend directory)
VECTOR_DB_PATH = "./data/vectorstore"
DATA_SOURCE_PATH = "./data"

# Embedding model - read from .env or use default
# IMPORTANT: Must match the app's embedding model in .env
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ChromaDB collection name
COLLECTION_NAME = "legal_documents"


# =============================================================================
# STEP 1: SAFETY CHECK
# =============================================================================

def check_vector_store(vector_path: Path) -> dict:
    """Check if vector store exists and get current stats."""
    print("\n" + "=" * 60)
    print("STEP 1: SAFETY CHECK")
    print("=" * 60)
    
    result = {"exists": False, "count": 0}
    
    if vector_path.exists():
        print(f"  ✓ Vector store found: {vector_path.absolute()}")
        result["exists"] = True
        
        # Try to get document count
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(vector_path))
            collection = client.get_or_create_collection(COLLECTION_NAME)
            result["count"] = collection.count()
            print(f"  ✓ Current document count: {result['count']}")
            del client  # Release lock
        except Exception as e:
            print(f"  ⚠ Could not read store: {e}")
    else:
        print(f"  ⚠ Vector store NOT found: {vector_path}")
        print("    (Will create fresh store)")
    
    return result


# =============================================================================
# STEP 2: DELETE VECTOR STORE
# =============================================================================

def delete_vector_store(vector_path: Path) -> bool:
    """Completely delete the vector store folder."""
    print("\n" + "=" * 60)
    print("STEP 2: DELETE EXISTING VECTOR STORE")
    print("=" * 60)
    
    if not vector_path.exists():
        print("  ✓ Nothing to delete (folder doesn't exist)")
        return True
    
    print(f"  Target: {vector_path.absolute()}")
    confirm = input("  ⚠ DELETE this folder? Type 'yes' to confirm: ").strip().lower()
    
    if confirm != "yes":
        print("  ✗ Aborted by user")
        return False
    
    try:
        shutil.rmtree(vector_path)
        print(f"  ✓ DELETED: {vector_path}")
        return True
    except Exception as e:
        print(f"  ✗ Failed to delete: {e}")
        return False


# =============================================================================
# STEP 3: LOAD JSON FILES
# =============================================================================

def load_json_documents(data_path: Path) -> list[dict]:
    """
    Load all JSON files from the data directory.
    
    Supports two JSON formats:
    1. Array format: [{"Section": 1, "section_title": "...", "section_desc": "..."}, ...]
    2. Object format: {"law_name": "BNS", "sections": [...]}
    """
    print("\n" + "=" * 60)
    print("STEP 3: LOAD JSON FILES")
    print("=" * 60)
    
    json_files = sorted(data_path.glob("*.json"))
    print(f"  Found {len(json_files)} JSON files:")
    
    all_documents = []
    
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Determine law name from filename (e.g., bns.json -> BNS)
            law_name = json_file.stem.upper()
            
            # Handle both array and object formats
            if isinstance(data, list):
                # Array format: [{"Section": 1, "section_title": "...", "section_desc": "..."}, ...]
                sections = data
            elif isinstance(data, dict):
                # Object format: {"law_name": "...", "sections": [...]}
                law_name = data.get("law_name", law_name)
                sections = data.get("sections", [])
            else:
                print(f"    ✗ {json_file.name}: Unknown format")
                continue
            
            for section in sections:
                # Extract section number (supports both "Section" and "section" keys)
                section_num = section.get("Section", section.get("section", ""))
                
                # Extract title (supports multiple key names)
                title = section.get("section_title", section.get("title", ""))
                
                # Extract content/description
                content = section.get("section_desc", section.get("content", section.get("text", "")))
                
                # Include chapter info if available
                chapter = section.get("chapter", "")
                chapter_title = section.get("chapter_title", "")
                
                # Build the full text for embedding
                full_text = f"{law_name} Section {section_num}"
                if title:
                    full_text += f": {title}"
                if chapter and chapter_title:
                    full_text += f"\nChapter {chapter}: {chapter_title}"
                if content:
                    full_text += f"\n\n{content}"
                
                doc = {
                    "text": full_text,
                    "metadata": {
                        "law": law_name,
                        "section": str(section_num),
                        "title": title,
                        "chapter": str(chapter),
                        "chapter_title": chapter_title,
                        "source": json_file.name
                    }
                }
                all_documents.append(doc)
            
            print(f"    ✓ {json_file.name}: {len(sections)} sections")
            
        except Exception as e:
            print(f"    ✗ {json_file.name}: Error - {e}")
    
    print(f"\n  Total documents loaded: {len(all_documents)}")
    return all_documents


# =============================================================================
# STEP 4: CREATE EMBEDDINGS & SAVE VECTOR STORE
# =============================================================================

def create_vector_store(documents: list[dict], vector_path: Path) -> int:
    """
    Create fresh ChromaDB vector store with LangChain.
    
    Uses HuggingFace embeddings (intfloat/e5-base-v2).
    NOTE: E5 models require 'passage:' prefix for documents and 'query:' prefix for queries.
    """
    print("\n" + "=" * 60)
    print("STEP 4: CREATE EMBEDDINGS & VECTOR STORE")
    print("=" * 60)
    
    if not documents:
        print("  ✗ No documents to embed!")
        return 0
    
    # Import LangChain components
    print("  Loading embedding model...")
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
    
    # Initialize embeddings with E5-specific encode kwargs
    # E5 models require 'passage:' prefix for documents
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"trust_remote_code": True},
        encode_kwargs={"normalize_embeddings": True}
    )
    print(f"  ✓ Loaded: {EMBEDDING_MODEL}")
    
    # Convert to LangChain Document format
    # E5 models require 'passage:' prefix, MiniLM models don't
    is_e5_model = "e5" in EMBEDDING_MODEL.lower()
    prefix = "passage: " if is_e5_model else ""
    
    print(f"  Converting documents{' (adding E5 passage: prefix)' if is_e5_model else ''}...")
    langchain_docs = [
        Document(
            page_content=f"{prefix}{doc['text']}",
            metadata=doc["metadata"]
        )
        for doc in documents
    ]
    
    # Create ChromaDB vector store
    print(f"  Creating ChromaDB at: {vector_path}")
    print(f"  Embedding {len(langchain_docs)} documents (this may take a few minutes)...")
    
    # Ensure directory exists
    vector_path.mkdir(parents=True, exist_ok=True)
    
    # Create vector store with all documents
    vectorstore = Chroma.from_documents(
        documents=langchain_docs,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(vector_path)
    )
    
    # Get final count
    final_count = vectorstore._collection.count()
    print(f"  ✓ Vector store created with {final_count} documents")
    
    return final_count


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the full reset pipeline."""
    print("\n" + "=" * 60)
    print("NYAYAMGPT VECTOR STORE HARD RESET")
    print("=" * 60)
    
    # Set working directory to backend
    backend_dir = Path(__file__).parent.parent
    os.chdir(backend_dir)
    print(f"Working directory: {backend_dir.absolute()}")
    
    vector_path = Path(VECTOR_DB_PATH)
    data_path = Path(DATA_SOURCE_PATH)
    
    # Step 1: Safety check
    old_stats = check_vector_store(vector_path)
    
    # Step 2: Delete
    if not delete_vector_store(vector_path):
        return 1
    
    # Step 3: Load JSON files
    documents = load_json_documents(data_path)
    if not documents:
        print("\n✗ No documents found. Aborting.")
        return 1
    
    # Step 4: Create new vector store
    new_count = create_vector_store(documents, vector_path)
    
    # Summary
    print("\n" + "=" * 60)
    print("RESET COMPLETE")
    print("=" * 60)
    print(f"  Previous count: {old_stats['count']}")
    print(f"  New count:      {new_count}")
    print(f"\n  ✓ Vector store is now clean and up-to-date!")
    print("  ✓ Restart your backend server to use the new index.")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n✗ Aborted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

