"""
RAG (Retrieval-Augmented Generation) package for QADoc.
Provides document ingestion, MongoDB Atlas vector search, and LangGraph QA execution.
Framework-agnostic: Pure Python, zero UI dependencies.
"""

from qadoc.rag.config import (
    embeddings,
    llm,
    get_vector_store,
    COLLECTION_NAME,
    INDEX_NAME,
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

from qadoc.rag.tools import (
    retrieve_document_context,
)

from qadoc.rag.graph import (
    ask_question,
    agent_executor,
)

__all__ = [
    "embeddings",
    "llm",
    "get_vector_store",
    "COLLECTION_NAME",
    "INDEX_NAME",
    "ingest_documents",
    "delete_chat_embeddings",
    "retrieve_candidates",
    "rerank_documents",
    "retrieve_documents",
    "retrieve_document_context",
    "agent_executor",
    "ask_question",
]
