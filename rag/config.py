"""
Application configuration and shared resources.

This module:
- Loads .env variables.
- Defines constants.
- Initializes the embedding model.
- Initializes the LLM.
- Initializes the Weaviate client.
"""

from dotenv import load_dotenv
from pydantic import SecretStr
import os

import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Property, DataType

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_weaviate import WeaviateVectorStore


# Load .env
_=load_dotenv()

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "")
WEAVIATE_URL = os.getenv("WEAVIATE_URL") or ""
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY") or ""

if not GROQ_API_KEY:
    raise ValueError("MISSING GROQ_API_KEY in .env")

if not WEAVIATE_API_KEY:
    raise ValueError("Missing WEAVIATE_API_KEY in .env")

if not WEAVIATE_URL:
    raise ValueError("Missing WEAVIATE_URL in .env")



# Application Constants

COLLECTION_NAME="Documents"
LLM_MODEL="llama-3.3-70b-versatile"
EMBEDDING_MODEL="BAAI/bge-base-en-v1.5"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

TOP_K = 5


# Embedding Model

embeddings = HuggingFaceEmbeddings(
    model_name = EMBEDDING_MODEL,
    model_kwargs = {"device": "cpu"},
    encode_kwargs = {"normalize_embeddings": True}
)


# Groq LLM

llm = ChatGroq(
    model = LLM_MODEL,
    api_key = SecretStr(GROQ_API_KEY),
    temperature=0.2,
)



from weaviate.classes.init import Auth, Timeout, AdditionalConfig

import atexit

# Close any existing client on module reload to prevent unclosed SSL sockets/connection leaks
_existing_client = globals().get("client")
if _existing_client is not None:
    try:
        _existing_client.close()
    except Exception:
        pass

client: weaviate.WeaviateClient | None = None

def cleanup_client():
    global client
    if client is not None:
        try:
            client.close()
        except Exception:
            pass

atexit.register(cleanup_client)


def get_client() -> weaviate.WeaviateClient:
    global client
    if client is None or not client.is_connected():
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
            additional_config=AdditionalConfig(
                timeout=Timeout(init=60, query=120, insert=180)
            )
        )
    return client


def create_collection_if_not_exists():
    """
    Create the Weaviate collection if it does not already exist.

    Raises:
        RuntimeError:
            If the collection cannot be created.
    """
    c = get_client()
    if c.collections.exists(COLLECTION_NAME):
        return

    try:
        _=c.collections.create(
            name=COLLECTION_NAME,
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="chat_id", data_type=DataType.TEXT),
                Property(name="document_id", data_type=DataType.TEXT),
                Property(name="filename", data_type=DataType.TEXT),
                Property(name="page", data_type=DataType.INT),
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
            ]
        )

    except Exception as exc:
        raise RuntimeError(
            f"Failed to create collection '{COLLECTION_NAME}'."
        ) from exc


# Initialize collection
create_collection_if_not_exists()


def get_vector_store() -> WeaviateVectorStore:
    """
    Initializes and returns a WeaviateVectorStore instance.

    Returns:
        An initialized WeaviateVectorStore instance.
    """
    c = get_client()
    return WeaviateVectorStore(
        client=c,
        index_name=COLLECTION_NAME,
        embedding=embeddings,
        text_key="text"
    )