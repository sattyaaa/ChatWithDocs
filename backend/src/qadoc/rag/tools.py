"""
LangChain tools for the QADoc ReAct Agent.
Encapsulates two-stage retrieval (MongoDB Atlas Vector Search + Jina Reranker v2).
Framework-agnostic: Pure Python, zero UI dependencies.
"""

import logging
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document

from qadoc.config import settings
from qadoc.rag.retrieval import retrieve_candidates, rerank_documents

logger = logging.getLogger(__name__)


@tool(response_format="content_and_artifact")
def retrieve_document_context(
    query: str,
    config: RunnableConfig,
) -> tuple[str, list[Document]]:
    """
    Search and retrieve relevant context from uploaded documents using two-stage retrieval:
    dense vector similarity search in MongoDB Atlas followed by Jina AI cross-encoder reranking.

    Args:
        query: Clear, standalone search query or keywords formulated to find relevant information in the documents.

    Returns:
        tuple containing:
            - content (str): Formatted context for the agent to synthesize an answer.
            - artifact (list[Document]): Original retrieved Document objects with metadata for citations.
    """
    configurable = config.get("configurable", {}) if config else {}
    chat_id = configurable.get("chat_id", "")
    tenant = configurable.get("tenant") or configurable.get("user_id", "")
    document_ids = configurable.get("document_ids")

    if not chat_id or not tenant:
        logger.warning("retrieve_document_context called without valid chat_id or tenant in config.")
        return "No documents found. Chat session or user context is missing.", []

    logger.info(f"ReAct Tool 'retrieve_document_context' called with query: '{query}'")

    # Stage 1: Dense Vector Similarity Search via Atlas
    candidates = retrieve_candidates(
        query=query,
        chat_id=chat_id,
        tenant=tenant,
        document_ids=document_ids,
        fetch_k=settings.fetch_k,
    )

    if not candidates:
        logger.info(f"Stage 1 returned 0 candidate documents for query: '{query}'")
        return "No matching documents found in the uploaded files.", []

    # Stage 2: Cross-Encoder Reranking via Jina AI
    reranked = rerank_documents(
        query=query,
        documents=candidates,
        top_n=settings.rerank_top_n,
    )

    if not reranked:
        return "No relevant sections could be matched after reranking.", []

    # Format text context for the agent
    context_parts: list[str] = []
    for i, doc in enumerate(reranked, 1):
        filename = doc.metadata.get("filename", "Unknown Document")
        page = doc.metadata.get("page")
        page_str = f"Page {page}" if page is not None else "Page N/A"
        score = doc.metadata.get("relevance_score")
        score_str = f" [Relevance: {score:.3f}]" if score is not None else ""

        context_parts.append(
            f"--- [Excerpt {i} | Source: {filename} ({page_str}){score_str}] ---\n{doc.page_content}"
        )

    formatted_context = "\n\n".join(context_parts)
    return formatted_context, reranked
