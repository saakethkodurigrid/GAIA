"""
Core configuration settings for the application.
Loads environment variables and provides configuration constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Server Configuration
    PORT: int = int(os.getenv('PORT', '5000'))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    DEBUG: bool = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Database Configuration
    DATABASE_URL: str = os.getenv('DATABASE_URL', '')
    
    # Backend URL Configuration (for OAuth redirect)
    # Use this to configure the backend URL for local or develop environment
    # Examples: http://localhost:5000 or https://api-dev.yourdomain.com
    BACKEND_URL: str = os.getenv('BACKEND_URL', 'http://localhost:5000')
    
    # Frontend URL Configuration (for OAuth redirect)
    # Use this to configure the frontend URL for redirecting after authentication
    # Examples: http://localhost:5175 or https://yourdomain.com
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:5175')
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str = os.getenv('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET: str = os.getenv('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI: str = os.getenv('GOOGLE_REDIRECT_URI', '')
    
    # Company Domain
    COMPANY_DOMAIN: str = os.getenv('COMPANY_DOMAIN', '')
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv('LLM_PROVIDER', 'anthropic')  # 'groq' or 'anthropic'
    
    # Groq LLM Configuration
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    GROQ_DEFAULT_MODEL: str = os.getenv('GROQ_DEFAULT_MODEL', 'llama-3.1-8b-instant')
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY: str = os.getenv('ANTHROPIC_API_KEY', '')
    # Note: Common model names: claude-sonnet-4-20250514, claude-3-5-sonnet-20240620, claude-3-opus-20240229, claude-3-haiku-20240307
    # claude-3-5-sonnet-20241022 was deprecated and retired
    ANTHROPIC_DEFAULT_MODEL: str = os.getenv('ANTHROPIC_DEFAULT_MODEL', 'claude-sonnet-4-20250514')
    
    # Azure Blob Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '')
    IMAGE_CONTAINER_NAME: str = os.getenv('IMAGE_CONTAINER_NAME', 'user-images')
    VIDEO_CONTAINER_NAME: str = os.getenv('VIDEO_CONTAINER_NAME', 'user-videos')
    
    # Email Configuration
    MAIL_USERNAME: str = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD: str = os.getenv('MAIL_PASSWORD', '')
    MAIL_FROM: str = os.getenv('MAIL_FROM', '')
    MAIL_FROM_NAME: str = os.getenv('MAIL_FROM_NAME', 'TechInterview Platform')
    MAIL_PORT: int = int(os.getenv('MAIL_PORT', '587'))
    MAIL_SERVER: str = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_STARTTLS: bool = os.getenv('MAIL_STARTTLS', 'True').lower() == 'true'
    MAIL_SSL_TLS: bool = os.getenv('MAIL_SSL_TLS', 'False').lower() == 'true'
    MAIL_USE_CREDENTIALS: bool = os.getenv('MAIL_USE_CREDENTIALS', 'True').lower() == 'true'
    MAIL_VALIDATE_CERTS: bool = os.getenv('MAIL_VALIDATE_CERTS', 'True').lower() == 'true'
    EMAIL_ENABLED: bool = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'
    
    # AWS SES Configuration
    AWS_SES_REGION: str = os.getenv('AWS_SES_REGION', 'us-east-1')
    AWS_ACCESS_KEY_ID: str = os.getenv('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY: str = os.getenv('AWS_SECRET_ACCESS_KEY', '')
    AWS_SES_SOURCE_EMAIL: str = os.getenv('AWS_SES_SOURCE_EMAIL', '')
    
    # Resume Score Threshold for Auto-Sending Scheduling Invitations
    RESUME_SCORE_THRESHOLD: float = float(os.getenv('RESUME_SCORE_THRESHOLD', '30.0'))
    
    # Redis Configuration
    # Use connection string if provided, otherwise fall back to individual settings
    REDIS_URL: str = os.getenv('REDIS_URL', '')
    # Fallback settings (only used if REDIS_URL is not provided)
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '')
    REDIS_DB: int = int(os.getenv('REDIS_DB', '0'))
    
    # Test Session Configuration
    HEARTBEAT_INTERVAL_SECONDS: int = int(os.getenv('HEARTBEAT_INTERVAL_SECONDS', '120'))  # 2 minutes
    STALE_TEST_THRESHOLD_MINUTES: int = int(os.getenv('STALE_TEST_THRESHOLD_MINUTES', '5'))  # 5 minutes
    BACKGROUND_SYNC_INTERVAL_MINUTES: int = int(os.getenv('BACKGROUND_SYNC_INTERVAL_MINUTES', '5'))  # 5 minutes
    REDIS_TTL_SECONDS: int = int(os.getenv('REDIS_TTL_SECONDS', '86400'))  # 24 hours
    
    # Coding Question Assignment Configuration
    RANDOM_CODING_QUESTIONS: bool = os.getenv('RANDOM_CODING_QUESTIONS', 'False').lower() == 'true'
    
    # Code Execution Service Configuration
    CODE_EXECUTION_URL: str = os.getenv('CODE_EXECUTION_URL', 'http://localhost:8000')
    
    # Google OAuth Scopes
    GOOGLE_SCOPES: list = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'
    ]


settings = Settings()


