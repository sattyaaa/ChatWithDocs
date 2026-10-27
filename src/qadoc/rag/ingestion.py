"""
Document ingestion pipeline for QADoc.

Pipeline Steps:
 1. Load documents from disk (.pdf, .docx, .txt, .md)
 2. Split documents into character chunks
 3. Attach metadata (user_id/tenant, chat_id, document_id, filename, page)
 4. Store embedded chunks into MongoDB Atlas Vector Search
 5. Purge chunks on chat deletion
Framework-agnostic: Pure Python, zero UI dependencies.
"""

from pathlib import Path
from uuid import uuid4
import logging

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from qadoc.rag.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    get_vector_store,
)
from qadoc.database.connection import documents_collection

logger = logging.getLogger(__name__)


def _load_documents(file_path: Path) -> list[Document]:
    """
    Loads a single document from disk.

    Supported file formats:
        - PDF (.pdf)
        - Microsoft Word (.docx)
        - Plain text (.txt)
        - Markdown (.md)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        loader = PyMuPDFLoader(str(file_path))
    elif suffix == ".docx":
        loader = Docx2txtLoader(str(file_path))
    elif suffix in (".txt", ".md"):
        loader = TextLoader(str(file_path), encoding="utf-8")
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported types are: .pdf, .docx, .txt, .md"
        )

    return loader.load()


def _split_documents(documents: list[Document]) -> list[Document]:
    """
    Splits documents into smaller chunks for efficient retrieval.
    """
    if not documents:
        raise ValueError("No documents were provided for splitting.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )

    return splitter.split_documents(documents)


def _sanitize_metadata(metadata: dict) -> dict:
    """
    Sanitizes metadata dictionary to retain relevant fields.
    """
    clean_meta = {}
    if "page" in metadata:
        try:
            clean_meta["page"] = int(metadata["page"])
        except (ValueError, TypeError):
            pass
    return clean_meta


def _add_metadata(
    chunks: list[Document],
    chat_id: str,
    tenant: str,
    document_id: str,
    filename: str,
) -> list[Document]:
    """
    Attach user, chat, document, and chunk metadata to each document chunk.
    """
    for chunk_id, chunk in enumerate(chunks):
        cleaned_meta = _sanitize_metadata(chunk.metadata)
        cleaned_meta.update(
            {
                "user_id": tenant,
                "chat_id": chat_id,
                "document_id": document_id,
                "filename": filename,
                "chunk_id": str(chunk_id),
                "source": filename,
            }
        )
        chunk.metadata = cleaned_meta

    return chunks


def ingest_documents(file_paths: list[Path], chat_id: str, tenant: str) -> int:
    """
    Ingest one or more documents into the MongoDB Atlas vector store.

    Args:
        file_paths: Paths to the documents to be ingested.
        chat_id: Unique identifier for the current chat session.
        tenant: Unique identifier of the user (user_id).

    Returns:
        The total number of document chunks successfully stored.
    """
    vector_store = get_vector_store()
    total_chunks = 0

    for file_path in file_paths:
        try:
            document_id = str(uuid4())

            documents = _load_documents(file_path)
            chunks = _split_documents(documents)

            chunks_with_meta = _add_metadata(
                chunks=chunks,
                chat_id=chat_id,
                tenant=tenant,
                document_id=document_id,
                filename=file_path.name,
            )

            # Insert documents and auto-compute embeddings via Voyage AI
            vector_store.add_documents(chunks_with_meta)
            total_chunks += len(chunks_with_meta)

            logger.info(
                "Successfully ingested '%s' (%d chunks) into MongoDB Atlas",
                file_path.name,
                len(chunks_with_meta),
            )

        except Exception as e:
            logger.error(f"Failed to ingest '{file_path.name}': {e}", exc_info=True)
            continue

    return total_chunks


def delete_chat_embeddings(chat_id: str, tenant: str) -> None:
    """
    Delete all vector embeddings associated with a specific chat_id under a user.
    """
    try:
        result = documents_collection.delete_many({
            "user_id": tenant,
            "chat_id": chat_id,
        })
        logger.info(
            f"Deleted {result.deleted_count} vector documents for chat '{chat_id}' under user '{tenant}'"
        )
    except Exception as e:
        logger.error(
            f"Failed to delete embeddings for chat_id '{chat_id}' under user '{tenant}': {e}"
        )
