# fastapi-energy-platform/app/api/v1/pypsa.py
"""
PyPSA API Endpoints for FastAPI.
Handles PyPSA model execution, data extraction, and results visualization.
"""
import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path as FastAPIPath, BackgroundTasks
from pydantic import BaseModel, Field
from pathlib import Path
import pypsa # PyPSA itself
import pandas as pd # For data manipulation if service returns DataFrames

# Assuming PyPSA utilities and runner are adapted and available.
# These imports need to be correct based on the final project structure.
try:
    from app.utils import pypsa_analysis_utils as pau
    from app.utils.pypsa_runner import run_pypsa_model_core # This is the core execution logic
    from app.utils.helpers import extract_tables_by_markers, validate_file_path, get_file_info # General helpers
    # from app.utils.pypsa_helpers import ... # If specific PyPSA helpers exist separately
except ImportError as e:
    logging.error(f"Failed to import PyPSA utilities: {e}", exc_info=True)
    # Define placeholders if imports fail, to allow API to load
    class pau: # type: ignore
        @staticmethod
        def dispatch_data_payload_former(*args, **kwargs): return {"error": "pau not loaded"}
        @staticmethod
        def capacity_data_payload_former(*args, **kwargs): return {"error": "pau not loaded"}
        # ... other pau functions as needed ...
    def run_pypsa_model_core(*args, **kwargs): raise NotImplementedError("pypsa_runner not loaded")

from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError
# from app.utils.constants import ... # If any constants are needed

logger = logging.getLogger(__name__)
router = APIRouter()

# --- In-memory store for PyPSA jobs (Replace with Redis/Celery in production) ---
pypsa_jobs: Dict[str, Dict[str, Any]] = {} # job_id -> job_details

# --- Network Manager Placeholder ---
# A proper NetworkManager would handle loading/caching PyPSA networks.
import uuid # For job IDs
from datetime import datetime # For timestamps

# Service and Pydantic models
from app.services.pypsa_service import PypsaService, pypsa_job_manager # Assuming job manager is global in service file
from app.models.pypsa import (
    PyPSAJobRunPayload,
    PyPSAJobStatusResponse,
    PyPSANetworkListResponse,
    # PyPSANetworkInfoResponse, # Used by PyPSANetworkListResponse
    PyPSANetworkInfoDetailResponse, # For detailed info of one network
    PyPSADataExtractionRequest,
    PyPSADataResponse,
    PyPSAComparisonRequest,
    PyPSAComparisonResponse,
    PyPSASystemStatusResponse
)
# --- Dependency for PypsaService ---
from app.dependencies import get_pypsa_service as get_pypsa_service_dependency


# --- API Endpoints ---

@router.post("/run_simulation", status_code=202, response_model=PyPSAJobStatusResponse, summary="Run PyPSA Optimization Model")
async def run_pypsa_simulation_api(
    payload: PyPSAJobRunPayload,
    background_tasks: BackgroundTasks,
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    """
    Triggers a PyPSA model optimization run for a given project and scenario.
    The job runs in the background. Use the returned job_id to track status.
    """
    try:
        job = await service.run_pypsa_simulation(
            project_name=payload.project_name,
            scenario_name=payload.scenario_name,
            ui_settings_overrides=payload.ui_settings_overrides,
            background_tasks=background_tasks
        )
        # Convert PyPSAJob dataclass to PyPSAJobStatusResponse Pydantic model for response
        return PyPSAJobStatusResponse(**job.__dict__) # Or map fields explicitly
    except Exception as e:
        logger.exception(f"Error initiating PyPSA simulation for project {payload.project_name}, scenario {payload.scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to start PyPSA simulation: {str(e)}")

@router.get("/job_status/{job_id}", response_model=PyPSAJobStatusResponse, summary="Get PyPSA Job Status")
async def get_pypsa_job_status_api(
    job_id: str = FastAPIPath(..., description="ID of the PyPSA simulation job"),
    service: PypsaService = Depends(get_pypsa_service_dependency) # Service might not be needed if job_manager is global
):
    job = await pypsa_job_manager.get_job(job_id) # Accessing global job manager
    if not job:
        raise HTTPException(status_code=404, detail=f"PyPSA Job with ID '{job_id}' not found.")
    return PyPSAJobStatusResponse(**job.__dict__)


@router.get("/{project_name}/networks", response_model=PyPSANetworkListResponse, summary="List Available PyPSA Networks/Scenarios")
async def list_available_networks_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: Optional[str] = Query(None, description="Optional: Specific scenario name to list its network files. If None, lists scenario folders."),
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        network_infos = await service.list_available_network_files(project_name, scenario_name)
        # Convert list of PyPSANetworkInfo dataclasses to list of PyPSANetworkInfoResponse Pydantic models
        response_networks = [PyPSANetworkInfoResponse(**info.__dict__) for info in network_infos]
        return PyPSANetworkListResponse(project_name=project_name, scenario_name=scenario_name, networks=response_networks)
    except Exception as e:
        logger.exception(f"Error listing PyPSA networks for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to list networks: {str(e)}")


# Placeholder for /extract_data - This needs more design on how filters/kwargs are passed
# and how the service's NetworkManager and DataExtractionComponent are used.
# The Flask version had GET with path params; POST with a body is more flexible.
@router.post("/{project_name}/scenario/{scenario_name}/network/{network_file_id}/extract_data",
             response_model=PyPSADataResponse, # Define this Pydantic model
             summary="Extract Data from a Specific PyPSA Network")
async def extract_pypsa_data_api(
    project_name: str = FastAPIPath(..., description="Project name"),
    scenario_name: str = FastAPIPath(..., description="Scenario name"),
    network_file_id: str = FastAPIPath(..., description="Network file identifier (e.g., year or run ID)"),
    payload: PyPSADataExtractionRequest,
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        # network = await service.load_network(project_name, scenario_name, payload.network_file_identifier) # Needs service method
        # data = await service.extract_data(network, payload.extraction_function_name, payload.filters, **payload.kwargs)
        # For now, placeholder as service methods are not fully there.
        logger.warning("PyPSA /extract_data endpoint called but service methods for network loading and data extraction are not fully implemented.")
        raise HTTPException(status_code=501, detail="Data extraction from PyPSA network not fully implemented yet.")

        # Example of how it might look once service is ready:
        # network_full_path = service._get_pypsa_results_path(project_name, scenario_name) / network_file_id
        # # ^ This path logic needs to be robust in service
        # if not await asyncio.to_thread(network_full_path.exists):
        #     raise HTTPException(status_code=404, detail=f"Network file {network_file_id} not found.")

        # # This part would use the NetworkManager and DataExtractor components within the service
        # extracted_data_dict = await service.get_network_data(
        #     project_name, scenario_name, network_file_id,
        #     payload.extraction_function_name, payload.filters, **payload.kwargs
        # )
        # return PyPSADataResponse(data=extracted_data_dict['data'], colors=extracted_data_dict.get('colors'), metadata=extracted_data_dict['metadata'])

    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.detail if isinstance(e.detail, str) else e.detail.get("message")))
    except CustomValidationError as e: # If service raises validation error
        raise HTTPException(status_code=422, detail=e.detail)
    except ProcessingError as e: # If service raises processing error
        raise HTTPException(status_code=500, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error extracting PyPSA data for {project_name}/{scenario_name}/{network_file_id}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")


@router.get("/{project_name}/scenario/{scenario_name}/network/{network_file_name}/info",
            response_model=PyPSANetworkInfoDetailResponse, # Use the detailed response model
            summary="Get Detailed Information for a Specific PyPSA Network File")
async def get_network_info_api(
    project_name: str = FastAPIPath(..., description="Project name"),
    scenario_name: str = FastAPIPath(..., description="Scenario name containing the network file"),
    network_file_name: str = FastAPIPath(..., description="The .nc network file name (e.g., 'results_2025.nc')"),
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        info = await service.get_network_info(project_name, scenario_name, network_file_name)
        return info # Service method should return data compatible with PyPSANetworkInfoDetailResponse
    except FileNotFoundError as e: # Raised by service if path is wrong or network not found
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e: # Raised by service if loading/processing fails
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting PyPSA network info for {project_name}/{scenario_name}/{network_file_name}")
        raise HTTPException(status_code=500, detail=f"Failed to get network info: {str(e)}")

@router.post("/{project_name}/compare_networks",
             response_model=PyPSAComparisonResponse, # Use the new response model
             summary="Compare Multiple PyPSA Networks")
async def compare_pypsa_networks_api(
    project_name: str = FastAPIPath(..., description="Project name under which networks reside"),
    payload: PyPSAComparisonRequest, # Uses the new request model
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    # The payload contains project_name, but we also have it as a path parameter.
    # Ensure consistency or decide which one to use (path param is conventional for resource scoping).
    # For now, assuming service will use the project_name from its own context or path.
    # The PyPSAComparisonRequest model's project_name might be redundant if always using path param.
    if payload.project_name != project_name:
        raise HTTPException(status_code=400, detail="Project name in payload does not match path parameter.")

    try:
        results = await service.compare_networks_data(
            project_name=project_name, # Use path parameter
            network_specs= [spec.model_dump() for spec in payload.network_specs], # Convert Pydantic to dict list
            comparison_func_name=payload.comparison_function_name,
            params=payload.parameters
        )
        return PyPSAComparisonResponse(comparison_results=results, metadata={"comparison_type": payload.comparison_function_name})
    except ValueError as e: # For issues like < 2 networks, invalid spec
        raise HTTPException(status_code=400, detail=str(e))
    except AttributeError as e: # For invalid comparison_func_name
        raise HTTPException(status_code=400, detail=str(e))
    except ProcessingError as e: # For issues during comparison logic in service
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error comparing PyPSA networks for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Network comparison failed: {str(e)}")

@router.get("/system_status",
            response_model=PyPSASystemStatusResponse, # Use the new response model
            summary="Get PyPSA Service System Status (Cache, Jobs)")
async def get_pypsa_system_status_api(
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        status = await service.get_pypsa_system_status()
        return status
    except Exception as e:
        logger.exception("Error getting PyPSA system status")
        raise HTTPException(status_code=500, detail=f"Failed to get PyPSA system status: {str(e)}")


logger.info("PyPSA API router updated for FastAPI with Job Management, Network Listing, Info, Comparison, and System Status.")
print("PyPSA API router updated for FastAPI with Job Management, Network Listing, Info, Comparison, and System Status.")
