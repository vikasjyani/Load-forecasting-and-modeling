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
from app.dependencies import get_admin_service as get_admin_service_dependency
# No longer need the local get_admin_service function, will use Depends(get_admin_service_dependency) directly in routes.

from app.models.admin import ( # Import Pydantic models from app.models.admin
    SystemStatus, StorageInfo, LogEntry, RecentLogsResponse,
    AdminActionRequest, AdminActionResponse
)
# Define more specific Pydantic models for feature flags if needed, or use generic Dict/List
class FeatureConfig(BaseModel):
    id: str
    enabled: bool
    description: Optional[str] = None
    category: Optional[str] = None
    last_modified: Optional[str] = None

class FeatureCategoryResponse(BaseModel):
    features_by_category: Dict[str, List[FeatureConfig]]
    feature_groups: Dict[str, List[str]]
    total_features: int
    enabled_features_count: int
    metadata: Dict[str, Any]
    data_source_project: Optional[str] = None
    timestamp: str
    error: Optional[str] = None


class FeatureUpdatePayload(BaseModel):
    enabled: bool

class BulkFeatureUpdateItem(BaseModel): # Renamed from FeatureUpdatePayload to avoid clash if it was global
    enabled: bool

class BulkFeaturesUpdateRequest(BaseModel):
    features: Dict[str, BulkFeatureUpdateItem] # feature_id: {enabled: bool}
    project_name: Optional[str] = None

class BulkFeaturesUpdateResponse(BaseModel):
    message: str
    successful_updates: List[Dict[str, Any]]
    failed_updates: List[Dict[str, Any]]


class SystemCleanupPayload(BaseModel):
    type: str = Field(default="logs", description="Type of cleanup: 'logs', 'temp', 'cache', 'all'")
    max_age_days: int = Field(default=30, ge=1, le=365, description="Max age of files to keep for 'logs' or 'temp'")

class SystemCleanupResponse(BaseModel):
    overall_status: str
    details: Dict[str, Any]
    total_files_cleaned: int
    cleanup_type_requested: str
    max_age_days_for_logs_temp: int
    timestamp: str
    error: Optional[str] = None

class SystemInfoResponse(BaseModel): # Define a more structured response
    platform: Dict[str, Any]
    resources: Dict[str, Any]
    disk: Dict[str, Any]
    application: Dict[str, Any]
    timestamp: str
    error: Optional[str] = None

class SystemHealthResponse(BaseModel): # Define a more structured response
    overall_health: str
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_percent_project_data: float
    disk_free_gb_project_data: float
    application_components_health: Dict[str, Any]
    active_processes_count: int
    system_uptime_seconds: float
    timestamp: str
    error: Optional[str] = None


# --- API Endpoints ---

@router.get("/features", response_model=FeatureCategoryResponse, summary="Get Features Configuration")
async def get_features_api(
    project_name: Optional[str] = Query(None, description="Optional project name for project-specific features"),
    service: AdminService = Depends(get_admin_service_dependency)
):
    """Retrieves the current feature flag configuration, optionally for a specific project."""
    try:
        features_data = await service.list_features(project_name=project_name)
        if "error" in features_data and features_data["error"]:
            # If service indicates an error in its structure, make it an HTTP error
            raise ProcessingError(message=features_data["error"])
        return FeatureCategoryResponse(**features_data)
    except ProcessingError as e:
        # Handle errors that might come from the service layer if it's designed to return them this way
        # Or, if service raises exceptions directly, this might not be needed.
        raise HTTPException(status_code=500, detail=str(e.detail if hasattr(e, 'detail') else e))
    except Exception as e: # Catch-all for unexpected issues
        logger.exception("Error in get_features_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.put("/features/{feature_id}", summary="Update Feature Status", response_model=Dict[str, Any]) # Define a specific response model later
async def update_feature_api(
    feature_id: str = FastAPIPath(..., description="The ID of the feature to update"),
    payload: FeatureUpdatePayload,
    project_name: Optional[str] = Query(None, description="Optional project context for the feature update"),
    service: AdminService = Depends(get_admin_service_dependency)
):
    """Enables or disables a specific feature, optionally for a project."""
    try:
        result = await service.update_feature_status(
            feature_id, payload.enabled, project_name=project_name
        )
        if not result.get('success'):
            # Use detail from result if available, else generic message
            error_detail = result.get('error', f'Failed to update feature {feature_id}')
            raise ProcessingError(message=error_detail) # Or a more specific error type
        return result
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e.detail if hasattr(e, 'detail') else e)) # Bad request if processing failed due to input/logic
    except Exception as e:
        logger.exception(f"Error updating feature {feature_id}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/features/bulk_update", response_model=BulkFeaturesUpdateResponse, summary="Bulk Update Feature Statuses")
async def bulk_update_features_api(
    payload: BulkFeaturesUpdateRequest,
    service: AdminService = Depends(get_admin_service_dependency)
):
    """Allows updating multiple feature statuses in a single request."""
    try:
        # Convert payload.features from Dict[str, BulkFeatureUpdateItem] to Dict[str, bool] for service
        features_to_update_simple: Dict[str, bool] = {
            fid: item.enabled for fid, item in payload.features.items()
        }
        result = await service.bulk_update_features_status(
            updates=features_to_update_simple,
            project_name=payload.project_name
        )
        return BulkFeaturesUpdateResponse(**result)
    except Exception as e:
        logger.exception("Error in bulk_update_features_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during bulk update: {str(e)}")


@router.post("/system/cleanup", response_model=SystemCleanupResponse, summary="Perform System Cleanup")
async def system_cleanup_api(
    payload: SystemCleanupPayload,
    service: AdminService = Depends(get_admin_service_dependency)
):
    """Triggers system cleanup tasks like deleting old logs or temporary files."""
    try:
        cleanup_result = await service.perform_system_cleanup(
            cleanup_type=payload.type, max_age_days=payload.max_age_days
        )
        if "error" in cleanup_result and cleanup_result["error"]:
            raise ProcessingError(message=cleanup_result["error"])
        return SystemCleanupResponse(**cleanup_result)
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e.detail if hasattr(e, 'detail') else e))
    except Exception as e:
        logger.exception("Error in system_cleanup_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during system cleanup: {str(e)}")

@router.get("/system/info", response_model=SystemInfoResponse, summary="Get Comprehensive System Information")
async def system_info_api(service: AdminService = Depends(get_admin_service_dependency)):
    """Retrieves detailed system information, including platform, resources, and application status."""
    try:
        system_info = await service.get_comprehensive_system_info()
        if "error" in system_info and system_info["error"]:
            raise ProcessingError(message=system_info["error"])
        return SystemInfoResponse(**system_info)
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e.detail if hasattr(e, 'detail') else e))
    except Exception as e:
        logger.exception("Error in system_info_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/system/health", response_model=SystemHealthResponse, summary="Get System Health Metrics")
async def system_health_api(service: AdminService = Depends(get_admin_service_dependency)):
    """Provides real-time system health metrics (CPU, memory, disk, application health)."""
    try:
        health_data = await service.get_system_health_metrics()
        if "error" in health_data and health_data["error"]:
            raise ProcessingError(message=health_data["error"])
        return SystemHealthResponse(**health_data)
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e.detail if hasattr(e, 'detail') else e))
    except Exception as e:
        logger.exception("Error in system_health_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


logger.info("Admin API router defined for FastAPI, using AdminService.")
print("Admin API router defined for FastAPI, using AdminService.")
