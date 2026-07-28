"""
MongoDB database utilities for chat persistence.
"""

import os
import datetime
from uuid import uuid4
from pymongo import MongoClient
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("Missing MONGODB_URI in environment variables.")

# Initialize the MongoClient.
# PyMongo manages connection pooling automatically.
client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000
)
db = client.get_database("docqa_chat")
chats_collection = db.get_collection("chats")
messages_collection = db.get_collection("messages")


def initialize_database() -> None:
    """
    Verify the connection to MongoDB and ensure indexes are created.
    """
    try:
        # Ping the admin database to verify the connection is alive
        client.admin.command("ping")
        # Ensure indexing on chat_id in messages collection for fast retrieval
        messages_collection.create_index("chat_id")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to MongoDB: {e}")


def create_chat(user_id: str, title: str = "New Chat") -> str:
    """
    Create a new chat conversation.

    Args:
        user_id: The ID of the user owning this chat.
        title: Initial title for chat
    
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
        "updated_at": now
    })

    return chat_id


def get_all_chats(user_id: str) -> list[dict]:
    """
    Retrieve all chats ordered by most recently updated.

    Args:
        user_id: The ID of the user.

    Returns:
        A list of chat records.
    """
    chats = chats_collection.find({"user_id": user_id}).sort("updated_at", -1)
    return list(chats)


def save_message(
    chat_id: str,
    role: str,
    content: str,
    sources: list[dict] | None = None
) -> None:
    """
    Save a message to a chat.

    Args:
        chat_id: The ID of the chat.
        role: The role of the message sender (user or assistant).
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
        "created_at": now
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
    Retrieve all messages for a chat.

    Args:
        chat_id: The ID of the chat

    Returns: 
        A list of messages ordered chronologically.
    """
    messages = list(messages_collection.find({"chat_id": chat_id}).sort("created_at", 1))
    
    # Map _id object to message_id as string for downstream compatibility
    for msg in messages:
        msg["message_id"] = str(msg["_id"])
        
    return messages


def get_recent_chat_messages(chat_id: str, limit: int = 10) -> list[dict]:
    """
    Retrieve the most recent messages for a chat, ordered chronologically.

    Args:
        chat_id: The ID of the chat
        limit: The maximum number of recent messages to return

    Returns: 
        A list of messages ordered chronologically.
    """
    # Fetch latest messages first
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


def update_chat_title(
    chat_id: str,
    title: str
) -> None:
    """
    Update the title of a chat.

    Args:
        chat_id: The ID of the chat.
        title: The new chat title.
    """
    chats_collection.update_one(
        {"_id": chat_id},
        {
            "$set": {
                "title": title,
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
        }
    )


def delete_chat(chat_id: str) -> None:
    """
    Delete a chat and all its associated messages.

    Args:
        chat_id: The ID of the chat to delete.
    """
    chats_collection.delete_one({"_id": chat_id})
    messages_collection.delete_many({"chat_id": chat_id})