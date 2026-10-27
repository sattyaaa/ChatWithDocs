"""
MongoDB database connection and persistence layer for QADoc.
Handles chat sessions, messages, and vector document storage.
Framework-agnostic: Pure Python, zero UI dependencies.
"""

import datetime
from uuid import uuid4
from pymongo import MongoClient

from qadoc.config import settings

# Initialize the MongoClient with connection pooling from central settings
client: MongoClient = MongoClient(
    settings.mongodb_uri,
    serverSelectionTimeoutMS=settings.mongodb_server_timeout_ms,
    connectTimeoutMS=settings.mongodb_server_timeout_ms,
)

db = client.get_database(settings.mongodb_db_name)
users_collection = db.get_collection(settings.users_collection_name)
chats_collection = db.get_collection(settings.chats_collection_name)
messages_collection = db.get_collection(settings.messages_collection_name)
documents_collection = db.get_collection(settings.documents_collection_name)


def initialize_database() -> None:
    """
    Verify connection to MongoDB and ensure standard indexes exist.
    """
    try:
        # Ping the admin database to verify connection is alive
        client.admin.command("ping")
        # Ensure indexing on chat_id in messages collection for fast retrieval
        messages_collection.create_index("chat_id")
        # Ensure compound indexing on user_id and chat_id in documents collection
        documents_collection.create_index([("user_id", 1), ("chat_id", 1)])
    except Exception as e:
        raise RuntimeError(f"Failed to connect to MongoDB: {e}") from e


def create_chat(user_id: str, title: str = "New Chat") -> str:
    """
    Create a new chat conversation.

    Args:
        user_id: The ID of the user owning this chat.
        title: Initial title for the chat.

    Returns:
        The unique ID of the newly created chat.
    """
    chat_id = str(uuid4())
    now = datetime.datetime.now(datetime.timezone.utc)

    chats_collection.insert_one({
        "_id": chat_id,
        "chat_id": chat_id,
        "user_id": user_id,
        "title": title,
        "created_at": now,
        "updated_at": now,
    })

    return chat_id


def get_all_chats(user_id: str) -> list[dict]:
    """
    Retrieve all chats for a given user ordered by most recently updated.
    """
    chats = chats_collection.find({"user_id": user_id}).sort("updated_at", -1)
    return list(chats)


def save_message(
    chat_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> None:
    """
    Save a message to a chat.

    Args:
        chat_id: The ID of the chat.
        role: The role of the message sender ('user' or 'assistant').
        content: The content of the message.
        sources: Optional list of source chunk metadata dicts.
    """
    if role not in {"user", "assistant"}:
        raise ValueError("Role must be either 'user' or 'assistant'.")

    now = datetime.datetime.now(datetime.timezone.utc)

    doc = {
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "created_at": now,
    }
    if sources:
        doc["sources"] = sources

    messages_collection.insert_one(doc)

    chats_collection.update_one(
        {"_id": chat_id},
        {"$set": {"updated_at": now}}
    )


def get_chat_messages(chat_id: str) -> list[dict]:
    """
    Retrieve all messages for a chat, ordered chronologically.
    """
    messages = list(messages_collection.find({"chat_id": chat_id}).sort("created_at", 1))

    for msg in messages:
        msg["message_id"] = str(msg["_id"])

    return messages


def get_recent_chat_messages(chat_id: str, limit: int = 10) -> list[dict]:
    """
    Retrieve the most recent messages for a chat, ordered chronologically.
    """
    messages = list(
        messages_collection.find({"chat_id": chat_id})
        .sort("created_at", -1)
        .limit(limit)
    )

    # Reverse to restore chronological order (older -> newer)
    messages.reverse()

    for msg in messages:
        msg["message_id"] = str(msg["_id"])

    return messages


def update_chat_title(chat_id: str, title: str) -> None:
    """
    Update the title of a chat.
    """
    chats_collection.update_one(
        {"_id": chat_id},
        {
            "$set": {
                "title": title,
                "updated_at": datetime.datetime.now(datetime.timezone.utc),
            }
        }
    )


def delete_chat(chat_id: str) -> None:
    """
    Delete a chat and all its associated messages.
    """
    chats_collection.delete_one({"_id": chat_id})
    messages_collection.delete_many({"chat_id": chat_id})
