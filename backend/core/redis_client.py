import redis
import logging
from typing import Optional
from core.config import settings
logger = logging.getLogger(__name__)
# Global Redis client instance
_redis_client: Optional[redis.Redis] = None
def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance.
    Supports REDIS_URL connection string (preferred) or individual settings.
    Returns:
        Redis client instance
    Raises:
        ConnectionError: If Redis connection fails
    """
    global _redis_client
    if _redis_client is None:
        try:
            # Configure SSL bypass for local development (DEBUG=True)
            # This is critical for connecting to Azure Redis from local machines without certificates
            ssl_params = {}
            if settings.DEBUG:
                import ssl
                ssl_params['ssl_cert_reqs'] = ssl.CERT_NONE
            # Prefer connection string if provided
            if settings.REDIS_URL:
                _redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=15,  # Increased for SSL/TLS handshake with Azure Redis
                    socket_timeout=60,  # Increased for bulk write operations with pipeline
                    **ssl_params
                )
                logger.info("Redis connection established via REDIS_URL")
            else:
                # Fallback to individual settings
                connection_params = {
                    'host': settings.REDIS_HOST,
                    'port': settings.REDIS_PORT,
                    'db': settings.REDIS_DB,
                    'decode_responses': True,
                    'socket_connect_timeout': 15,  # Increased for SSL/TLS handshake with Azure Redis
                    'socket_timeout': 60,  # Increased for bulk write operations with pipeline
                    'socket_connect_timeout': 15,  # Increased for SSL/TLS handshake with Azure Redis
                    'socket_timeout': 60,  # Increased for bulk write operations with pipeline
                }
                # Add SSL params if valid
                connection_params.update(ssl_params)
                if settings.REDIS_PASSWORD:
                    connection_params['password'] = settings.REDIS_PASSWORD
                _redis_client = redis.Redis(**connection_params)
                logger.info(f"Redis connection established: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            # Test connection
            _redis_client.ping()
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error initializing Redis client: {str(e)}")
            raise
    return _redis_client
def close_redis_client():
    """Close Redis client connection."""
    global _redis_client
    if _redis_client:
        _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")
