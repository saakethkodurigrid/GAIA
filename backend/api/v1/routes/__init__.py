"""
API routes module.
"""
from api.v1.routes.auth import router as auth_router
from api.v1.routes.admin import router as admin_router
from api.v1.routes.candidate import router as candidate_router
from api.v1.routes.system_design import router as system_design_router

__all__ = ['auth_router', 'admin_router', 'candidate_router', 'system_design_router']


