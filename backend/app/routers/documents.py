"""
Document upload and ingestion router for QADoc FastAPI backend.
"""

from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status

from app.schemas import IngestionResponse, DocumentItem, DeleteDocumentResponse
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


@router.get("/{chat_id}", response_model=List[DocumentItem])
async def get_chat_documents(
    chat_id: str,
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Retrieve the list of distinct ingested documents for a chat session.
    Falls back to user-level documents if none are specifically mapped to chat_id.
    """
    from qadoc.database.connection import documents_collection

    # 1. First check documents specifically mapped to this chat
    pipeline = [
        {"$match": {"user_id": user_id, "chat_id": chat_id}},
        {"$group": {"_id": "$filename", "chunks_count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    docs = list(documents_collection.aggregate(pipeline))

    # 2. If no docs directly in this chat, check user's overall uploaded docs
    if not docs:
        pipeline_user = [
            {"$match": {"user_id": user_id}},
            {"$group": {"_id": "$filename", "chunks_count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        docs = list(documents_collection.aggregate(pipeline_user))

    items = [
        DocumentItem(
            filename=d["_id"],
            chunks_count=d["chunks_count"],
            chat_id=chat_id,
            user_id=user_id,
        )
        for d in docs
        if d.get("_id")
    ]
    return items


@router.delete("/{chat_id}/{filename}", response_model=DeleteDocumentResponse)
async def delete_chat_document(
    chat_id: str,
    filename: str,
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Delete all vector chunks of a specific ingested document for this chat (and user).
    """
    from qadoc.database.connection import documents_collection

    # Delete chunks for this chat_id first
    filter_query = {
        "user_id": user_id,
        "chat_id": chat_id,
        "filename": filename,
    }
    result = documents_collection.delete_many(filter_query)

    deleted_count = result.deleted_count

    # If 0 deleted with chat_id filter, delete user-level chunks with this filename
    if deleted_count == 0:
        result_user = documents_collection.delete_many({
            "user_id": user_id,
            "filename": filename,
        })
        deleted_count = result_user.deleted_count

    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{filename}' not found for deletion.",
        )

    # Optional: Delete file on disk if no other chunks reference it
    upload_dir = Path(settings.upload_dir)
    file_path = upload_dir / filename
    try:
        remaining = documents_collection.count_documents({"filename": filename})
        if remaining == 0 and file_path.exists():
            file_path.unlink()
    except Exception:
        pass

    return DeleteDocumentResponse(
        filename=filename,
        deleted_chunks=deleted_count,
        message=f"Successfully deleted '{filename}' ({deleted_count} chunks removed).",
    )

