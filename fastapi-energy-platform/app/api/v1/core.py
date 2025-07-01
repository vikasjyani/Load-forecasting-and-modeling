# fastapi-energy-platform/app/api/v1/core.py
"""
Core API Endpoints for FastAPI (e.g., health checks, system info)
Adapted from the Flask core_bp.py, focusing on API-relevant parts.
HTML rendering routes are typically handled by a separate frontend or specific FastAPI HTMLResponse endpoints.
"""
import logging
import time # For performance timing if needed
from typing import Dict, Any, List, Optional
from pathlib import Path # Added Path import
from fastapi import APIRouter, Depends, Query, HTTPException, Request, Body
from pydantic import BaseModel, Field # Added Field
import asyncio # For concurrent operations if any
from fastapi.responses import JSONResponse # Added JSONResponse
from datetime import datetime # Added datetime for health check

# Assuming CoreService is adapted for FastAPI and available for DI.
# For now, using a placeholder if not fully refactored.
try:
    from app.services.core_service import CoreService # This service needs to be created/adapted
except ImportError:
    logging.warning("CoreService not found, using placeholder for core API.")
    class CoreService: # Placeholder
        def __init__(self, project_path: Optional[Path] = None): self.project_path = project_path
        async def get_dashboard_data(self, include_details: bool = False) -> Dict[str, Any]:
            await asyncio.sleep(0.01) # Simulate async
            return {"message": "Mock Dashboard Data", "details_included": include_details}
        async def get_project_status(self, include_details: bool = False) -> Dict[str, Any]:
            return {"status": "Mock Project OK", "details": include_details}
        async def get_project_details(self) -> Dict[str, Any]: return {"details": "Mock Project Details"}
        async def get_system_info(self) -> Dict[str, Any]: return {"system": "Mock System Info", "version": "1.0"}
        async def get_health_status(self) -> Dict[str, Any]: return {"status": "healthy", "components": {"db": "ok"}}
        async def get_navigation_data(self) -> Dict[str, Any]: return {"items": [{"name": "Home", "path": "/"}]}
        async def get_recent_activities(self, limit: int = 10, activity_type: str = 'all') -> List[Dict]:
            return [{"activity": f"Mock activity {i} of type {activity_type}" for i in range(limit)}]
        async def get_performance_metrics(self) -> Dict[str, Any]: return {"cpu": "10%", "memory": "20%"}
        async def clear_caches(self, cache_types: List[str]) -> List[str]: return cache_types
        async def get_feature_flags(self) -> Dict[str, Any]: return {"feature_x": True}
        async def get_notifications(self) -> List[Dict]: return [{"id": 1, "message": "Mock notification"}]

# Custom error handlers are registered globally, but custom exceptions can be raised.
from app.utils.error_handlers import ProcessingError, ResourceNotFoundError # Assuming these are defined

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for CoreService ---
async def get_core_service():
    return CoreService()


# --- Pydantic Models ---
class CacheClearPayload(BaseModel):
    cache_types: List[str] = Field(default=["all"], example=[ "all", "feature_flags", "user_data"])


# --- API Endpoints (Adapted from Flask blueprint) ---

@router.get("/dashboard_data", summary="Get Dashboard Data")
async def get_dashboard_data_api(
    include_details: bool = Query(False, description="Whether to include detailed information"),
    service: CoreService = Depends(get_core_service)
):
    try:
        data = await service.get_dashboard_data(include_details=include_details)
        return data
    except Exception as e:
        logger.exception("Error in get_dashboard_data_api")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard data: {str(e)}")

@router.get("/project_status", summary="Get Current Project Status")
async def get_project_status_api(
    include_details: bool = Query(False),
    service: CoreService = Depends(get_core_service)
):
    try:
        status = await service.get_project_status(include_details=include_details)
        return status
    except Exception as e:
        logger.exception("Error in get_project_status_api")
        raise HTTPException(status_code=500, detail=f"Failed to get project status: {str(e)}")


@router.get("/system_info", summary="Get System Information")
async def get_system_info_api(service: CoreService = Depends(get_core_service)):
    try:
        info = await service.get_system_info()
        return info
    except Exception as e:
        logger.exception("Error in get_system_info_api")
        raise HTTPException(status_code=500, detail=f"Failed to get system info: {str(e)}")


@router.get("/health", summary="Application Health Check")
async def health_check_api(service: CoreService = Depends(get_core_service)):
    try:
        health = await service.get_health_status()
        status_code = 200 if health.get('status') == 'healthy' else 503
        return JSONResponse(content=health, status_code=status_code)
    except Exception as e:
        logger.exception("Error in health_check_api")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=503)


@router.get("/recent_activities", summary="Get Recent Activities")
async def get_recent_activities_api(
    limit: int = Query(10, ge=1, le=100),
    activity_type: str = Query("all"),
    service: CoreService = Depends(get_core_service)
):
    try:
        activities = await service.get_recent_activities(limit=limit, activity_type=activity_type)
        return {"activities": activities, "limit": limit, "type_filter": activity_type}
    except Exception as e:
        logger.exception("Error in get_recent_activities_api")
        raise HTTPException(status_code=500, detail=f"Failed to get recent activities: {str(e)}")

@router.post("/clear_cache", summary="Clear Application Caches")
async def clear_cache_api(
    payload: CacheClearPayload,
    service: CoreService = Depends(get_core_service)
):
    try:
        cleared = await service.clear_caches(cache_types=payload.cache_types)
        return {"message": "Caches cleared successfully.", "cleared_caches": cleared}
    except Exception as e:
        logger.exception("Error in clear_cache_api")
        raise HTTPException(status_code=500, detail=f"Failed to clear caches: {str(e)}")

@router.get("/feature_flags", summary="Get UI Feature Flags")
async def get_feature_flags_api(service: CoreService = Depends(get_core_service)):
    try:
        flags = await service.get_feature_flags()
        return flags
    except Exception as e:
        logger.exception("Error in get_feature_flags_api")
        raise HTTPException(status_code=500, detail=f"Failed to get feature flags: {str(e)}")

logger.info("Core API router (general app endpoints) defined for FastAPI.")
print("Core API router (general app endpoints) defined for FastAPI.")
