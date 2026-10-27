"""
Chats and QA router for QADoc FastAPI backend.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas import (
    ChatSummary,
    CreateChatRequest,
    ChatMessageResponse,
    AskQuestionRequest,
    AskQuestionResponse,
    DocumentCitation,
)

from qadoc.database.connection import (
    get_all_chats,
    create_chat,
    get_chat_messages,
    save_message,
    update_chat_title,
    chats_collection,
    messages_collection,
)
from qadoc.rag.graph import ask_question
from qadoc.rag.config import llm
from qadoc.rag.ingestion import delete_chat_embeddings

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=List[ChatSummary])
def list_chats(user_id: str = Query(..., description="The tenant/user ID")):
    """
    List all chat sessions for a given user, ordered by most recent.
    """
    try:
        raw_chats = get_all_chats(user_id=user_id)
        return [
            ChatSummary(
                chat_id=c.get("chat_id", c.get("_id")),
                title=c.get("title", "Untitled Chat"),
                created_at=str(c.get("created_at", "")),
                updated_at=str(c.get("updated_at", "")),
            )
            for c in raw_chats
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chats: {str(e)}",
        )


@router.post("", response_model=ChatSummary)
def create_new_chat(
    payload: CreateChatRequest,
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Create a new chat conversation.
    """
    try:
        chat_id = create_chat(user_id=user_id, title=payload.title or "New Chat")
        return ChatSummary(chat_id=chat_id, title=payload.title or "New Chat")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat: {str(e)}",
        )


@router.get("/{chat_id}/messages", response_model=List[ChatMessageResponse])
def get_messages(chat_id: str):
    """
    Retrieve message history for a given chat session.
    """
    try:
        raw_messages = get_chat_messages(chat_id=chat_id)
        result: List[ChatMessageResponse] = []

        for msg in raw_messages:
            sources_list: List[DocumentCitation] = []
            if "sources" in msg and isinstance(msg["sources"], list):
                for s in msg["sources"]:
                    sources_list.append(
                        DocumentCitation(
                            filename=s.get("filename", "Unknown Document"),
                            page=s.get("page"),
                            relevance_score=s.get("relevance_score"),
                            content=s.get("content", ""),
                        )
                    )

            result.append(
                ChatMessageResponse(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    created_at=str(msg.get("timestamp", "")),
                    sources=sources_list,
                )
            )

        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}",
        )


@router.post("/{chat_id}/ask", response_model=AskQuestionResponse)
def ask(
    chat_id: str,
    payload: AskQuestionRequest,
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Send a question to the ReAct agent. Returns the complete grounded answer and citations.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty.",
        )

    # 1. Update chat title intelligently if generic
    updated_title: Optional[str] = None
    try:
        chat_rec = chats_collection.find_one({"chat_id": chat_id})
        current_title = (chat_rec.get("title") or "") if chat_rec else ""
        is_generic = not current_title or current_title.strip().lower() in {
            "new chat", "hi", "hello", "hey", "untitled chat", "chat session"
        }
        is_greeting = query.strip().lower() in {"hi", "hello", "hey", "test", "how are you"}

        if is_generic and not is_greeting:
            title_prompt = (
                f"Generate a short, informative 3 to 5 word title for a chat that begins with this question: '{query}'. "
                "Output ONLY the title. Do NOT include quotes, punctuation, or conversational words."
            )
            res_title = llm.invoke(title_prompt)
            gen_title = res_title.content.strip().strip('"').strip("'") if hasattr(res_title, "content") else str(res_title).strip()
            if gen_title and len(gen_title) < 50:
                update_chat_title(chat_id, gen_title)
                updated_title = gen_title
        elif not current_title:
            new_title = query[:30] + ("..." if len(query) > 30 else "")
            update_chat_title(chat_id, new_title)
            updated_title = new_title
    except Exception:
        pass

    # 2. Save user message to database
    try:
        save_message(chat_id=chat_id, role="user", content=query)
    except Exception:
        pass

    # 3. Execute LangGraph ReAct Agent
    try:
        res = ask_question(
            query=query,
            chat_id=chat_id,
            tenant=user_id,
            document_ids=payload.document_ids,
        )

        answer = res.get("answer", "")
        raw_sources = res.get("sources", [])

        citations: List[DocumentCitation] = []
        source_dicts_for_db: List[dict] = []

        for doc in raw_sources:
            filename = doc.metadata.get("filename", "Unknown Document")
            page = doc.metadata.get("page")
            score = doc.metadata.get("relevance_score")
            content = doc.page_content

            citation = DocumentCitation(
                filename=filename,
                page=page,
                relevance_score=score,
                content=content,
            )
            citations.append(citation)

            source_dicts_for_db.append({
                "filename": filename,
                "page": page,
                "relevance_score": score,
                "content": content,
            })

        # 4. Save assistant answer with citations to database
        try:
            save_message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                sources=source_dicts_for_db,
            )
        except Exception:
            pass

        return AskQuestionResponse(
            answer=answer,
            sources=citations,
            chat_title=updated_title,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ReAct agent execution failed: {str(e)}",
        )


@router.delete("/{chat_id}")
def delete_chat(
    chat_id: str,
    user_id: str = Query(..., description="The tenant/user ID"),
):
    """
    Delete a chat session, its messages, and its vector embeddings.
    """
    try:
        # Delete chat record
        chats_collection.delete_one({"chat_id": chat_id, "user_id": user_id})
        # Delete messages
        messages_collection.delete_many({"chat_id": chat_id})
        # Delete embeddings in MongoDB Atlas Vector Search
        delete_chat_embeddings(chat_id=chat_id, tenant=user_id)

        return {"message": f"Chat '{chat_id}' deleted successfully."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat: {str(e)}",
        )
