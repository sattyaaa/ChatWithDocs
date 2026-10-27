"""
LangGraph state graph workflow for Document QA.

Workflow Nodes (Each independently traced with latency, inputs, and outputs):
1. load_history: Retrieves recent chat conversation context from MongoDB.
2. rephrase_query: Reformulates conversational queries into standalone database search queries (Groq 20B).
3. retrieve_candidates: Executes similarity search on MongoDB Atlas Vector Search (Stage 1).
4. rerank_documents: Reranks candidate chunks with cross-attention scoring using Jina Reranker v2 (Stage 2).
5. generate_answer: Generates grounded response using Groq 120B (openai/gpt-oss-120b).
Framework-agnostic: Pure Python, zero UI dependencies.
"""

from typing import TypedDict, List
import logging
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

from qadoc.config import settings
from qadoc.rag.config import llm, rephrase_llm
from qadoc.rag.retrieval import retrieve_candidates, rerank_documents
from qadoc.rag.prompts import CONDENSE_QUESTION_PROMPT, SYSTEM_PROMPT
from qadoc.database.connection import get_recent_chat_messages

logger = logging.getLogger(__name__)


class RAGState(TypedDict):
    query: str
    chat_id: str
    tenant: str
    document_ids: List[str] | None

    chat_history_rephrase: str
    chat_history_qa: str
    rephrased_query: str
    raw_documents: List[Document]
    documents: List[Document]
    answer: str


def load_history_node(state: RAGState) -> dict:
    """
    Node 1: Pull recent conversation history from MongoDB.
    """
    messages = get_recent_chat_messages(state["chat_id"], limit=settings.history_fetch_limit)
    history_messages = [msg for msg in messages if msg.get("content") != state["query"]]

    recent_rephrase = history_messages[-settings.history_rephrase_limit:]
    recent_qa = history_messages[-settings.history_qa_limit:]

    chat_history_rephrase = ""
    for msg in recent_rephrase:
        role = "User" if msg.get("role") == "user" else "Assistant"
        chat_history_rephrase += f"{role}: {msg.get('content', '')}\n"

    chat_history_qa = ""
    for msg in recent_qa:
        role = "User" if msg.get("role") == "user" else "Assistant"
        chat_history_qa += f"{role}: {msg.get('content', '')}\n"

    return {
        "chat_history_rephrase": chat_history_rephrase,
        "chat_history_qa": chat_history_qa,
    }


def rephrase_query_node(state: RAGState) -> dict:
    """
    Node 2: Condense conversational query into a standalone search query using Groq 20B.
    """
    chat_history = state["chat_history_rephrase"]
    query = state["query"]

    # First turn in conversation: keep query as-is to save latency and tokens
    if not chat_history.strip():
        return {"rephrased_query": query}

    try:
        rephrase_prompt = CONDENSE_QUESTION_PROMPT.format(
            chat_history=chat_history,
            question=query,
        )
        response = rephrase_llm.invoke(rephrase_prompt)
        rephrased = response.content.strip() if hasattr(response, "content") else str(response).strip()

        if rephrased:
            logger.info(f"Rephrased query: '{query}' -> '{rephrased}'")
            return {"rephrased_query": rephrased}

    except Exception as e:
        logger.error(f"Failed to rephrase query: {e}")

    return {"rephrased_query": query}


def retrieve_candidates_node(state: RAGState) -> dict:
    """
    Node 3: Stage 1 - Retrieve raw candidate chunks from MongoDB Atlas Vector Search.
    """
    candidates = retrieve_candidates(
        query=state["rephrased_query"],
        chat_id=state["chat_id"],
        tenant=state["tenant"],
        document_ids=state["document_ids"],
        fetch_k=settings.fetch_k,
    )
    return {"raw_documents": candidates}


def rerank_documents_node(state: RAGState) -> dict:
    """
    Node 4: Stage 2 - Rerank candidate chunks with Jina AI cross-encoder reranker.
    """
    candidates = state.get("raw_documents", [])
    if not candidates:
        return {"documents": []}

    reranked = rerank_documents(
        query=state["rephrased_query"],
        documents=candidates,
        top_n=settings.rerank_top_n,
    )
    return {"documents": reranked}


def _format_context(documents: List[Document]) -> str:
    return "\n\n".join(document.page_content for document in documents)


def generate_answer_node(state: RAGState) -> dict:
    """
    Node 5: Grounded QA generation using Groq 120B (openai/gpt-oss-120b).
    """
    formatted_context = _format_context(state["documents"])
    history = state["chat_history_qa"]

    prompt = SYSTEM_PROMPT.format(
        context=formatted_context if formatted_context.strip() else "No documents matched the query.",
        chat_history=history if history.strip() else "No previous messages.",
    )

    response = llm.invoke([
        ("system", prompt),
        ("human", state["query"]),
    ])

    ans = response.content.strip() if hasattr(response, "content") else str(response).strip()
    return {"answer": ans}


# Compile workflow graph with distinct nodes for complete observability
workflow = StateGraph(RAGState)

workflow.add_node("load_history", load_history_node)
workflow.add_node("rephrase_query", rephrase_query_node)
workflow.add_node("retrieve_candidates", retrieve_candidates_node)
workflow.add_node("rerank_documents", rerank_documents_node)
workflow.add_node("generate_answer", generate_answer_node)

workflow.add_edge(START, "load_history")
workflow.add_edge("load_history", "rephrase_query")
workflow.add_edge("rephrase_query", "retrieve_candidates")
workflow.add_edge("retrieve_candidates", "rerank_documents")
workflow.add_edge("rerank_documents", "generate_answer")
workflow.add_edge("generate_answer", END)

app = workflow.compile()


@traceable(name="Document QA Turn", run_type="chain")
def ask_question(
    query: str,
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
) -> dict:
    """
    Executes the compiled RAG workflow and returns the grounded answer and citations.
    Traced to LangSmith with session grouping and per-node latency telemetry.

    Args:
        query: User input query.
        chat_id: Active chat session ID.
        tenant: User ID for tenant filtering.
        document_ids: Optional list of document IDs to restrict retrieval to.

    Returns:
        dict with keys:
            - 'answer' (str): Generated answer text.
            - 'sources' (list[Document]): List of retrieved LangChain documents.
    """
    try:
        initial_state = {
            "query": query,
            "chat_id": chat_id,
            "tenant": tenant,
            "document_ids": document_ids,
            "chat_history_rephrase": "",
            "chat_history_qa": "",
            "rephrased_query": "",
            "raw_documents": [],
            "documents": [],
            "answer": "",
        }

        config = {
            "metadata": {
                "session_id": chat_id,
                "user_id": tenant,
                "chat_id": chat_id,
            },
            "tags": ["rag", "chat_turn", "qadoc"],
            "run_name": f"Chat Turn ({chat_id[:8]})",
        }

        result = app.invoke(initial_state, config=config)

        return {
            "answer": result["answer"],
            "sources": result["documents"],
        }

    except Exception as exc:
        logger.exception("Failed to execute RAG workflow.")
        raise RuntimeError(f"Failed to generate answer: {exc}") from exc
