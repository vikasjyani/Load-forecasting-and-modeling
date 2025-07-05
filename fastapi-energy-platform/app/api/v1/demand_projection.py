# fastapi-energy-platform/app/api/v1/demand_projection.py
"""
Demand Projection API Endpoints for FastAPI
Handles demand forecasting model execution, status tracking, and results retrieval.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, BackgroundTasks
from pydantic import BaseModel, Field
import uuid # Added for job ID generation
from pathlib import Path

# Actual service imports - remove placeholder block
from app.services.demand_projection_service import (
    DemandProjectionService,
    ForecastJobConfig, # Data class for job configuration from the service
    forecast_job_manager # Global instance of ForecastJobManager from the service
)

# Custom error handlers and constants
from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, BusinessLogicError
from app.utils.constants import FORECAST_MODELS # Assuming this constant is still relevant

logger = logging.getLogger(__name__)
router = APIRouter()

# Dependency for DemandProjectionService from app.dependencies
from app.dependencies import get_demand_projection_service as get_demand_projection_service_dependency

# --- Pydantic Models for Request/Response ---
# Use ForecastJobConfig from service directly for payload if it matches API needs
# Or define a specific API payload model if they diverge.
# For now, assuming RunForecastPayload can be the same as service's ForecastJobConfig
class RunForecastPayload(ForecastJobConfig):
    pass

class ScenarioNameValidationPayload(BaseModel):
    scenarioName: str = Field(..., min_length=2, max_length=50, pattern=r'^[a-zA-Z0-9_\-\s]+$')
    # Note: The pattern allows spaces. If spaces are not desired in scenario directory names,
    # the service layer should handle sanitizing this (e.g. replacing spaces with underscores)
    # before creating directories. The safe_filename utility could be used.


# --- API Endpoints ---
# Note: HTML rendering routes are omitted.

@router.get("/{project_name}/data_summary", summary="Get Input Data Summary for a Project")
async def get_data_summary_api(
    project_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
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
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
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
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
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

@router.get("/{project_name}/chart_data/{sector_name}", summary="Get Chart Data for a Sector")
async def get_chart_data_api(
    project_name: str,
    sector_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
):
    try:
        # Assuming the service will have a method like get_chart_data
        # This was present in the Flask blueprint's service call.
        result = await service.get_chart_data(project_name=project_name, sector=sector_name)
        if 'error' in result: # Service might return error dict
             raise ResourceNotFoundError(resource_type="Chart data", resource_id=f"{project_name}/{sector_name}", message=result['error'])
        return result
    except ValueError as e: # Raised by service if sector not found
        raise ResourceNotFoundError(resource_type="Sector for chart data", resource_id=sector_name, message=str(e))
    except Exception as e:
        logger.exception(f"Error getting chart data for {project_name}/{sector_name}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{project_name}/run_forecast", status_code=202, summary="Run Demand Forecast for a Project")
async def run_forecast_api(
    project_name: str,
    payload: RunForecastPayload,
    background_tasks: BackgroundTasks,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
):
    """
    Starts a demand forecasting job for the specified project and configuration.
    The job runs in the background. Use the returned job_id to track status.
    """
    try:
        # Validate the configuration using the service method
        # Ensure the service's ForecastJobConfig matches what `validate_forecast_config` expects
        # The payload is already an instance of ForecastJobConfig (service version)
        validation_errors = await service.validate_forecast_config(project_name=project_name, config=payload)
        if validation_errors:
            raise HTTPException(status_code=422, detail={"message": "Configuration validation failed", "errors": validation_errors})

        # Check concurrent job limits (if ForecastJobManager implements this check)
        # Example:
        # jobs_summary = await forecast_job_manager.get_jobs_summary()
        # if jobs_summary.get('active_jobs', 0) >= MAX_CONCURRENT_FORECASTS: # Define MAX_CONCURRENT_FORECASTS
        #     raise HTTPException(status_code=429, detail="Too many active forecast jobs.")

        job_id = str(uuid.uuid4())
        # Create job using the global forecast_job_manager from the service module
        await forecast_job_manager.create_job(config=payload, id=job_id, type="demand_forecast", project_name=project_name)

        # Add the long-running task to background tasks
        background_tasks.add_task(service.execute_forecast_async, project_name, payload, job_id)

        logger.info(f"Forecast job {job_id} started for project '{project_name}', scenario '{payload.scenario_name}'.")
        return {
            "message": f"Forecast job started for scenario '{payload.scenario_name}'.",
            "job_id": job_id,
            "status_url": router.url_path_for("get_forecast_status_api", job_id=job_id),
            "cancel_url": router.url_path_for("cancel_forecast_api", job_id=job_id)
        }
    except HTTPException: # Re-raise HTTPExceptions
        raise
    except Exception as e:
        logger.exception(f"Error starting forecast for project {project_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start forecast: {str(e)}")

@router.get("/forecast_status/{job_id}", summary="Get Forecast Job Status")
async def get_forecast_status_api(job_id: str): # Add type hint for service if used
    # Uses the global forecast_job_manager from the service module
    job = await forecast_job_manager.get_job(job_id)
    if not job:
        raise ResourceNotFoundError(resource_type="Forecast Job", resource_id=job_id)
    return job

@router.post("/cancel_forecast/{job_id}", summary="Cancel Forecast Job")
async def cancel_forecast_api(job_id: str): # Add type hint for service if used
    # Uses the global forecast_job_manager from the service module
    job = await forecast_job_manager.get_job(job_id) # Check job existence first
    if not job:
        raise ResourceNotFoundError(resource_type="Forecast Job", resource_id=job_id)

    if job.get('status') not in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
         raise BusinessLogicError(message=f"Cannot cancel job {job_id}. Status: {job.get('status')}.")

    success = await forecast_job_manager.cancel_job(job_id)
    if not success: # Should not happen if status check passed, but good for robustness
        # This might indicate an issue with the job manager's internal state
        raise HTTPException(status_code=500, detail=f"Failed to request cancellation for job {job_id}.")
    return {"message": f"Forecast job '{job_id}' cancellation requested."}


@router.get("/jobs/summary", summary="Get Summary of All Forecast Jobs")
async def get_jobs_summary_api(): # Add type hint for service if used
    # Uses the global forecast_job_manager from the service module
    summary = await forecast_job_manager.get_jobs_summary()
    return summary

@router.post("/{project_name}/validate_scenario_name", summary="Validate Scenario Name for a Project")
async def validate_scenario_name_api(
    project_name: str,
    payload: ScenarioNameValidationPayload,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency) # Service needed for checking existence
):
    scenario_name = payload.scenarioName
    # This should ideally call a service method to check for scenario existence
    # For now, assuming a simplified check or that service method will be added.
    # exists = await service.check_scenario_exists(project_name, scenario_name) # Example

    # Placeholder logic for existence check (should be in service)
    from app.config import settings as global_settings # Temporary direct import
    scenario_results_path = global_settings.PROJECT_DATA_ROOT / project_name / "results" / "demand_projection" / scenario_name
    exists = await asyncio.to_thread(scenario_results_path.exists)


    return {
        "scenario_name": scenario_name,
        "is_valid": True, # Pydantic handled basic validation of format
        "already_exists": exists,
        "message": f"Scenario name '{scenario_name}' format is valid. {'It will overwrite an existing scenario.' if exists else 'It is available.'}"
    }

@router.get("/{project_name}/configuration/{scenario_name}", summary="Get Saved Scenario Configuration")
async def get_scenario_configuration_api(
    project_name: str,
    scenario_name: str,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
):
    try:
        # Assuming service has get_scenario_configuration method
        config_data = await service.get_scenario_configuration(project_name=project_name, scenario_name=scenario_name)
        if config_data is None: # Service should return None if not found
            raise ResourceNotFoundError(resource_type="Scenario Configuration", resource_id=f"{project_name}/{scenario_name}")
        return config_data
    except ResourceNotFoundError: # Re-raise specific not found errors
        raise
    except ValueError as ve: # Catch other specific errors from service
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error getting configuration for project '{project_name}', scenario '{scenario_name}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scenario configuration: {str(e)}")


@router.post("/{project_name}/validate_configuration", summary="Validate Forecast Configuration")
async def validate_configuration_api(
    project_name: str,
    payload: RunForecastPayload,
    service: DemandProjectionService = Depends(get_demand_projection_service_dependency)
):
    """Validates a complete forecast configuration without starting the job."""
    try:
        # Ensure the service's ForecastJobConfig matches what `validate_forecast_config` expects
        validation_errors = await service.validate_forecast_config(project_name=project_name, config=payload)
        if validation_errors:
            # Return 422 for validation errors
            return HTTPException(status_code=422, detail={"message": "Configuration has validation errors.", "errors": validation_errors})
        return {"is_valid": True, "message": "Configuration is valid."}
    except ValueError as ve: # Catch specific errors from service like file not found for project
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"Error validating configuration for project {project_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


# Omitted: _prepare_sector_tables, _prepare_aggregated_table, _assess_overall_data_quality
# These are primarily for rendering HTML tables/summaries in Flask templates.
# If similar data is needed for API responses, specific endpoints or data models would be created.
# Chart data generation (_get_chart_data_api) is kept as it's common for APIs to serve chart-ready data.

logger.info("Demand Projection API router defined for FastAPI.")
print("Demand Projection API router defined for FastAPI.")
