"""
Central Application Configuration for QADoc.
Uses Pydantic Settings to load and validate all settings from environment variables (.env).
Controls database, LLM, embedding, retrieval, reranking, and observability.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration schema for QADoc.
    Loads from .env file or system environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ==========================================
    # 1. MongoDB Database Settings
    # ==========================================
    mongodb_uri: str = Field(
        ...,
        validation_alias=AliasChoices("MONGODB_URI", "mongodb_uri"),
        description="MongoDB Atlas connection URI",
    )
    mongodb_db_name: str = Field(
        "docqa_chat",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "mongodb_db_name"),
        description="Target MongoDB database name",
    )
    mongodb_server_timeout_ms: int = Field(
        5000,
        description="Server selection and connection timeout in milliseconds",
    )

    # Collections
    users_collection_name: str = Field("users", description="Collection storing user credentials")
    chats_collection_name: str = Field("chats", description="Collection storing chat sessions")
    messages_collection_name: str = Field("messages", description="Collection storing messages")
    documents_collection_name: str = Field(
        "documents",
        validation_alias=AliasChoices("COLLECTION_NAME", "documents_collection_name"),
        description="Collection storing document vector chunks",
    )

    # Atlas Vector Search Index Name
    mongodb_vector_index: str = Field(
        "doc_index",
        validation_alias=AliasChoices("MONGODB_VECTOR_INDEX", "INDEX_NAME", "mongodb_vector_index"),
        description="Atlas Vector Search index name defined in MongoDB Atlas",
    )

    # ==========================================
    # 2. Groq Cloud LLM Settings
    # ==========================================
    groq_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("GROQ_API_KEY", "groq_api_key"),
        description="Groq API key for LPU inference",
    )
    groq_model: str = Field(
        "openai/gpt-oss-120b",
        validation_alias=AliasChoices("GROQ_MODEL", "groq_model"),
        description="Primary LLM for QA answer generation",
    )
    groq_rephrase_model: str = Field(
        "openai/gpt-oss-20b",
        validation_alias=AliasChoices("GROQ_REPHRASE_MODEL", "groq_rephrase_model"),
        description="LLM used for condensing conversation turns into standalone search queries",
    )
    llm_temperature: float = Field(0.2, description="Temperature for final answer generation")
    rephrase_temperature: float = Field(0.1, description="Temperature for query rephrasing")

    # ==========================================
    # 3. Jina AI (Embeddings & Reranker)
    # ==========================================
    jina_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("JINA_API_KEY", "jinaapikey", "jina_api_key"),
        description="Jina AI API key",
    )
    jina_model: str = Field(
        "jina-embeddings-v3",
        validation_alias=AliasChoices("JINA_MODEL", "jina_model"),
        description="Jina AI embedding model (1024 output dimensions)",
    )
    jina_rerank_model: str = Field(
        "jina-reranker-v2-base-multilingual",
        validation_alias=AliasChoices("JINA_RERANK_MODEL", "jina_rerank_model"),
        description="Jina AI cross-encoder reranker model",
    )
    jina_rerank_endpoint: str = Field(
        "https://api.jina.ai/v1/rerank",
        description="Jina AI rerank REST API endpoint",
    )

    # ==========================================
    # 4. Document Processing & Ingestion
    # ==========================================
    chunk_size: int = Field(1000, description="Character chunk size for text splitting")
    chunk_overlap: int = Field(200, description="Character overlap between consecutive chunks")
    upload_dir: Path = Field(Path("data/uploads"), description="Directory where uploaded files are stored")

    # ==========================================
    # 5. RAG Retrieval & Reranking Settings
    # ==========================================
    top_k: int = Field(5, description="Final number of top reranked chunks passed to LLM")
    fetch_k: int = Field(10, description="Stage 1 candidates retrieved from Atlas Vector Search")
    rerank_top_n: int = Field(5, description="Stage 2 top reranked chunks")

    # ==========================================
    # 6. Conversation History Window Limits
    # ==========================================
    history_fetch_limit: int = Field(11, description="Max messages loaded from MongoDB for context")
    history_rephrase_limit: int = Field(10, description="Messages passed to query rephraser (~5 turns)")
    history_qa_limit: int = Field(6, description="Messages passed to final QA prompt (~3 turns)")


# Export a global singleton instance
settings = Settings()
