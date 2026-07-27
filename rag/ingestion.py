"""
Document ingestion pipeline

Pipeline Steps: 
 - Upload Files
 - Load Documents
 - Split Documents
 - Add Metadata
 - Store in weaviate

 """

from pathlib import Path
from uuid import uuid4
import logging
logger = logging.getLogger(__name__)

from langchain_core.documents import Document

from rag.config import get_vector_store

from langchain_community.document_loaders import (
    PyMuPDFLoader,
    Docx2txtLoader,
    TextLoader,
)


from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def _load_documents(file_path: Path) -> list[Document]:
    """Loads a single document from disk
    
    Supported file formats:
        - PDF (.pdf)
        - Microsoft Word (.docx)
        - Plain text (.txt)
        - Markdown (.md)

    Args:
        file_path_str: Path of the document.

    Returns:
        A list of Langchain Document objects.

    Raises:
        FileNotFoundError:
            If the specifies file does not exist.
        
        ValueError:
            If the file extension is not supported.
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
            f"Unsupported file type '{suffix}'.\nSupported types are: .pdf, .docx, .txt, .md"
        )

    return loader.load()
    


def _split_documents(documents: list[Document]) ->list[Document]:
    """Splits documents into smaller chunks for efficient retrieval.

    Args:
        documents: List of Langchain Document objects to split.

    Returns:
        list[Document]: List of split document chunks.
    """
    if not documents:
        raise ValueError("No documents were provides for splitting.")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        add_start_index=True,
    )

    return splitter.split_documents(documents)



import re


def _sanitize_metadata(metadata):
    """
    Sanitizes metadata dictionary for Weaviate compatibility.
    - Only retains relevant metadata keys (like 'page') to prevent schema pollution
      and database insertion failures on unexpected types (like invalid dates).
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
    document_id: str,
    filename: str,
) -> list[Document]:
    """
    Attach metadata to every document chunk.

    Args:
        chunks: List of chunked Document objects.
        chat_id: Unique identifier of the current chat.
        document_id: Unique identifier of the uploaded document.
        filename: Original document filename

    Returns:
        The updated list of Document chunks.
    """

    for chunk_id, chunk in enumerate(chunks):
        cleaned_meta = _sanitize_metadata(chunk.metadata)
        cleaned_meta.update(
            {
                "chat_id": chat_id,
                "document_id": document_id,
                "filename": filename,
                "chunk_id": str(chunk_id),
                "source": filename,
            }
        )
        chunk.metadata = cleaned_meta

    return chunks




def ingest_documents(file_paths: list[Path], chat_id: str) ->int:
    """
    Ingest one or more documents into the Weaviate vector store.


    Args:
        file_paths: Paths to the documents to be ingested.
        chat_id: Unique identifier for the current chat session.

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
                document_id=document_id,
                filename=file_path.name,
            )
            _ = vector_store.add_documents(chunks_with_meta)
            total_chunks += len(chunks_with_meta)

            logger.info(
                "Succesfully ingested '%s' ('%d chunks')",
                file_path.name,
                len(chunks_with_meta),
            )

        except Exception as e:
            logger.error(
                f"Failed to ingest '{file_path.name}'"
            )
            continue

    return total_chunks


def delete_chat_embeddings(chat_id: str) -> None:
    """
    Delete all vector embeddings associated with a specific chat_id.
    """
    from weaviate.classes.query import Filter
    from rag.config import get_client, COLLECTION_NAME

    try:
        client = get_client()
        collection = client.collections.get(COLLECTION_NAME)
        response = collection.data.delete_many(
            where=Filter.by_property("chat_id").equal(chat_id)
        )
        logger.info(
            f"Deleted embeddings for chat_id '{chat_id}': "
            f"{response.successful} successful, {response.failed} failed."
        )
    except Exception as e:
        logger.error(f"Failed to delete embeddings for chat_id '{chat_id}': {e}")
