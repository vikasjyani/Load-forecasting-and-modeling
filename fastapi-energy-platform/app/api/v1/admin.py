# fastapi-energy-platform/app/api/v1/admin.py
"""
Admin API Endpoints for FastAPI
Handles system administration, feature management, and monitoring.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query
from pydantic import BaseModel, Field # For request/response models

# Assuming AdminService is adapted and available for DI
# from app.services.admin_service import AdminService
# Placeholder if AdminService is not yet ready for DI or needs instantiation
# For now, we'll define a placeholder AdminService if not importable
try:
    from app.services.admin_service import AdminService
except ImportError:
    # This case should ideally not happen if dependencies are correctly managed.
    # If it does, the app might not start correctly due to missing dependency.
    # For robustness in case of partial deployments or issues, we could log heavily or raise an import error.
    logger.error("CRITICAL: AdminService could not be imported. Admin API will not function.")
    # Fallback to a dummy service to allow app to potentially start but endpoints will fail informatively.
    class AdminService: # type: ignore
        async def __getattr__(self, name):
            async def method(*args, **kwargs):
                logger.error(f"AdminService not available. Method {name} called with {args} and {kwargs}")
                return {"error": "AdminService is not available due to an import error.", "details": f"Method {name} could not be executed."}
            return method

# Custom error handlers from app.utils.error_handlers
# These would be registered globally in main.py, but custom exceptions can be raised from here.
# from app.utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError # Not directly used here now

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for AdminService ---
from app.dependencies import get_admin_service

# Pydantic Models for Admin API.
# These models should align with the data structures returned by AdminService.

class FeatureConfig(BaseModel):
    id: str
    enabled: bool
    description: Optional[str] = None
    category: Optional[str] = None
    last_modified: Optional[str] = None
    project_specific_description: Optional[str] = None

class FeatureCategoryResponse(BaseModel):
    features_by_category: Dict[str, List[FeatureConfig]] # Key is category display name
    feature_groups: Dict[str, List[str]] # Key is category internal ID
    total_features: int
    enabled_features_count: int
    metadata: Dict[str, Any]
    data_source_project: Optional[str] = None
    timestamp: str
    error: Optional[str] = None

class FeatureUpdatePayload(BaseModel):
    enabled: bool

class FeatureUpdateResponseItem(BaseModel): # For individual feature update results
    feature_id: str
    enabled: bool
    message: str
    error: Optional[str] = None

class FeatureUpdateResponse(BaseModel): # For single feature update endpoint
    success: bool
    feature_id: str
    enabled: bool
    message: str
    error: Optional[str] = None


class BulkFeatureUpdateItem(BaseModel):
    enabled: bool

class BulkFeaturesUpdateRequest(BaseModel):
    features: Dict[str, BulkFeatureUpdateItem] # feature_id: {enabled: bool}
    project_name: Optional[str] = None

class BulkFeaturesUpdateResponse(BaseModel): # Matches service output
    message: str
    successful_updates: List[FeatureUpdateResponseItem] # More specific type
    failed_updates: List[FeatureUpdateResponseItem] # More specific type

class SystemCleanupPayload(BaseModel):
    type: str = Field(default="logs", description="Type of cleanup: 'logs', 'temp', 'cache', 'all', 'none'")
    max_age_days: int = Field(default=30, ge=1, le=365, description="Max age of files to keep for 'logs' or 'temp'")

class SystemCleanupResponse(BaseModel): # Matches service output
    overall_status: str
    details: Dict[str, Any] # Could be more specific if structure is fixed
    total_files_cleaned: int
    cleanup_type_requested: str
    max_age_days_for_logs_temp: int
    timestamp: str
    error: Optional[str] = None

class SystemInfoResponse(BaseModel): # Matches service output
    platform: Dict[str, Any]
    resources: Dict[str, Any]
    disk: Dict[str, Any]
    application: Dict[str, Any]
    timestamp: str
    error: Optional[str] = None

class SystemHealthResponse(BaseModel): # Matches service output
    overall_health: str
    cpu_percent: Optional[float] = None # Optional if psutil fails for some reason
    memory_percent: Optional[float] = None
    memory_available_gb: Optional[float] = None
    disk_percent_project_data: Optional[float] = None
    disk_free_gb_project_data: Optional[float] = None
    application_components_health: Dict[str, Any]
    active_processes_count: Optional[int] = None
    system_uptime_seconds: Optional[float] = None
    timestamp: str
    error: Optional[str] = None


# --- API Endpoints ---

@router.get("/features", response_model=FeatureCategoryResponse, summary="Get Features Configuration")
async def get_features_api(
    project_name: Optional[str] = Query(None, description="Optional project name for project-specific features"),
    service: AdminService = Depends(get_admin_service)
):
    """Retrieves the current feature flag configuration, optionally for a specific project."""
    try:
        features_data = await service.list_features(project_name=project_name)
        if features_data.get("error"):
            raise HTTPException(status_code=500, detail=features_data["error"])
        # The service now directly returns a dict that should match FeatureCategoryResponse
        return FeatureCategoryResponse(**features_data)
    except HTTPException: # Re-raise if it's already an HTTPException
        raise
    except Exception as e:
        logger.exception(f"Error in get_features_api for project '{project_name}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.put("/features/{feature_id}", response_model=FeatureUpdateResponse, summary="Update Feature Status")
async def update_feature_api(
    feature_id: str = Path(..., description="The ID of the feature to update"),
    payload: FeatureUpdatePayload,
    project_name: Optional[str] = Query(None, description="Optional project context for the feature update"),
    service: AdminService = Depends(get_admin_service)
):
    """Enables or disables a specific feature, optionally for a project."""
    try:
        result = await service.update_feature_status(
            feature_id, payload.enabled, project_name=project_name
        )
        if not result.get('success'):
            status_code = 404 if "not found" in result.get('message', '').lower() else 400
            raise HTTPException(status_code=status_code, detail=result.get('message') or result.get('error', 'Failed to update feature'))
        return FeatureUpdateResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating feature {feature_id} for project '{project_name}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/features/bulk_update", response_model=BulkFeaturesUpdateResponse, summary="Bulk Update Feature Statuses")
async def bulk_update_features_api(
    payload: BulkFeaturesUpdateRequest,
    service: AdminService = Depends(get_admin_service)
):
    """Allows updating multiple feature statuses in a single request."""
    try:
        features_to_update_simple: Dict[str, bool] = {
            fid: item.enabled for fid, item in payload.features.items()
        }
        result = await service.bulk_update_features_status(
            updates=features_to_update_simple,
            project_name=payload.project_name
        )
        # Service result should directly match BulkFeaturesUpdateResponse structure
        return BulkFeaturesUpdateResponse(**result)
    except Exception as e: # Catch unexpected errors from service or here
        logger.exception(f"Error in bulk_update_features_api for project '{payload.project_name}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during bulk update: {str(e)}")


@router.post("/system/cleanup", response_model=SystemCleanupResponse, summary="Perform System Cleanup")
async def system_cleanup_api(
    payload: SystemCleanupPayload,
    service: AdminService = Depends(get_admin_service)
):
    """Triggers system cleanup tasks like deleting old logs or temporary files."""
    try:
        cleanup_result = await service.perform_system_cleanup(
            cleanup_type=payload.type, max_age_days=payload.max_age_days
        )
        if cleanup_result.get("error") or cleanup_result.get("overall_status") == "failed":
            # Log the full result for debugging if there's an error
            logger.error(f"System cleanup failed or reported error. Type: {payload.type}. Result: {cleanup_result}")
            raise HTTPException(status_code=500, detail=cleanup_result.get("error") or "System cleanup operation failed or encountered errors.")
        return SystemCleanupResponse(**cleanup_result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in system_cleanup_api for type '{payload.type}'")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during system cleanup: {str(e)}")

@router.get("/system/info", response_model=SystemInfoResponse, summary="Get Comprehensive System Information")
async def system_info_api(service: AdminService = Depends(get_admin_service)):
    """Retrieves detailed system information, including platform, resources, and application status."""
    try:
        system_info = await service.get_comprehensive_system_info()
        if system_info.get("error"):
            raise HTTPException(status_code=500, detail=system_info["error"])
        return SystemInfoResponse(**system_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in system_info_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/system/health", response_model=SystemHealthResponse, summary="Get System Health Metrics")
async def system_health_api(service: AdminService = Depends(get_admin_service)):
    """Provides real-time system health metrics (CPU, memory, disk, application health)."""
    try:
        health_data = await service.get_system_health_metrics()
        if health_data.get("error"): # Service indicates an issue
             # Log the full health_data for debugging if there's an error
            logger.error(f"System health check reported an error: {health_data.get('error')}. Full data: {health_data}")
            # Still return the (partial) health data along with a 503 if overall_health is not good,
            # or 500 if there's a generic error string.
            if health_data.get("overall_health", "unknown") not in ["healthy", "warning"] : # Treat degraded/critical/unknown as service unavailable
                 raise HTTPException(status_code=503, detail=health_data.get("error") or "System health indicates issues.")
            # If there's an error string but health is somehow okay, it's more like a 500 for data retrieval problem.
            raise HTTPException(status_code=500, detail=health_data.get("error") or "Failed to retrieve complete system health.")

        # If overall_health is warning/degraded/critical, the client might want to know,
        # but the request itself succeeded. A 200 is fine, client inspects 'overall_health'.
        # However, if the service explicitly sets an error message, it implies a failure in data gathering.
        return SystemHealthResponse(**health_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in system_health_api")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


logger.info("Admin API router defined for FastAPI, using AdminService.")
print("Admin API router defined for FastAPI, using AdminService.")
