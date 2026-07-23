"""
SQLite database utilities for chat persistence.
"""

import sqlite3
from pathlib import Path
from uuid import uuid4

DATABASE_PATH = Path("database/chat.db")

from contextlib import contextmanager


@contextmanager
def get_connection():
    """
    Create, yield, and close a SQLite database connection.
    """
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    _ = connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    """
    Create the required database tables if they do not already exist.
    """
    with get_connection() as connection:

        _=connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        _=connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(chat_id)
                REFERENCES chats(chat_id)
                ON DELETE CASCADE
            )
            """
        )

        connection.commit()
    

def create_chat(title: str = "New Chat") -> str:
    """
    Create a new chat conversation.

    Args:
        title: Initial title for chat
    
    Returns: 
        The unique ID of the newly created chat.
    """

    chat_id = str(uuid4())

    with get_connection() as connection:
        _=connection.execute(
            """
            INSERT INTO chats (chat_id, title)
            VALUES (?, ?)
            """,
            (chat_id, title),
        )
        connection.commit()

    return chat_id


def get_all_chats() -> list[sqlite3.Row]:
    """
    Retrieve all chats ordered by most recently updated.

    Returns:
        A list of chat records
    """

    with get_connection() as connection:
        chats = connection.execute(
            """
            SELECT *
            FROM chats
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return chats


def save_message(
    chat_id: str,
    role: str,
    content: str
) -> None:
    """
    Save a message to a chat.

    Args:
        chat_id: The ID of the chat.
        role: The role of the message sender (user or assistant).
        content: The content of the message.
    """

    if role not in {"user", "assistant"}:
        raise ValueError("Role must be either 'user' or 'assistant'.")
        
    with get_connection() as connection:

        _=connection.execute(
            """
            INSERT INTO messages (
                chat_id,
                role,
                content
            )
            VALUES (?, ?, ?)
            """,
            (chat_id, role, content),
        )

        _=connection.execute(
            """
            UPDATE chats
            SET updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
            """,
            (chat_id,),
        )

        connection.commit()


def get_chat_messages(chat_id: str) -> list[sqlite3.Row]:
    """
    Retrieve all messages for a chat.

    Args:
        chat_id: The ID of the chat

    Returns: 
        A list of messages ordered chronologically.
    """

    with get_connection() as connection:
        message = connection.execute(
            """
            SELECT
                message_id,
                role,
                content,
                created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at ASC, message_id ASC
            """,
            (chat_id,),
        ).fetchall()

    return message


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

    with get_connection() as connection:
        _=connection.execute(
            """
            UPDATE chats
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE chat_id = ?
            """,
            (title, chat_id,),
        )

        connection.commit()


def delete_chat(chat_id: str)-> None:
    """
    Delete a chat and all its associated messages.

    Args:
        chat_id: The ID of the chat to delete.
    """

    with get_connection() as connection:
        _=connection.execute(
            """
            DELETE FROM chats
            WHERE chat_id = ?
            """,
            (chat_id,),
        )

        connection.commit()