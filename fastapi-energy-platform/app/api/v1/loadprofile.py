# fastapi-energy-platform/app/api/v1/loadprofile.py
"""
Load Profile API Endpoints for FastAPI.
Handles load profile generation, management, and retrieval.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body, Path as FastAPIPath, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from pathlib import Path
import tempfile # For creating temporary files for downloads
import asyncio # For asyncio.to_thread if direct os calls were needed here (but they are in service)

# Actual service import
from app.services.loadprofile_service import LoadProfileService

from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
from app.utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE # Assuming these are relevant

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for LoadProfileService ---
from app.dependencies import get_load_profile_service as get_load_profile_service_dependency

# --- Pydantic Models ---
class BaseProfileGenerationPayload(BaseModel):
    base_year: int = Field(..., ge=2000, le=2030)
    start_fy: int = Field(..., ge=2000, le=2050)
    end_fy: int = Field(..., ge=2000, le=2050)
    demand_source: str = Field(..., pattern="^(template|scenario)$")
    scenario_name: Optional[str] = None # Required if demand_source is 'scenario'
    frequency: str = Field(default="hourly", pattern="^(hourly|15min|30min|daily)$")
    custom_name: Optional[str] = Field(default=None, max_length=50)
    # Constraints can be added here as complex nested models if needed
    # apply_monthly_peaks: bool = False
    # apply_load_factors: bool = False

class StlProfileGenerationPayload(BaseModel):
    start_fy: int = Field(..., ge=2000, le=2050)
    end_fy: int = Field(..., ge=2000, le=2050)
    demand_source: str = Field(..., pattern="^(template|scenario)$")
    scenario_name: Optional[str] = None
    frequency: str = Field(default="hourly", pattern="^(hourly|15min|30min|daily)$")
    custom_name: Optional[str] = Field(default=None, max_length=50)
    stl_params: Optional[Dict[str, Any]] = None # e.g., {"period": 8760, "seasonal": 13}
    # Constraints can be added here

# --- API Endpoints ---
# Note: HTML rendering route is omitted.

@router.get("/{project_name}/main_data", summary="Get Main Page Data for Load Profile Generation")
async def get_main_page_data_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        data = await service.get_main_page_data(project_name=project_name)
        if "error" in data: raise ProcessingError(message=data["error"])
        return data
    except Exception as e:
        logger.exception(f"Error getting main page data for load profiles (project: {project_name})")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_name}/generate_base_profile", summary="Generate Base Load Profile")
async def generate_base_profile_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    payload: BaseProfileGenerationPayload,
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        # Additional validation if Pydantic models are not enough
        if payload.demand_source == "scenario" and not payload.scenario_name:
            raise CustomValidationError(message="scenario_name is required when demand_source is 'scenario'.")

        result = await service.generate_profile(project_name, "base_profile", payload.model_dump())
        if not result.get("success"):
            raise ProcessingError(message=result.get("error", "Base profile generation failed."))
        return result
    except (CustomValidationError, ValueError) as e: # Catch specific validation or value errors from service
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating base profile for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to generate base profile: {str(e)}")

@router.post("/{project_name}/generate_stl_profile", summary="Generate STL Load Profile")
async def generate_stl_profile_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    payload: StlProfileGenerationPayload,
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        if payload.demand_source == "scenario" and not payload.scenario_name:
            raise CustomValidationError(message="scenario_name is required when demand_source is 'scenario'.")

        result = await service.generate_profile(project_name, "stl_profile", payload.model_dump())
        if not result.get("success"):
            raise ProcessingError(message=result.get("error", "STL profile generation failed."))
        return result
    except (CustomValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating STL profile for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to generate STL profile: {str(e)}")

@router.get("/{project_name}/saved_profiles", summary="List Saved Load Profiles")
async def get_saved_profiles_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        profiles_data = await service.get_saved_profiles_with_metadata(project_name=project_name)
        return profiles_data
    except Exception as e:
        logger.exception(f"Error getting saved profiles for project {project_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/profile_data/{profile_id}", summary="Get Detailed Data for a Saved Profile")
async def get_profile_data_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the saved load profile"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        profile_data = await service.get_profile_detailed_data(project_name, profile_id)
        return profile_data
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting data for profile {project_name}/{profile_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/download_profile/{profile_id}", summary="Download Saved Profile CSV")
async def download_profile_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the saved load profile"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        file_path = await service.get_profile_file_path(project_name, profile_id) # Service returns Path object
        if not file_path or not file_path.exists():
            raise ResourceNotFoundError(resource_type="Profile CSV", resource_id=profile_id)

        return FileResponse(path=file_path, filename=f"{profile_id}.csv", media_type='text/csv')
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error downloading profile {project_name}/{profile_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{project_name}/delete_profile/{profile_id}", summary="Delete a Saved Profile")
async def delete_profile_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile to delete"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        result = await service.delete_profile(project_name, profile_id)
        if not result.get("success"):
            raise ProcessingError(message=result.get("error", "Failed to delete profile."))
        return result
    except Exception as e:
        logger.exception(f"Error deleting profile {project_name}/{profile_id}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_name}/upload_template", summary="Upload Load Curve Template")
async def upload_template_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    file: UploadFile = File(...),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    # Basic validation for filename and extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected or filename is empty.")
    if not file.filename.endswith(".xlsx"): # Assuming only xlsx for this specific template
        raise HTTPException(status_code=400, detail="Invalid file type. Only .xlsx templates are allowed.")

    # File size validation (example: 50MB) - can be done more robustly with streaming if needed
    MAX_TEMPLATE_SIZE = 50 * 1024 * 1024
    if hasattr(file, 'size') and file.size is not None and file.size > MAX_TEMPLATE_SIZE:
        raise HTTPException(status_code=413, detail=f"Template file too large. Max size: {MAX_TEMPLATE_SIZE//(1024*1024)}MB")

    try:
        result = await service.upload_template_file(project_name, file)
        if not result.get("success"):
            raise ProcessingError(message=result.get("error", "Template upload failed."))
        return result
    except Exception as e:
        logger.exception(f"Error uploading template for project {project_name}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Pydantic Models (from app.models.loadprofile) ---
# Assuming these are defined in app.models.loadprofile and imported here
# For brevity, not re-listing all of them, but they would be imported:
from app.models.loadprofile import (
    LoadProfileGenerationRequest, # Using a more generic one for payload
    LoadProfileResponse, # For single profile GET
    # Need Pydantic models for preview_base_profiles payload, scenario_info, analysis, comparison
    # For now, using basic BaseModel or Dict for some payloads.
)
from app.models.common import SuccessResponse # General success response


# --- API Endpoints (Derived from Flask blueprint) ---

@router.get("/{project_name}/template_info", summary="Get Load Curve Template Information")
async def get_template_info_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        info = await service.get_template_info(project_name)
        return info # Service method already handles ResourceNotFound for template
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e: # Catch-all for unexpected
        logger.exception(f"Unexpected error getting template info for project {project_name}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.get("/{project_name}/available_base_years", summary="Get Available Base Years for Profiles")
async def get_available_base_years_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        years = await service.get_available_base_years(project_name)
        return {"project_name": project_name, "available_base_years": years}
    except ProcessingError as e: # If service raises this for other reasons
        raise HTTPException(status_code=500, detail=str(e))
    # No ResourceNotFoundError expected here from service as it returns [] if template missing

class PreviewBaseProfilesPayload(BaseModel):
    base_year: int

@router.post("/{project_name}/preview_base_profiles", summary="Preview Base Load Profiles")
async def preview_base_profiles_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    payload: PreviewBaseProfilesPayload,
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        # The service method for this needs to be implemented in LoadProfileService
        # For now, assuming a placeholder or future implementation that takes base_year
        # preview_data = await service.preview_base_profiles(project_name, payload.base_year)
        # return preview_data
        raise HTTPException(status_code=501, detail="Preview base profiles endpoint not fully implemented in service yet.")
    except ValueError as e: # From service if base_year is invalid
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Reusing BaseProfileGenerationPayload and StlProfileGenerationPayload defined earlier
# if they match the structure needed by service.generate_profile's 'config' dict.
# For Flask, it was flat JSON. Let's ensure Pydantic models match.

# The service's `generate_profile` takes a `config: Dict[str, Any]`.
# The Pydantic models BaseProfileGenerationPayload & StlProfileGenerationPayload can be used directly.

@router.get("/{project_name}/profiles", summary="List All Saved Load Profiles", response_model=List[Dict[str, Any]]) # Adjust response_model
async def list_saved_profiles_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        profiles = await service.list_saved_profiles(project_name)
        return profiles
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/profiles/{profile_id}", summary="Get Specific Load Profile Data", response_model=Dict[str,Any]) # Adjust response_model
async def get_profile_data_api( # Renamed from Flask's get_profile_data_route
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        profile_data = await service.get_profile_detailed_data(project_name, profile_id)
        return profile_data
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))

# Download endpoint already exists.

# Delete endpoint already exists.

# Upload template endpoint already exists.

# Placeholder for Demand Scenario Info (if needed separately from generation payload)
@router.get("/{project_name}/demand_scenario/{scenario_name}", summary="Get Demand Scenario Information")
async def get_demand_scenario_info_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: str = FastAPIPath(..., description="Name of the demand projection scenario"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        # This service method needs to be implemented in LoadProfileService
        # It would use ProjectLoadProfileManager.load_demand_scenario_data
        # scenario_data = await service.get_demand_scenario_info(project_name, scenario_name)
        # return scenario_data
        # For now:
        manager = await service._get_project_generator(project_name)
        df = await manager.load_demand_scenario_data(scenario_name)
        if df.empty:
            raise ResourceNotFoundError(f"Scenario {scenario_name} has no data or does not exist.")
        return {"project_name":project_name, "scenario_name": scenario_name, "data_preview": df.head().to_dict("records"), "num_rows": len(df)}

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting demand scenario info for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))


# Analysis and Comparison endpoints would follow a similar pattern:
# Define Pydantic models for their specific request payloads & responses if not already in app.models.loadprofile
# Implement service methods in LoadProfileService
# Create router endpoints that call these service methods

class ProfileAnalysisRequestPayload(BaseModel): # Example
    analysis_type: str # e.g. "peak_analysis"
    params: Optional[Dict[str, Any]] = None

@router.post("/{project_name}/profiles/{profile_id}/analysis", summary="Analyze a Load Profile")
async def analyze_profile_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    payload: ProfileAnalysisRequestPayload, # This should use the more specific Pydantic models from app.models.loadprofile
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    # service_method = getattr(service, f"analyze_{payload.analysis_type}", None)
    # if not service_method or not callable(service_method):
    #     raise HTTPException(status_code=400, detail=f"Invalid analysis type: {payload.analysis_type}")
    # result = await service_method(project_name, profile_id, payload.params or {})
    # return result
    raise HTTPException(status_code=501, detail="Profile analysis endpoint not fully implemented in service yet.")

class CompareProfilesPayload(BaseModel): # Example
    profile_ids: List[str] = Field(..., min_items=2)
    metrics: Optional[List[str]] = None

@router.post("/{project_name}/compare_profiles", summary="Compare Multiple Load Profiles")
async def compare_profiles_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    payload: CompareProfilesPayload,
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    # result = await service.compare_profiles(project_name, payload.profile_ids, payload.metrics)
    # return result
    raise HTTPException(status_code=501, detail="Compare profiles endpoint not fully implemented in service yet.")

@router.get("/{project_name}/historical_summary", summary="Get Historical Data Summary")
async def get_historical_summary_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        summary = await service.get_historical_data_summary(project_name)
        return summary
    except ResourceNotFoundError as e: # If template not found
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e: # Other processing errors
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting historical summary for project {project_name}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching historical summary.")

@router.get("/{project_name}/base_year_info/{year}", summary="Get Detailed Info for a Base Year")
async def get_base_year_info_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    year: int = FastAPIPath(..., description="The base year to get information for", ge=2000, le=2050),
    service: LoadProfileService = Depends(get_load_profile_service_dependency)
):
    try:
        info = await service.get_base_year_detailed_info(project_name, year)
        return info
    except ResourceNotFoundError as e: # If template or year data not found
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e: # If year is invalid for other reasons (e.g. not in data though template exists)
        raise HTTPException(status_code=404, detail=str(e)) # Or 422 if it's a validation issue
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting base year info for project {project_name}, year {year}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred while fetching base year information.")

logger.info("Load Profile API router defined for FastAPI with new endpoints and service integration.")
print("Load Profile API router defined for FastAPI with new endpoints and service integration.")
