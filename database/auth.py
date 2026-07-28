"""
Authentication and user management utilities for the Document QA Assistant.
Uses MongoDB for credential storage and standard hashlib for secure PBKDF2-SHA256 password hashing.
"""

import hashlib
import os
import datetime
from database.database import db

users_collection = db.get_collection("users")


def hash_password(password: str) -> str:
    """
    Hash a password using PBKDF2 HMAC SHA-256 with a unique salt.
    
    Format: salt_hex:hash_hex
    """
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt,
        iterations=100000,
    )
    return f"{salt.hex()}:{pwd_hash.hex()}"


def verify_password(stored_password: str, provided_password: str) -> bool:
    """
    Verify a stored password against a user-provided password.
    """
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        
        pwd_hash = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=provided_password.encode("utf-8"),
            salt=salt,
            iterations=100000,
        )
        return pwd_hash == expected_hash
    except Exception:
        return False


def register_user(username: str, password: str) -> str:
    """
    Register a new user in the database.
    
    Args:
        username: Desired username (case-insensitive checks recommended)
        password: Raw password string
        
    Returns:
        The string representation of the unique MongoDB user _id.
        
    Raises:
        ValueError: If username is already taken.
    """
    username_clean = username.strip().lower()
    if not username_clean:
        raise ValueError("Username cannot be empty.")
    if not password:
        raise ValueError("Password cannot be empty.")

    # Check if username already exists
    existing = users_collection.find_one({"username": username_clean})
    if existing:
        raise ValueError("Username already taken. Please choose another one.")

    password_hash = hash_password(password)
    now = datetime.datetime.now(datetime.timezone.utc)

    result = users_collection.insert_one({
        "username": username_clean,
        "password_hash": password_hash,
        "created_at": now,
    })

    return str(result.inserted_id)


def login_user(username: str, password: str) -> dict | None:
    """
    Authenticate a user.
    
    Args:
        username: Registered username
        password: Raw password
        
    Returns:
        A dictionary containing the authenticated user's details, or None if authentication fails.
    """
    username_clean = username.strip().lower()
    if not username_clean or not password:
        return None

    user = users_collection.find_one({"username": username_clean})
    if not user:
        return None

    if verify_password(user["password_hash"], password):
        return {
            "user_id": str(user["_id"]),
            "username": user["username"],
        }
    
    return None
