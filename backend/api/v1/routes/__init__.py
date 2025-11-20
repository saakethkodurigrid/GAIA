"""
API routes module.
"""
from api.v1.routes.auth import router as auth_router
from api.v1.routes.admin import router as admin_router
from api.v1.routes.candidate import router as candidate_router

__all__ = ['auth_router', 'admin_router', 'candidate_router']


