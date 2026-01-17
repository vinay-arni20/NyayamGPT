"""
NyayamGPT - Document Management Routes
======================================
API endpoints for uploading and managing legal documents.
"""

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.rag.loader import DocumentLoader
from app.rag.indexing import get_indexing_service

router = APIRouter()

# Directory to store uploaded files
UPLOAD_DIR = Path("data")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def process_and_index_file(file_path: str, law_name: str):
    """
    Background task to process and index a file.
    """
    try:
        logger.info(f"Starting background indexing for {file_path}")
        
        loader = DocumentLoader()
        indexing_service = get_indexing_service()
        
        # Load documents based on extension
        documents = []
        ext = Path(file_path).suffix.lower()
        
        if ext == ".pdf":
            documents = loader.load_pdf_file(file_path, law_name)
        elif ext == ".json":
            documents = loader.load_json_file(file_path)
        elif ext == ".txt":
            documents = loader.load_text_file(file_path, law_name)
            
        if documents:
            # Index and store
            chunks, docs = await indexing_service.index_and_store(documents)
            logger.info(
                "Background indexing completed",
                file=file_path,
                chunks=chunks,
                docs=docs
            )
        else:
            logger.warning(f"No documents extracted from {file_path}")
            
    except Exception as e:
        logger.error(f"Background indexing failed for {file_path}: {e}")


@router.post("/upload", response_model=dict)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    law_name: str = None
):
    """
    Upload a legal document (PDF, JSON, TXT) and trigger indexing.
    
    - **file**: The file to upload
    - **law_name**: Optional name of the law (e.g., "BNS", "IPC"). If not provided, inferred from filename.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in [".pdf", ".json", ".txt", ".jsonl"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type: {ext}. Supported: .pdf, .json, .txt"
        )
    
    try:
        # Save file
        file_path = UPLOAD_DIR / file.filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File uploaded successfully: {file_path}")
        
        # Determine law name
        if not law_name:
            law_name = Path(file.filename).stem.upper()
            
        # Trigger background indexing
        background_tasks.add_task(process_and_index_file, str(file_path), law_name)
        
        return {
            "message": "File uploaded successfully. Indexing started in background.",
            "filename": file.filename,
            "law_name": law_name
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
