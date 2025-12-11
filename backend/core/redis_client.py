"""
Redis client for caching and temporary storage.
"""
import ssl
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
            # Prefer connection string if provided
            if settings.REDIS_URL:
                # redis-py 5.0+: SSL is automatic with rediss:// URLs
                # No need to pass ssl parameters explicitly
                if 'rediss://' in settings.REDIS_URL or ':6380' in settings.REDIS_URL:
                    logger.info("Redis connection using SSL/TLS (via rediss:// scheme)")
                
                _redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                logger.info("Redis connection established via REDIS_URL")
            else:
                # Fallback to individual settings
                connection_params = {
                    'host': settings.REDIS_HOST,
                    'port': settings.REDIS_PORT,
                    'db': settings.REDIS_DB,
                    'decode_responses': True,
                    'socket_connect_timeout': 5,
                    'socket_timeout': 5,
                }
                
                if settings.REDIS_PASSWORD:
                    connection_params['password'] = settings.REDIS_PASSWORD
                
                # Add SSL for Azure Redis (port 6380)
                if settings.REDIS_PORT == 6380:
                    connection_params['ssl'] = True
                    connection_params['ssl_cert_reqs'] = ssl.CERT_NONE
                    logger.info("Redis connection using SSL/TLS")
                
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

