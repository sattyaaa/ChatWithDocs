"""
Two-Stage Document Retrieval using MongoDB Atlas Vector Search + Jina AI Reranker v2.
Stage 1: Dense Vector Similarity Search (candidate retrieval with tenant filtering).
Stage 2: Cross-Encoder Reranking (precise relevance scoring and reordering).
Traced via LangSmith with detailed timing and metadata.
Framework-agnostic: Pure Python, zero UI dependencies.
"""

import logging
import requests
from langchain_core.documents import Document
from langsmith import traceable

from qadoc.rag.config import (
    FETCH_K,
    RERANK_TOP_N,
    RERANK_MODEL,
    JINA_API_KEY,
    get_vector_store,
)
from qadoc.database.connection import documents_collection

logger = logging.getLogger(__name__)


def _build_filter(
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
) -> dict:
    """
    Builds a MongoDB Atlas Vector Search pre-filter expression.
    Filters by user_id and chat_id if documents exist in this chat,
    otherwise falls back to searching across all documents uploaded by this user.
    """
    has_chat_docs = documents_collection.find_one({"user_id": tenant, "chat_id": chat_id})
    if has_chat_docs:
        filters: dict = {
            "user_id": tenant,
            "chat_id": chat_id,
        }
    else:
        filters = {
            "user_id": tenant,
        }

    if document_ids:
        filters["document_id"] = {"$in": document_ids}

    return filters


@traceable(name="MongoDB Atlas Vector Search", run_type="retriever")
def retrieve_candidates(
    query: str,
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
    fetch_k: int = FETCH_K,
) -> list[Document]:
    """
    Stage 1: Retrieve candidate document chunks from MongoDB Atlas Vector Search.

    Args:
        query: Rephrased standalone query.
        chat_id: Active chat session ID.
        tenant: User ID for tenant isolation.
        document_ids: Optional document ID filters.
        fetch_k: Number of raw candidate chunks to retrieve.

    Returns:
        List of candidate Document objects.
    """
    vector_store = get_vector_store()

    pre_filter = _build_filter(
        chat_id=chat_id,
        tenant=tenant,
        document_ids=document_ids,
    )

    try:
        candidates = vector_store.similarity_search(
            query=query,
            k=fetch_k,
            pre_filter=pre_filter,
        )
        logger.info(
            f"Stage 1 (Atlas Vector Search): Retrieved {len(candidates)} candidates for chat '{chat_id}'"
        )
        return candidates

    except Exception as e:
        logger.exception(f"Failed to retrieve candidates from MongoDB Vector Search: {e}")
        return []


@traceable(name="Jina AI Reranker v2", run_type="tool")
def rerank_documents(
    query: str,
    documents: list[Document],
    top_n: int = RERANK_TOP_N,
) -> list[Document]:
    """
    Stage 2: Reranks candidate documents using Jina AI's cross-encoder reranker model.
    Falls back gracefully to the original document order if the API call fails.

    Args:
        query: Search query for cross-attention scoring.
        documents: Candidate Document objects from Stage 1.
        top_n: Number of final top-scoring documents to return.

    Returns:
        List of reranked Document objects with relevance scores attached to metadata.
    """
    if not documents:
        return []

    if not JINA_API_KEY:
        logger.warning("Missing JINA_API_KEY; returning un-reranked candidates.")
        return documents[:top_n]

    try:
        url = "https://api.jina.ai/v1/rerank"
        headers = {
            "Authorization": f"Bearer {JINA_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": RERANK_MODEL,
            "query": query,
            "documents": [doc.page_content for doc in documents],
            "top_n": min(top_n, len(documents)),
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result_data = response.json()

        reranked_docs: list[Document] = []
        for item in result_data.get("results", []):
            orig_idx = item["index"]
            score = item.get("relevance_score")
            doc = documents[orig_idx]
            doc.metadata["relevance_score"] = score
            reranked_docs.append(doc)

        logger.info(
            f"Stage 2 (Jina Reranker v2): Reranked {len(documents)} candidates -> top {len(reranked_docs)} chunks"
        )
        return reranked_docs

    except Exception as e:
        logger.warning(f"Jina reranker call failed, falling back to vector search rank: {e}")
        return documents[:top_n]


def retrieve_documents(
    query: str,
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
    fetch_k: int = FETCH_K,
    top_n: int = RERANK_TOP_N,
) -> list[Document]:
    """
    Combined Two-Stage Retrieval (Vector Search + Jina Reranker v2).
    """
    candidates = retrieve_candidates(
        query=query,
        chat_id=chat_id,
        tenant=tenant,
        document_ids=document_ids,
        fetch_k=fetch_k,
    )

    if not candidates:
        return []

    return rerank_documents(query=query, documents=candidates, top_n=top_n)
