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

import platform
import sys
# Assuming CoreService is adapted for FastAPI and available for DI.
# For now, using a placeholder if not fully refactored.
# try:
#     from app.services.core_service import CoreService # This service needs to be created/adapted
# except ImportError:
#     logging.warning("CoreService not found, using placeholder for core API.")
# No specific core_service.py, implementing directly here or enhancing this placeholder.

class CoreService:
    def __init__(self, project_path: Optional[Path] = None):
        self.project_path = project_path
        # In-memory cache example for feature flags or simple data
        self._cache = {}

    async def get_dashboard_data(self, include_details: bool = False) -> Dict[str, Any]:
        # This would eventually fetch real dashboard data
        await asyncio.sleep(0.01) # Simulate async I/O
        return {"message": "Dashboard data: Overview of operations.", "details_included": include_details, "timestamp": datetime.now().isoformat()}

    async def get_project_status(self, include_details: bool = False) -> Dict[str, Any]:
        # This would check the current project's status
        # For now, a placeholder. It might depend on a project context/manager service.
        if self.project_path:
            return {"status": f"Project at {self.project_path} loaded (mock status).", "details": include_details}
        return {"status": "No active project (mock status).", "details": include_details}

    async def get_project_details(self) -> Dict[str, Any]:
        # Placeholder, would fetch detailed project metadata
        return {"details": "Mock Project Details: configuration, files, etc."}

    async def get_system_info(self) -> Dict[str, Any]:
        return {
            "system_time": datetime.now().isoformat(),
            "os_platform": platform.platform(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version,
            "architecture": platform.machine(),
        }

    async def get_health_status(self) -> Dict[str, Any]:
        # Basic health check, could be expanded to check DB, external services, etc.
        # For now, it assumes the API itself being up means "healthy".
        # Components could be checked: e.g., database connection, disk space
        components_status = {
            "api_service": "healthy",
            "database": "not_checked", # Placeholder
            "disk_space": "not_checked" # Placeholder
        }
        overall_healthy = all(status == "healthy" or status == "not_checked" for status in components_status.values()) # Modify logic as needed

        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": datetime.now().isoformat(),
            "components": components_status
        }

    async def get_navigation_data(self) -> Dict[str, Any]:
        # Placeholder for navigation structure, could be dynamic based on user roles/features
        return {"items": [
            {"name": "Dashboard", "path": "/dashboard", "icon": "home"},
            {"name": "Projects", "path": "/projects", "icon": "folder"},
            {"name": "Demand Projection", "path": "/demand-projection", "icon": "chart-line"},
            # Add other navigation items
        ]}

    async def get_recent_activities(self, limit: int = 10, activity_type: str = 'all') -> List[Dict]:
        # Placeholder, this would typically fetch from a log or event store
        return [{"id": i, "activity": f"Mock activity {i} of type {activity_type}", "timestamp": datetime.now().isoformat()} for i in range(1, limit + 1)]

    async def get_performance_metrics(self) -> Dict[str, Any]:
        # Placeholder, could integrate with psutil or similar for actual metrics
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_usage = psutil.cpu_percent(interval=0.1) # Non-blocking, short interval
            return {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory.percent,
                "available_memory_gb": round(memory.available / (1024**3), 2),
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            return {"cpu_usage_percent": "N/A (psutil not installed)", "memory_usage_percent": "N/A", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            logger.warning(f"Could not retrieve performance metrics: {e}")
            return {"error": "Could not retrieve performance metrics", "timestamp": datetime.now().isoformat()}


    async def clear_caches(self, cache_types: List[str]) -> Dict[str, str]:
        cleared_status = {}
        if "all" in cache_types or "feature_flags" in cache_types:
            if "feature_flags" in self._cache:
                del self._cache["feature_flags"]
            cleared_status["feature_flags_cache"] = "cleared"
        if "all" in cache_types or "user_data" in cache_types:
            # Add logic for other cache types if they exist
            cleared_status["user_data_cache"] = "cleared (mock)"

        if not cleared_status and "all" not in cache_types:
             return {"message": "No specific caches matching types to clear.", "cleared_caches": cache_types}
        elif not cleared_status and "all" in cache_types:
             self._cache.clear() # Clear all in-memory cache for this service
             return {"message": "All service-level caches cleared.", "cleared_caches": ["all"]}
        return {"message": "Selected caches cleared.", "cleared_status": cleared_status}


    async def get_feature_flags(self) -> Dict[str, Any]:
        if "feature_flags" not in self._cache:
            # Simulate fetching or defining feature flags
            await asyncio.sleep(0.01) # Simulate I/O
            self._cache["feature_flags"] = {
                "newDashboard": True,
                "detailedAnalysis": False,
                "experimentalPypsaDirectImport": True,
                "cloudSaveEnabled": False,
                "updated_at": datetime.now().isoformat()
            }
        return self._cache["feature_flags"]

    async def get_notifications(self) -> List[Dict]:
        # Placeholder, could fetch from a notification system or database
        return [
            {"id": 1, "message": "System maintenance scheduled for Sunday.", "type": "info", "timestamp": datetime.now().isoformat()},
            {"id": 2, "message": "New PyPSA version available for modeling.", "type": "update", "timestamp": datetime.now().isoformat()}
        ]

# Custom error handlers are registered globally, but custom exceptions can be raised.
# from app.utils.error_handlers import ProcessingError, ResourceNotFoundError # Assuming these are defined
# Using standard HTTPException for now or custom ones if they are defined in app.core.exceptions
from app.core.exceptions import AppException, ResourceNotFoundError, ConfigurationError

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
