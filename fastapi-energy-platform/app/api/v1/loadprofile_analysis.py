# fastapi-energy-platform/app/api/v1/loadprofile_analysis.py
"""
API Endpoints for Load Profile Analysis.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path as FastAPIPath, HTTPException, Body

from app.services.loadprofile_analysis_service import LoadProfileAnalysisService
# The get_load_profile_analysis_service dependency needs to be added to app.dependencies.py
from app.dependencies import get_load_profile_analysis_service
from app.models.loadprofile_analysis import (
    AvailableProfileForAnalysis,
    StatisticalSummary,
    ProfileAnalysisResult # Generic for now
)
from app.utils.error_handlers import ResourceNotFoundError, ProcessingError

logger = logging.getLogger(__name__)
router = APIRouter()

# --- API Endpoints ---

@router.get("/{project_name}/available_profiles",
            response_model=List[AvailableProfileForAnalysis],
            summary="List Available Load Profiles for Analysis")
async def list_profiles_for_analysis_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        profiles = await service.list_available_profiles_for_analysis(project_name)
        return profiles
    except Exception as e:
        logger.exception(f"Error listing profiles for analysis in project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list profiles: {str(e)}")

@router.get("/{project_name}/profile/{profile_id}/statistical_summary",
            response_model=StatisticalSummary,
            summary="Get Statistical Summary for a Load Profile")
async def get_statistical_summary_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    unit: Optional[str] = Query("kW", description="Unit for the summary results (e.g., kW, MW)"),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        summary = await service.get_statistical_summary(project_name, profile_id, unit)
        return summary
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e)) # Or 500 if it's a server-side processing issue
    except Exception as e:
        logger.exception(f"Error getting statistical summary for profile '{profile_id}', project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistical summary: {str(e)}")


# Placeholder for generic analysis endpoint
# More specific endpoints for each analysis type (peak, seasonal etc.) might be better
# Or a single endpoint that takes analysis_type and params in request body.
@router.post("/{project_name}/profile/{profile_id}/analyze/{analysis_type}",
             response_model=ProfileAnalysisResult, # This is a generic model
             summary="Perform a Specific Analysis on a Load Profile (Placeholder)")
async def perform_profile_analysis_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    analysis_type: str = FastAPIPath(..., description="Type of analysis to perform (e.g., 'peak', 'seasonal')"),
    params: Optional[Dict[str, Any]] = Body(None, description="Parameters for the analysis"),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    logger.warning(f"Generic analysis endpoint /analyze/{analysis_type} called for {project_name}/{profile_id}. Not fully implemented.")
    # try:
    #     # result = await service.perform_single_analysis(project_name, profile_id, analysis_type, params or {})
    #     # return result
    # except ResourceNotFoundError as e:
    #     raise HTTPException(status_code=404, detail=str(e))
    # except ProcessingError as e: # Or specific validation errors for params
    #     raise HTTPException(status_code=400, detail=str(e))
    # except Exception as e:
    #     logger.exception(f"Error performing '{analysis_type}' analysis for profile '{profile_id}': {e}")
    #     raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    raise HTTPException(status_code=501, detail=f"Analysis type '{analysis_type}' not implemented yet.")


logger.info("Load Profile Analysis API router defined for FastAPI.")
