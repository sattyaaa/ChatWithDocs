from typing import TypedDict, List
from langchain_core.documents import Document
from langgraph.graph import StateGraph, START, END

from rag.config import llm, rephrase_llm
from rag.retrieval import retrieve_documents
from rag.prompts import CONDENSE_QUESTION_PROMPT, SYSTEM_PROMPT
from database.database import get_recent_chat_messages

import logging
logger = logging.getLogger(__name__)


class RAGState(TypedDict):
    query: str
    chat_id: str
    tenant: str
    document_ids: List[str] | None

    chat_history_rephrase: str
    chat_history_qa: str
    rephrased_query: str
    documents: List[Document]
    answer: str


def load_history_node(state: RAGState) -> dict:
    messages = get_recent_chat_messages(state["chat_id"], limit=11)
    history_messages = [msg for msg in messages if msg["content"] != state["query"]]

    recent_rephrase = history_messages[-10:]
    recent_qa = history_messages[-6:]

    chat_history_rephrase = ""
    for msg in recent_rephrase:
        role = "User" if msg["role"] == "user" else "Assistant"
        chat_history_rephrase += f"{role}: {msg['content']}\n"

    chat_history_qa = ""
    for msg in recent_qa:
        role = "User" if msg["role"] == "user" else "Assistant"
        chat_history_qa += f"{role}: {msg['content']}\n"

    return {
        "chat_history_rephrase": chat_history_rephrase,
        "chat_history_qa": chat_history_qa
    }


def rephrase_query_node(state: RAGState) -> dict:
    chat_history = state["chat_history_rephrase"]
    query = state["query"]

    if not chat_history.strip():
        return {"rephrased_query": query}

    try:
        rephrase_prompt = CONDENSE_QUESTION_PROMPT.format(
            chat_history=chat_history,
            question=query
        )
        rephrased = rephrase_llm.invoke(rephrase_prompt).content.strip()
        if rephrased:
            logger.info(f"Rephrased query: '{query}' -> '{rephrased}'")
            return {"rephrased_query": rephrased}
    except Exception as e:
        logger.error(f"Failed to rephrase query: {e}")
        
    return {"rephrased_query": query}


def retrieve_documents_node(state: RAGState) -> dict:
    docs = retrieve_documents(
        query=state["rephrased_query"],
        chat_id=state["chat_id"],
        tenant=state["tenant"],
        document_ids=state["document_ids"],
    )
    return {"documents": docs}


def _formate_context(documents: List[Document]) -> str:
    return "\n\n".join(document.page_content for document in documents)


def generate_answer_node(state: RAGState) -> dict:
    formatted_context = _formate_context(state["documents"])
    history = state["chat_history_qa"]
    
    prompt = SYSTEM_PROMPT.format(
        context=formatted_context,
        chat_history=history if history.strip() else "No previous messages."
    )
    
    ans = llm.invoke([
        ("system", prompt),
        ("human", state["query"])
    ]).content.strip()
    
    return {"answer": ans}


workflow = StateGraph(RAGState)

workflow.add_node("load_history", load_history_node)
workflow.add_node("rephrase_query", rephrase_query_node)
workflow.add_node("retrieve_documents", retrieve_documents_node)
workflow.add_node("generate_answer", generate_answer_node)

workflow.add_edge(START, "load_history")
workflow.add_edge("load_history", "rephrase_query")
workflow.add_edge("rephrase_query", "retrieve_documents")
workflow.add_edge("retrieve_documents", "generate_answer")
workflow.add_edge("generate_answer", END)

app = workflow.compile()


def ask_question(
    query: str, 
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
):
    try:
        initial_state = {
            "query": query,
            "chat_id": chat_id,
            "tenant": tenant,
            "document_ids": document_ids,
            "chat_history_rephrase": "",
            "chat_history_qa": "",
            "rephrased_query": "",
            "documents": [],
            "answer": "",
        }

        result = app.invoke(initial_state)

        return {
            "answer": result["answer"],
            "sources": result["documents"],
        }

    except Exception as exc:
        logger.exception("Failed to execute RAG workflow.")
        raise RuntimeError("Failed to generate answer.") from exc
