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
    
    # Groq LLM Configuration (for MCQ RAG generation)
    GROQ_API_KEY: str = os.getenv('GROQ_API_KEY', '')
    
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
    
    # Resume Score Threshold for Auto-Sending Scheduling Invitations
    RESUME_SCORE_THRESHOLD: float = float(os.getenv('RESUME_SCORE_THRESHOLD', '70.0'))
    
    # Google OAuth Scopes
    GOOGLE_SCOPES: list = [
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'
    ]


settings = Settings()


