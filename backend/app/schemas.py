"""
Pydantic schemas for the QADoc FastAPI REST API.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# --- Auth Schemas ---
class UserLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    user_id: str
    username: str


# --- Chat Session Schemas ---
class ChatSummary(BaseModel):
    chat_id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"


# --- Citation & Message Schemas ---
class DocumentCitation(BaseModel):
    filename: str
    page: Optional[int] = None
    relevance_score: Optional[float] = None
    content: str = ""


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None
    sources: List[DocumentCitation] = []


class AskQuestionRequest(BaseModel):
    query: str = Field(..., min_length=1)
    document_ids: Optional[List[str]] = None


class AskQuestionResponse(BaseModel):
    answer: str
    sources: List[DocumentCitation] = []
    chat_title: Optional[str] = None


# --- Document Upload & Management Schemas ---
class IngestionResponse(BaseModel):
    filename: str
    chunks_ingested: int
    message: str


class DocumentItem(BaseModel):
    filename: str
    chunks_count: int
    chat_id: str
    user_id: str


class DeleteDocumentResponse(BaseModel):
    filename: str
    deleted_chunks: int
    message: str

