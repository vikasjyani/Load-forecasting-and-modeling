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

# Assuming LoadProfileService is adapted and available for DI.
try:
    from app.services.loadprofile_service import LoadProfileService
except ImportError:
    logging.warning("LoadProfileService not found, using placeholder for load profile API.")
    # Simplified placeholder
    class LoadProfileService:
        def __init__(self, project_data_root: Path): self.project_data_root = project_data_root
        async def get_main_page_data(self, project_name: str) -> Dict[str, Any]: return {"project_name": project_name, "template_info": {"exists": True}}
        async def get_template_analysis(self, project_name: str) -> Dict[str, Any]: return {"analysis": "mock_template_analysis"}
        async def get_available_base_years(self, project_name: str) -> Dict[str, Any]: return {"years": [2020, 2021]}
        async def get_scenario_analysis(self, project_name: str, scenario_name: str) -> Dict[str, Any]: return {"scenario": scenario_name, "analysis": "mock"}
        async def generate_profile(self, project_name: str, generation_type: str, config: Dict[str, Any]) -> Dict[str, Any]: return {"success": True, "profile_id": "new_mock_profile"}
        async def get_saved_profiles_with_metadata(self, project_name: str) -> Dict[str, Any]: return {"profiles": [{"profile_id": "mock_profile"}], "total_count": 1}
        async def get_profile_detailed_data(self, project_name: str, profile_id: str) -> Dict[str, Any]:
            if profile_id == "mock_profile": return {"profile_id": profile_id, "data_records": [{"value": 100}]}
            raise ResourceNotFoundError(resource_type="Profile", resource_id=profile_id)
        async def delete_profile(self, project_name: str, profile_id: str) -> Dict[str, Any]: return {"success": True}
        async def upload_template_file(self, project_name: str, file: UploadFile) -> Dict[str, Any]: return {"success": True, "filename": file.filename}
        # async def analyze_profile(self, project_name: str, profile_id: str) -> Dict[str, Any]: return {"analysis": "mock"} # This might belong to analysis service
        # async def compare_profiles(self, project_name: str, profile_ids: List[str]) -> Dict[str, Any]: return {"comparison": "mock"}
        async def get_profile_file_path(self, project_name: str, profile_id: str) -> Optional[Path]: # For downloads
             mock_path = self.project_data_root / project_name / "results" / "load_profiles" / f"{profile_id}.csv"
             mock_path.parent.mkdir(parents=True, exist_ok=True)
             mock_path.touch(exist_ok=True)
             return mock_path


from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
from app.utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE # Assuming these are relevant

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for LoadProfileService ---
async def get_load_profile_service(request: Request):
    # project_data_root = Path(request.app.state.settings.PROJECT_DATA_ROOT) # Example
    project_data_root = Path("user_projects_data") # Placeholder
    return LoadProfileService(project_data_root=project_data_root)

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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
):
    try:
        file_path = await service.get_profile_file_path(project_name, profile_id) # Service should return Path object
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
    service: LoadProfileService = Depends(get_load_profile_service)
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
    service: LoadProfileService = Depends(get_load_profile_service)
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

# Other API endpoints from the Flask blueprint like /api/template_info, /api/available_base_years,
# /api/scenario_info, /api/preview_base_profiles, /api/profile_analysis, /api/compare_profiles
# would be translated similarly using APIRouter, Pydantic, Depends, and async service calls.

logger.info("Load Profile (Generation/Management) API router defined for FastAPI.")
print("Load Profile (Generation/Management) API router defined for FastAPI.")
