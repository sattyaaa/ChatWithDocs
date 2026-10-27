"""
LangGraph ReAct Agent workflow for Document QA.

ReAct Agent Architecture:
- Uses Groq's high-speed reasoning model (openai/gpt-oss-120b) with native tool calling.
- Equipped with `retrieve_document_context` tool (Stage 1 Atlas Vector Search + Stage 2 Jina Reranker v2).
- Autonomously formulates search queries based on conversational context (Auto-Rephrase).
- Skips retrieval on chit-chat or direct conversational questions to save latency and API cost.
- Sliding-window context pruning retains recent chat turns without bloating context windows.
- Granular LangSmith tracing with per-step latency telemetry.
Framework-agnostic: Pure Python, zero UI dependencies.
"""

import logging
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langsmith import traceable

from qadoc.config import settings
from qadoc.rag.config import llm
from qadoc.rag.tools import retrieve_document_context
from qadoc.rag.prompts import get_agent_system_prompt
from qadoc.database.connection import get_recent_chat_messages, documents_collection

logger = logging.getLogger(__name__)

# Compile ReAct Agent with the two-stage retrieval tool
agent_executor = create_react_agent(
    model=llm,
    tools=[retrieve_document_context],
)


def get_chat_documents(chat_id: str, tenant: str) -> list[str]:
    """Retrieve distinct document filenames accessible in this chat session."""
    try:
        filenames = documents_collection.distinct("filename", {"user_id": tenant, "chat_id": chat_id})
        if not filenames:
            filenames = documents_collection.distinct("filename", {"user_id": tenant})
        return filenames
    except Exception as e:
        logger.warning(f"Failed to query chat document names: {e}")
        return []


@traceable(name="Document QA ReAct Turn", run_type="chain")
def ask_question(
    query: str,
    chat_id: str,
    tenant: str,
    document_ids: list[str] | None = None,
) -> dict:
    """
    Executes the Document QA ReAct Agent and returns the grounded answer and citations.
    Traced to LangSmith with session grouping and per-node latency telemetry.

    Args:
        query: User input query.
        chat_id: Active chat session ID.
        tenant: User ID for tenant filtering.
        document_ids: Optional list of document IDs to restrict retrieval to.

    Returns:
        dict with keys:
            - 'answer' (str): Generated answer text.
            - 'sources' (list[Document]): List of retrieved LangChain documents with relevance scores.
    """
    try:
        # 1. Fetch available documents in this session
        uploaded_files = get_chat_documents(chat_id=chat_id, tenant=tenant)
        system_prompt = get_agent_system_prompt(uploaded_files=uploaded_files)

        # 2. Fetch and prune conversation history from MongoDB
        raw_history = get_recent_chat_messages(
            chat_id=chat_id,
            limit=settings.history_fetch_limit,
        )

        # Exclude any entry that matches the current query if it was already saved
        history_messages = [msg for msg in raw_history if msg.get("content") != query]

        # Apply context pruning to the configured QA limit
        pruned_history = history_messages[-settings.history_qa_limit:]

        formatted_messages = [SystemMessage(content=system_prompt)]
        for msg in pruned_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                formatted_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_messages.append(AIMessage(content=content))

        # Append current user prompt
        formatted_messages.append(HumanMessage(content=query))

        # 2. Configure runtime parameters and tracing metadata
        config = {
            "configurable": {
                "chat_id": chat_id,
                "tenant": tenant,
                "document_ids": document_ids,
            },
            "metadata": {
                "session_id": chat_id,
                "user_id": tenant,
                "chat_id": chat_id,
            },
            "tags": ["rag", "react_agent", "qadoc"],
            "run_name": f"ReAct Turn ({chat_id[:8]})",
        }

        logger.info(
            f"Invoking ReAct Agent for chat '{chat_id}' with {len(formatted_messages)} messages in context"
        )

        # 3. Invoke ReAct Agent
        result = agent_executor.invoke({"messages": formatted_messages}, config=config)
        result_messages = result.get("messages", [])

        # 4. Extract final model answer
        last_message = result_messages[-1] if result_messages else None
        if last_message and hasattr(last_message, "content"):
            answer = str(last_message.content).strip()
        else:
            answer = str(last_message or "I couldn't process your question.").strip()

        # 5. Extract retrieved document artifacts from ToolMessages
        sources: list[Document] = []
        seen_keys: set[str] = set()

        for msg in result_messages:
            if isinstance(msg, ToolMessage) and getattr(msg, "artifact", None):
                artifacts = msg.artifact
                if isinstance(artifacts, list):
                    for doc in artifacts:
                        if isinstance(doc, Document):
                            # Unique key per chunk to prevent duplicates
                            key = (
                                doc.metadata.get("_id")
                                or f"{doc.metadata.get('document_id')}_{doc.metadata.get('chunk_id')}"
                                or doc.page_content[:60]
                            )
                            if key not in seen_keys:
                                seen_keys.add(key)
                                sources.append(doc)

        logger.info(
            f"ReAct Turn completed for chat '{chat_id}'. Citations extracted: {len(sources)}"
        )

        return {
            "answer": answer,
            "sources": sources,
        }

    except Exception as exc:
        logger.exception("Failed to execute ReAct agent.")
        raise RuntimeError(f"Failed to generate answer: {exc}") from exc
