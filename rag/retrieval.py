from langchain_core.documents import Document

from weaviate.classes.query import Filter

from rag.config import (
    TOP_K,
    get_vector_store,
)



def _build_filter(
    chat_id: str,
    document_ids: list[str] | None = None,
):
    """
    Builds a Weaviate filter expression for RAG retrieval.

    Args:
        chat_id: Unique identifier of the chat session.
        document_ids: OPtional list of document IDs to search within,

    Returns:
        A Weaviate Filter object.
    """
    chat_filter = Filter.by_property("chat_id").equal(chat_id)

    if not document_ids:
        return chat_filter

    document_filter = Filter.by_property("document_id").contains_any(document_ids)


    return chat_filter & document_filter



def retrieve_documents(
    query: str,
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
    top_k: int = TOP_K,
) -> list[Document]:
    """
    Retrieve the most relevant document chunks for a query under a tenant.

    Args:
        query: User's question
        chat_id: Unique id of current chat
        tenant: Unique identifier of the tenant (user_id)
        document_ids: Optional list of document ids to search within.
        top_k: Maximum number of chunks to return

    Returns:
        A list of relevant langchain Document objects.
    """
    vector_store = get_vector_store()

    metadata_filter = _build_filter(
        chat_id=chat_id,
        document_ids=document_ids,
    )

    try:
        return vector_store.similarity_search(
            query=query,
            k=top_k,
            filters=metadata_filter,
            tenant=tenant
        )
    except Exception:
        # Re-fetch vector store instance with fresh connection and retry once
        vector_store = get_vector_store()
        return vector_store.similarity_search(
            query=query,
            k=top_k,
            filters=metadata_filter,
            tenant=tenant
        )