"""
Application configuration and shared AI resources.

Initializes:
- Jina AI embeddings (jina-embeddings-v3)
- Groq Cloud LLM (openai/gpt-oss-20b)
- MongoDB Atlas Vector Search
Using central Pydantic settings from qadoc.config.
"""

import logging
from pydantic import SecretStr

from langchain_groq import ChatGroq
from langchain_community.embeddings import JinaEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch

from qadoc.config import settings
from qadoc.database.connection import documents_collection

logger = logging.getLogger(__name__)

# Re-export key constants for convenience
CHUNK_SIZE = settings.chunk_size
CHUNK_OVERLAP = settings.chunk_overlap
FETCH_K = settings.fetch_k
RERANK_TOP_N = settings.rerank_top_n
RERANK_MODEL = settings.jina_rerank_model
COLLECTION_NAME = settings.documents_collection_name
INDEX_NAME = settings.mongodb_vector_index
JINA_API_KEY = settings.jina_api_key

# 1. Cloud Embeddings: Jina AI (jina-embeddings-v3: 1024 dims)
embeddings = JinaEmbeddings(
    jina_api_key=settings.jina_api_key,
    model_name=settings.jina_model,
)

# 2. Groq Cloud Reasoning LLM for ReAct Agent
llm = ChatGroq(
    model=settings.groq_model,
    api_key=SecretStr(settings.groq_api_key),
    temperature=settings.llm_temperature,
)


# 3. MongoDB Atlas Vector Store Singleton
_vector_store: MongoDBAtlasVectorSearch | None = None


def get_vector_store() -> MongoDBAtlasVectorSearch:
    """
    Returns the initialized MongoDBAtlasVectorSearch instance.
    """
    global _vector_store
    if _vector_store is None:
        _vector_store = MongoDBAtlasVectorSearch(
            collection=documents_collection,
            embedding=embeddings,
            index_name=settings.mongodb_vector_index,
            text_key="text",
            embedding_key="embedding",
            relevance_score_fn="cosine",
        )
    return _vector_store
