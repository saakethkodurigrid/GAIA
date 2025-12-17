"""
System configuration model for storing application-wide settings.
"""
from sqlalchemy import Column, String, Text, DateTime, func
from core.database import Base


class SystemConfig(Base):
    """System configuration model for storing application-wide settings."""
    
    __tablename__ = 'system_config'
    
    config_key = Column(String(255), primary_key=True, index=True)
    config_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    updated_by = Column(String(255), nullable=True)  # Email of admin who updated it

