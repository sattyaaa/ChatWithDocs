"""
RAG (Retrieval-Augmented Generation) package for QADoc.
Provides document ingestion, MongoDB Atlas vector search, and LangGraph QA execution.
Framework-agnostic: Pure Python, zero UI dependencies.
"""

from qadoc.rag.config import (
    embeddings,
    llm,
    rephrase_llm,
    get_vector_store,
    COLLECTION_NAME,
    INDEX_NAME,
    TOP_K,
)

from qadoc.rag.ingestion import (
    ingest_documents,
    delete_chat_embeddings,
)

from qadoc.rag.retrieval import (
    retrieve_candidates,
    rerank_documents,
    retrieve_documents,
)

from qadoc.rag.graph import (
    ask_question,
)

__all__ = [
    "embeddings",
    "llm",
    "rephrase_llm",
    "get_vector_store",
    "COLLECTION_NAME",
    "INDEX_NAME",
    "TOP_K",
    "ingest_documents",
    "delete_chat_embeddings",
    "retrieve_candidates",
    "rerank_documents",
    "retrieve_documents",
    "ask_question",
]
