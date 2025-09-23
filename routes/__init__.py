"""
Routes package initialization
Date: 2025-08-27 02:41:32 UTC
User: HarrisonKuo47
"""

from . import upload_routes
from . import analysis_routes  
from . import view_routes
from . import api_routes

__all__ = ['upload_routes', 'analysis_routes', 'view_routes', 'api_routes']