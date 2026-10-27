"""
Document upload and ingestion router for QADoc FastAPI backend.
"""

from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status

from app.schemas import IngestionResponse
from qadoc.config import settings
from qadoc.rag.ingestion import ingest_documents

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload/{chat_id}", response_model=List[IngestionResponse])
async def upload_documents(
    chat_id: str,
    files: List[UploadFile] = File(...),
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Upload one or more documents, store on disk, and ingest into MongoDB Atlas Vector Search.
    Supported file types: .pdf, .docx, .txt, .md
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided for upload.",
        )

    # Ensure upload directory exists
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    results: List[IngestionResponse] = []

    for file in files:
        filename = file.filename or "uploaded_document"
        suffix = Path(filename).suffix.lower()

        if suffix not in (".pdf", ".docx", ".txt", ".md"):
            results.append(
                IngestionResponse(
                    filename=filename,
                    chunks_ingested=0,
                    message=f"Unsupported file format '{suffix}'. Supported: .pdf, .docx, .txt, .md",
                )
            )
            continue

        file_path = upload_dir / filename

        try:
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            # Ingest into vector store
            chunks_count = ingest_documents(
                file_paths=[file_path],
                chat_id=chat_id,
                tenant=user_id,
            )

            results.append(
                IngestionResponse(
                    filename=filename,
                    chunks_ingested=chunks_count,
                    message=f"Successfully processed and indexed into {chunks_count} chunks.",
                )
            )

        except Exception as e:
            results.append(
                IngestionResponse(
                    filename=filename,
                    chunks_ingested=0,
                    message=f"Ingestion failed: {str(e)}",
                )
            )

    return results
