from fastapi import APIRouter
from .v1 import admin, auth, core, data, demand_projection, demand_visualization, loadprofile, loadprofile_analysis, projects, pypsa, colors

api_router = APIRouter()

api_router.include_router(admin.router, prefix="/v1", tags=["admin"])
api_router.include_router(auth.router, prefix="/v1", tags=["auth"])
api_router.include_router(core.router, prefix="/v1", tags=["core"])
api_router.include_router(data.router, prefix="/v1", tags=["data"])
api_router.include_router(demand_projection.router, prefix="/v1", tags=["demand_projection"])
api_router.include_router(demand_visualization.router, prefix="/v1", tags=["demand_visualization"])
api_router.include_router(loadprofile.router, prefix="/v1", tags=["loadprofile"])
api_router.include_router(loadprofile_analysis.router, prefix="/v1", tags=["loadprofile_analysis"])
api_router.include_router(projects.router, prefix="/v1", tags=["projects"])
api_router.include_router(pypsa.router, prefix="/v1", tags=["pypsa"])
api_router.include_router(colors.router, prefix="/v1", tags=["colors"])
