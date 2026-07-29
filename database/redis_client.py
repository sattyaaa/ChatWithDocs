import os
import json
import logging
from redis import Redis
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

# Redis connection client instance
_redis_client = None
_redis_disabled = False


class MongoJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder to handle datetime objects, ObjectIds, and other 
    non-standard types when serializing documents for Redis caching.
    """
    def default(self, o):
        if hasattr(o, "isoformat"):
            return o.isoformat()
        try:
            from bson import ObjectId
            if isinstance(o, ObjectId):
                return str(o)
        except ImportError:
            pass
        if hasattr(o, "__str__"):
            return str(o)
        return super().default(o)


def get_redis_client() -> Redis | None:
    """
    Retrieves the Redis client instance. Attempts to connect if not already done.
    If Redis is disabled, unconfigured, or fails to connect, returns None.
    """
    global _redis_client, _redis_disabled
    if _redis_disabled:
        return None

    if _redis_client is not None:
        return _redis_client

    if not REDIS_URL:
        logger.warning("REDIS_URL is not set in environment variables. Redis caching is disabled.")
        _redis_disabled = True
        return None

    try:
        client = Redis.from_url(
            REDIS_URL,
            socket_timeout=3.0,
            socket_connect_timeout=3.0,
            decode_responses=True  # Automatically decodes responses to strings
        )
        # Test connection with a ping
        client.ping()
        _redis_client = client
        logger.info("Successfully connected to Redis server.")
        return _redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis at {REDIS_URL}: {e}. Redis caching will be disabled.")
        _redis_disabled = True
        return None


def cache_push_message(chat_id: str, message_dict: dict, ttl_seconds: int = 7200) -> bool:
    """
    Pushes a chat message into the Redis List cache for the chat session and sets a TTL.
    """
    client = get_redis_client()
    if client is None:
        return False

    key = f"chat:{chat_id}:messages"
    try:
        serialized_msg = json.dumps(message_dict, cls=MongoJSONEncoder)
        client.rpush(key, serialized_msg)
        client.expire(key, ttl_seconds)
        return True
    except Exception as e:
        logger.warning(f"Failed to write chat message to Redis cache: {e}")
        return False


def cache_get_messages(chat_id: str, limit: int | None = None) -> list[dict] | None:
    """
    Retrieves messages from the Redis cache.
    If key doesn't exist, returns None (cache miss).
    If limit is specified, returns the last 'limit' messages.
    """
    client = get_redis_client()
    if client is None:
        return None

    key = f"chat:{chat_id}:messages"
    try:
        # Check if the cache key exists first
        if not client.exists(key):
            return None

        # Fetch messages
        if limit is not None:
            start_index = -limit
            end_index = -1
        else:
            start_index = 0
            end_index = -1

        raw_messages = client.lrange(key, start_index, end_index)
        
        # Deserialize JSON strings
        messages = []
        for raw in raw_messages:
            messages.append(json.loads(raw))
        return messages
    except Exception as e:
        logger.warning(f"Failed to read chat messages from Redis cache: {e}")
        return None


def cache_clear(chat_id: str) -> bool:
    """
    Clears the Redis cache list for the chat session.
    """
    client = get_redis_client()
    if client is None:
        return False

    key = f"chat:{chat_id}:messages"
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Failed to clear Redis cache for chat {chat_id}: {e}")
        return False
