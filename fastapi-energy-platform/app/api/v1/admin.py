# fastapi-energy-platform/app/api/v1/admin.py
"""
Admin API Endpoints for FastAPI
Handles system administration, feature management, and monitoring.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body # Added Body
from pydantic import BaseModel, Field # For request/response models

# Assuming AdminService is adapted and available for DI
# from app.services.admin_service import AdminService
# Placeholder if AdminService is not yet ready for DI or needs instantiation
# For now, we'll define a placeholder AdminService if not importable
try:
    from app.services.admin_service import AdminService
except ImportError:
    logging.warning("AdminService not found, using placeholder for admin API.")
    class AdminService: # Placeholder
        async def get_features_configuration(self, project_name: Optional[str] = None) -> Dict[str, Any]:
            return {"features": {"mock_feature": {"enabled": True, "description": "Mocked"}}, "feature_groups": {}, "metadata": {}, "error": "Using Placeholder AdminService"}
        async def update_feature_status(self, feature_id: str, enabled: bool, project_name: Optional[str] = None) -> Dict[str, Any]:
            return {"success": True, "feature_id": feature_id, "enabled": enabled, "message": "Mocked update"}
        async def bulk_update_features(self, features_updates: Dict[str, Dict], project_name: Optional[str] = None) -> Dict[str, Any]:
            return {"successful_updates": list(features_updates.keys()), "failed_updates": [], "message": "Mocked bulk update"}
        async def perform_system_cleanup(self, cleanup_type: str = 'logs', max_age_days: int = 30) -> Dict[str, Any]:
            return {"cleanup_results": {"logs": {"cleaned_files": ["mock.log"]}}, "total_files_cleaned": 1, "message": "Mocked cleanup"}
        async def get_comprehensive_system_info(self) -> Dict[str, Any]:
            return {"system_info": {"platform": "mock"}, "message": "Mocked system info"}
        async def get_system_health_metrics(self) -> Dict[str, Any]:
            return {"overall_health": "healthy", "cpu_percent": 10, "message": "Mocked health"}

# Custom error handlers from app.utils.error_handlers
# These would be registered globally in main.py, but custom exceptions can be raised from here.
from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for AdminService ---
# This is a simplified way to get the service. In a larger app, you might have a more complex DI setup.
# For now, we assume AdminService can be instantiated directly or we use the placeholder.
# If actual DI is set up (e.g., with FastAPI-Limiter, or custom provider):
# async def get_admin_service(service: AdminService = Depends()):
# return service
# For now:
async def get_admin_service():
    # This path would be configured, e.g. via settings
    # For project-specific features, AdminService might need project_data_root
    # and the specific project_name would be passed to its methods.
    # global_feature_config_path = Path(app.state.settings.GLOBAL_FEATURES_PATH) # Example
    # project_data_root_path = Path(app.state.settings.PROJECTS_DATA_ROOT) # Example
    # return AdminService(global_feature_config_path, project_data_root_path)
    return AdminService() # Using placeholder or default constructor for now

# --- Pydantic Models for Request/Response ---
class FeatureUpdatePayload(BaseModel):
    enabled: bool

class BulkFeatureUpdatePayload(BaseModel):
    features: Dict[str, FeatureUpdatePayload] # feature_id: {enabled: bool}
    project_name: Optional[str] = None # Optional project context

class SystemCleanupPayload(BaseModel):
    type: str = Field(default="logs", description="Type of cleanup: 'logs', 'temp', 'cache', 'all'")
    max_age_days: int = Field(default=30, ge=1, le=365, description="Max age of files to keep for 'logs' or 'temp'")


# --- API Endpoints ---

@router.get("/features", summary="Get Features Configuration")
async def get_features_api(
    project_name: Optional[str] = None, # Query parameter for project-specific features
    service: AdminService = Depends(get_admin_service)
):
    """Retrieves the current feature flag configuration, optionally for a specific project."""
    try:
        features_data = await service.get_features_configuration(project_name=project_name)
        if "error" in features_data: # Check if service returned an error structure
            raise ProcessingError(message=features_data["error"])
        return features_data
    except Exception as e:
        logger.exception("Error in get_features_api")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/features/{feature_id}", summary="Update Feature Status")
async def update_feature_api(
    feature_id: str,
    payload: FeatureUpdatePayload,
    project_name: Optional[str] = None, # Query parameter
    service: AdminService = Depends(get_admin_service)
):
    """Enables or disables a specific feature, optionally for a project."""
    try:
        result = await service.update_feature_status(
            feature_id, payload.enabled, project_name=project_name
        )
        if not result.get('success'):
            raise BusinessLogicError(message=result.get('error', 'Failed to update feature'))
        return result
    except BusinessLogicError as e:
        raise e # Re-raise to be handled by global exception handler
    except Exception as e:
        logger.exception(f"Error updating feature {feature_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/bulk_update", summary="Bulk Update Feature Statuses")
async def bulk_update_features_api(
    payload: BulkFeatureUpdatePayload,
    service: AdminService = Depends(get_admin_service)
):
    """Allows updating multiple feature statuses in a single request."""
    try:
        # Convert payload to the structure expected by the service
        features_to_update_service_format: Dict[str, Dict] = {
            fid: {"enabled": f_payload.enabled} for fid, f_payload in payload.features.items()
        }
        result = await service.bulk_update_features(
            features_updates=features_to_update_service_format,
            project_name=payload.project_name
        )
        return result
    except Exception as e:
        logger.exception("Error in bulk_update_features_api")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/system/cleanup", summary="Perform System Cleanup")
async def system_cleanup_api(
    payload: SystemCleanupPayload,
    service: AdminService = Depends(get_admin_service)
):
    """Triggers system cleanup tasks like deleting old logs or temporary files."""
    try:
        cleanup_result = await service.perform_system_cleanup(
            cleanup_type=payload.type, max_age_days=payload.max_age_days
        )
        if "error" in cleanup_result:
            raise ProcessingError(message=cleanup_result["error"])
        return cleanup_result
    except Exception as e:
        logger.exception("Error in system_cleanup_api")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/info", summary="Get Comprehensive System Information")
async def system_info_api(service: AdminService = Depends(get_admin_service)):
    """Retrieves detailed system information, including platform, resources, and application status."""
    try:
        system_info = await service.get_comprehensive_system_info()
        if "error" in system_info:
            raise ProcessingError(message=system_info["error"])
        return system_info
    except Exception as e:
        logger.exception("Error in system_info_api")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/health", summary="Get System Health Metrics")
async def system_health_api(service: AdminService = Depends(get_admin_service)):
    """Provides real-time system health metrics (CPU, memory, disk, application health)."""
    try:
        health_data = await service.get_system_health_metrics()
        if "error" in health_data:
            raise ProcessingError(message=health_data["error"])
        return health_data
    except Exception as e:
        logger.exception("Error in system_health_api")
        raise HTTPException(status_code=500, detail=str(e))

# Note: The original Flask blueprint had HTML rendering routes.
# For a FastAPI backend, these are typically not included if the frontend is separate (e.g., React).
# If admin UI pages are to be served by FastAPI, they would use HTMLResponse and Jinja2Templates.
# For now, only API endpoints are translated.

logger.info("Admin API router defined for FastAPI.")
print("Admin API router defined for FastAPI.")
