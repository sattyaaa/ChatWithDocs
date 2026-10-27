"""
Database layer for QADoc.
Provides MongoDB connection, session/chat persistence, and authentication services.
"""

from qadoc.database.connection import (
    db,
    initialize_database,
    create_chat,
    get_all_chats,
    get_chat_messages,
    get_recent_chat_messages,
    save_message,
    delete_chat,
    update_chat_title,
    users_collection,
    chats_collection,
    messages_collection,
    documents_collection,
)

from qadoc.database.auth import (
    hash_password,
    verify_password,
    register_user,
    authenticate_user,
)

__all__ = [
    "db",
    "initialize_database",
    "create_chat",
    "get_all_chats",
    "get_chat_messages",
    "get_recent_chat_messages",
    "save_message",
    "delete_chat",
    "update_chat_title",
    "users_collection",
    "chats_collection",
    "messages_collection",
    "documents_collection",
    "hash_password",
    "verify_password",
    "register_user",
    "authenticate_user",
]
