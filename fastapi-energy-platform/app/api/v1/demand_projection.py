# fastapi-energy-platform/app/api/v1/demand_projection.py
"""
Demand Projection API Endpoints for FastAPI
Handles demand forecasting model execution, status tracking, and results retrieval.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, BackgroundTasks
from pydantic import BaseModel, Field
from pathlib import Path # Added for project_path type hint

# Assuming DemandProjectionService and related classes are adapted and available for DI.
try:
    from app.services.demand_projection_service import (
        DemandProjectionService,
        ForecastJobConfig, # Data class for job configuration
        forecast_job_manager # Global instance of ForecastJobManager
    )
except ImportError:
    logging.warning("DemandProjectionService not found, using placeholder for demand projection API.")
    # Simplified placeholders if actual service is not ready
    class ForecastJobConfig(BaseModel):
        scenario_name: str
        target_year: int
        exclude_covid_years: bool
        sector_configs: Dict[str, Any]
        detailed_configuration: Optional[Dict[str, Any]] = None
        user_metadata: Optional[Dict[str, Any]] = None
    class ForecastJobManager:
        async def create_job(self, config: ForecastJobConfig, **kwargs) -> Dict[str, Any]: return {"id": "mock_job_id", "status": "STARTING"}
        async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]: return {"id": job_id, "status": "COMPLETED", "progress": 100, "result_summary": {"message": "Mock result"}} if job_id =="mock_job_id" else None
        async def cancel_job(self, job_id: str) -> bool: return True
        async def get_jobs_summary(self) -> Dict[str, Any]: return {"total_jobs": 1, "active_jobs": 0}
    forecast_job_manager = ForecastJobManager()
    class DemandProjectionService:
        def __init__(self, project_data_root: Path): self.project_data_root = project_data_root
        async def get_input_data_summary(self, project_name: str) -> Dict[str, Any]: return {"project_name": project_name, "sectors_available": ["mock_sector"]}
        async def get_sector_data(self, project_name: str, sector_name: str) -> Dict[str, Any]: return {"sector_name": sector_name, "data_records": [{"Year": 2020, "Electricity": 100}]}
        async def get_independent_variables(self, project_name: str, sector: str) -> Dict[str, Any]: return {"sector": sector, "variables": ["var1"]}
        async def get_correlation_data(self, project_name: str, sector: str) -> Dict[str, Any]: return {"sector": sector, "correlations": {"var1": 0.8}}
        async def get_chart_data(self, project_name: str, sector: str) -> Dict[str, Any]: return {"sector": sector, "chart_type": "line", "data": {}}
        async def validate_forecast_config(self, project_name: str, config: ForecastJobConfig) -> List[str]: return [] # No errors
        async def execute_forecast_async(self, project_name: str, config: ForecastJobConfig, job_id: str): pass # Runs in background
        async def get_scenario_configuration(self, project_name: str, scenario_name: str) -> Optional[Dict[str, Any]]: return {"config": "mock"} if scenario_name == "mock_scenario" else None


from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
from app.utils.constants import FORECAST_MODELS # Assuming this constant is still relevant

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Dependency for DemandProjectionService ---
# This needs project_data_root, which should come from settings or app state.
async def get_demand_projection_service(request: Request):
    # Example: project_data_root = Path(request.app.state.settings.PROJECT_DATA_ROOT)
    # For now, using a placeholder path.
    project_data_root = Path("user_projects_data") # This MUST be configured correctly
    return DemandProjectionService(project_data_root=project_data_root)


# --- Pydantic Models for Request/Response ---
# ForecastJobConfig is already defined in the service, can be reused or a specific API model created.
# For API input, directly use the service's ForecastJobConfig or a subset.
class RunForecastPayload(ForecastJobConfig): # Inherit or redefine as needed for API
    pass

class ScenarioNameValidationPayload(BaseModel):
    scenarioName: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-zA-Z0-9_\-\s]+$')


# --- API Endpoints ---
# Note: HTML rendering routes are omitted.

@router.get("/{project_name}/data_summary", summary="Get Input Data Summary for a Project")
async def get_data_summary_api(
    project_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    try:
        summary = await service.get_input_data_summary(project_name=project_name)
        if "error" in summary:
            raise ProcessingError(message=summary["error"])
        return summary
    except FileNotFoundError as e:
        raise ResourceNotFoundError(resource_type="Project input data", resource_id=project_name, message=str(e))
    except Exception as e:
        logger.exception(f"Error getting data summary for project {project_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/independent_variables/{sector_name}", summary="Get Independent Variables for a Sector")
async def get_independent_variables_api(
    project_name: str,
    sector_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    try:
        result = await service.get_independent_variables(project_name=project_name, sector=sector_name)
        return result
    except ValueError as e: # Raised by service if sector not found
        raise ResourceNotFoundError(resource_type="Sector", resource_id=sector_name, message=str(e))
    except Exception as e:
        logger.exception(f"Error getting independent variables for {project_name}/{sector_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{project_name}/correlation_data/{sector_name}", summary="Get Correlation Data for a Sector")
async def get_correlation_data_api(
    project_name: str,
    sector_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    try:
        result = await service.get_correlation_data(project_name=project_name, sector=sector_name)
        if 'error' in result: # Service might return error dict
            raise ResourceNotFoundError(resource_type="Sector data for correlation", resource_id=sector_name, message=result['error'])
        return result
    except ValueError as e:
        raise ResourceNotFoundError(resource_type="Sector", resource_id=sector_name, message=str(e))
    except Exception as e:
        logger.exception(f"Error getting correlation data for {project_name}/{sector_name}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_name}/run_forecast", status_code=202, summary="Run Demand Forecast for a Project")
async def run_forecast_api(
    project_name: str,
    payload: RunForecastPayload, # Uses the ForecastJobConfig structure
    background_tasks: BackgroundTasks,
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    """
    Starts a demand forecasting job for the specified project and configuration.
    The job runs in the background. Use the returned job_id to track status.
    """
    try:
        validation_errors = await service.validate_forecast_config(project_name=project_name, config=payload)
        if validation_errors:
            # Using FastAPI's HTTPException for 422 directly, as Pydantic validation errors are handled by FastAPI.
            # This is for business logic validation failures.
            raise HTTPException(status_code=422, detail={"message": "Configuration validation failed", "errors": validation_errors})

        # Check for scenario replacement (service might handle this or provide info)
        # For now, assume overwrite or new scenario.

        # Check concurrent job limits (if ForecastJobManager implements this)
        # current_active_jobs = (await forecast_job_manager.get_jobs_summary()).get('active_jobs', 0)
        # MAX_CONCURRENT_FORECASTS = 3 # Example limit
        # if current_active_jobs >= MAX_CONCURRENT_FORECASTS:
        #     raise HTTPException(status_code=429, detail="Too many active forecast jobs. Please try again later.")

        job_id = str(uuid.uuid4()) # Generate job ID here or let manager do it
        job_info = await forecast_job_manager.create_job(config=payload, id=job_id, type="demand_forecast") # Pass explicit id

        background_tasks.add_task(service.execute_forecast_async, project_name, payload, job_id)

        logger.info(f"Forecast job {job_id} started for project '{project_name}', scenario '{payload.scenario_name}'.")
        return {
            "message": f"Forecast job started for scenario '{payload.scenario_name}'.",
            "job_id": job_id,
            "status_url": f"/api/v1/demand_projection/forecast_status/{job_id}", # Example URL
            "cancel_url": f"/api/v1/demand_projection/cancel_forecast/{job_id}"  # Example URL
        }
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.exception(f"Error starting forecast for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to start forecast: {str(e)}")


@router.get("/forecast_status/{job_id}", summary="Get Forecast Job Status")
async def get_forecast_status_api(job_id: str):
    job = await forecast_job_manager.get_job(job_id)
    if not job:
        raise ResourceNotFoundError(resource_type="Forecast Job", resource_id=job_id)
    return job

@router.post("/cancel_forecast/{job_id}", summary="Cancel Forecast Job")
async def cancel_forecast_api(job_id: str):
    success = await forecast_job_manager.cancel_job(job_id)
    if not success:
        # Could be job not found or job already completed/cancelled
        job = await forecast_job_manager.get_job(job_id)
        if not job:
            raise ResourceNotFoundError(resource_type="Forecast Job", resource_id=job_id)
        raise BusinessLogicError(message=f"Cannot cancel job {job_id} with status {job.get('status')}.")
    return {"message": f"Forecast job '{job_id}' cancellation requested."}

@router.get("/jobs/summary", summary="Get Summary of All Forecast Jobs")
async def get_jobs_summary_api():
    summary = await forecast_job_manager.get_jobs_summary()
    return summary

@router.post("/{project_name}/validate_scenario_name", summary="Validate Scenario Name for a Project")
async def validate_scenario_name_api(project_name: str, payload: ScenarioNameValidationPayload):
    # In FastAPI, basic validation (length, pattern) is handled by Pydantic model.
    # This endpoint might check for existing scenarios with the same name.
    scenario_name = payload.scenarioName # Access validated field
    # Placeholder: check if scenario_name already exists for project_name
    # scenario_path = service._get_project_input_file_path(project_name).parent.parent / "results" / "demand_projection" / scenario_name
    # exists = scenario_path.exists()
    exists = False # Mock
    return {
        "scenario_name": scenario_name,
        "is_valid": True, # Pydantic handled basic validation
        "already_exists": exists,
        "message": f"Scenario name '{scenario_name}' is valid. {'It will overwrite an existing scenario.' if exists else 'It is available.'}"
    }

@router.get("/{project_name}/configuration/{scenario_name}", summary="Get Saved Scenario Configuration")
async def get_scenario_configuration_api(
    project_name: str,
    scenario_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    try:
        config_data = await service.get_scenario_configuration(project_name=project_name, scenario_name=scenario_name)
        if config_data is None:
            raise ResourceNotFoundError(resource_type="Scenario Configuration", resource_id=f"{project_name}/{scenario_name}")
        return config_data
    except ResourceNotFoundError as e:
        raise e
    except Exception as e:
        logger.exception(f"Error getting config for {project_name}/{scenario_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_name}/validate_configuration", summary="Validate Forecast Configuration")
async def validate_configuration_api(
    project_name: str,
    payload: RunForecastPayload, # Reusing the run forecast payload for validation
    service: DemandProjectionService = Depends(get_demand_projection_service)
):
    """Validates a complete forecast configuration without starting the job."""
    try:
        validation_errors = await service.validate_forecast_config(project_name=project_name, config=payload)
        if validation_errors:
            return {"is_valid": False, "errors": validation_errors, "message": "Configuration has validation errors."}
        return {"is_valid": True, "message": "Configuration is valid."}
    except Exception as e:
        logger.exception(f"Error validating configuration for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# Omitted: _prepare_sector_tables, _prepare_aggregated_table, _assess_overall_data_quality
# These are primarily for rendering HTML tables/summaries in Flask templates.
# If similar data is needed for API responses, specific endpoints or data models would be created.
# Chart data generation (_get_chart_data_api) is kept as it's common for APIs to serve chart-ready data.

logger.info("Demand Projection API router defined for FastAPI.")
print("Demand Projection API router defined for FastAPI.")
