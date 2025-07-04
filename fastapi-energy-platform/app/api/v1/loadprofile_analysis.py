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


from app.models.loadprofile_analysis import ( # Updated imports
    AvailableProfileForAnalysis,
    StatisticalSummary,
    # ProfileAnalysisResult, # Kept generic one for now, or use specific ones below
    PeakAnalysisParams, PeakAnalysisResultData,
    DurationCurveParams, DurationCurveResultData,
    SeasonalAnalysisParams, SeasonalAnalysisResultData,
    ComprehensiveAnalysisParams, ComprehensiveAnalysisResultData, # Added
    ProfileComparisonParams, ProfileComparisonResultData # Added for comparison
)
# ... (keep existing imports)

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting statistical summary for profile '{profile_id}', project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistical summary: {str(e)}")

@router.post("/{project_name}/profile/{profile_id}/comprehensive_analysis",
            response_model=ComprehensiveAnalysisResultData,
            summary="Perform Comprehensive Analysis on a Load Profile")
async def perform_comprehensive_analysis_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    params: ComprehensiveAnalysisParams = Body(...),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        result = await service.perform_comprehensive_analysis(project_name, profile_id, params)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error performing comprehensive analysis for profile '{profile_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

@router.post("/{project_name}/profile/{profile_id}/peak_analysis",
             response_model=PeakAnalysisResultData,
             summary="Perform Peak Analysis on a Load Profile")
async def perform_peak_analysis_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    params: PeakAnalysisParams = Body(...),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        result = await service.perform_peak_analysis(project_name, profile_id, params)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error performing peak analysis for profile '{profile_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Peak analysis failed: {str(e)}")

@router.post("/{project_name}/profile/{profile_id}/duration_curve",
             response_model=DurationCurveResultData,
             summary="Generate Load Duration Curve for a Profile")
async def generate_duration_curve_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    params: DurationCurveParams = Body(...),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        result = await service.generate_duration_curve(project_name, profile_id, params)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating duration curve for profile '{profile_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Duration curve generation failed: {str(e)}")

@router.post("/{project_name}/profile/{profile_id}/seasonal_analysis",
             response_model=SeasonalAnalysisResultData,
             summary="Perform Seasonal Analysis on a Load Profile")
async def perform_seasonal_analysis_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    profile_id: str = FastAPIPath(..., description="ID of the load profile"),
    params: SeasonalAnalysisParams = Body(...),
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        result = await service.perform_seasonal_analysis(project_name, profile_id, params)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error performing seasonal analysis for profile '{profile_id}': {e}")
        raise HTTPException(status_code=500, detail=f"Seasonal analysis failed: {str(e)}")

# The generic /analyze/{analysis_type} endpoint can be removed or kept for future flexibility / less common analyses.
# For now, removing it in favor of specific endpoints.

@router.post("/{project_name}/compare_profiles",
            response_model=ProfileComparisonResultData,
            summary="Compare two Load Profiles")
async def compare_load_profiles_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    params: ProfileComparisonParams = Body(...), # Contains profile_ids and unit
    service: LoadProfileAnalysisService = Depends(get_load_profile_analysis_service)
):
    try:
        result = await service.compare_load_profiles(project_name, params)
        return result
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error comparing load profiles in project '{project_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Profile comparison failed: {str(e)}")


logger.info("Load Profile Analysis API router updated with specific analysis endpoints.")
