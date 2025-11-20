"""
Role model for ROLE_TABLE.
"""
from sqlalchemy import Column, Integer, String
from core.database import Base


class Role(Base):
    """Role model representing ROLE_TABLE."""
    
    __tablename__ = 'role_table'
    
    role_id = Column(Integer, primary_key=True, index=True)
    role = Column(String(20), nullable=False)




