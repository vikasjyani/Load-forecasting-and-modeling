# fastapi-energy-platform/app/api/v1/pypsa.py
"""
PyPSA API Endpoints for FastAPI.
Handles PyPSA model execution, data extraction, and results visualization.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Body, Query, Path as FastAPIPath, BackgroundTasks
from pathlib import Path

# Service and Pydantic models
from app.services.pypsa_service import PypsaService
from app.dependencies import get_pypsa_service as get_pypsa_service_dependency
from app.models.pypsa import (
    PyPSAJobRunPayload,
    PyPSAJobStatusResponse,
    PyPSANetworkListResponse,
    PyPSANetworkInfoResponse, # Used by PyPSANetworkListResponse
    PyPSANetworkInfoDetailResponse,
    PyPSADataExtractionRequest,
    PyPSADataResponse,
    PyPSAComparisonRequest,
    PyPSAComparisonResponse,
    PyPSASystemStatusResponse
)
from app.utils.error_handlers import ProcessingError, ResourceNotFoundError, ValidationError as CustomValidationError


logger = logging.getLogger(__name__)
router = APIRouter()

# --- API Endpoints ---

@router.post("/run_simulation", status_code=202, response_model=PyPSAJobStatusResponse, summary="Run PyPSA Optimization Model")
async def run_pypsa_simulation_api(
    payload: PyPSAJobRunPayload, # project_name is in payload
    background_tasks: BackgroundTasks,
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        job = await service.run_pypsa_simulation(
            project_name=payload.project_name,
            scenario_name=payload.scenario_name,
            ui_settings_overrides=payload.ui_settings_overrides,
            background_tasks=background_tasks
        )
        # Convert PyPSAJob dataclass from service to PyPSAJobStatusResponse Pydantic model
        return PyPSAJobStatusResponse(**vars(job))
    except Exception as e:
        logger.exception(f"Error initiating PyPSA simulation for project {payload.project_name}, scenario {payload.scenario_name}")
        raise HTTPException(status_code=500, detail=f"Failed to start PyPSA simulation: {str(e)}")

@router.get("/job_status/{job_id}", response_model=PyPSAJobStatusResponse, summary="Get PyPSA Job Status")
async def get_pypsa_job_status_api(
    job_id: str = FastAPIPath(..., description="ID of the PyPSA simulation job"),
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    job = await service.get_simulation_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"PyPSA Job with ID '{job_id}' not found.")
    return PyPSAJobStatusResponse(**vars(job))

@router.get("/{project_name}/networks", response_model=PyPSANetworkListResponse, summary="List Available PyPSA Networks/Scenarios")
async def list_available_networks_api(
    project_name: str = FastAPIPath(..., description="The name of the project"),
    scenario_name: Optional[str] = Query(None, description="Optional: Specific scenario name to list its .nc network files. If None, lists scenario folders."),
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        network_infos_dataclasses = await service.list_available_network_files(project_name, scenario_name)
        # Convert list of PyPSANetworkInfo dataclasses to list of PyPSANetworkInfoResponse Pydantic models
        response_networks = [PyPSANetworkInfoResponse(**vars(info)) for info in network_infos_dataclasses]
        return PyPSANetworkListResponse(project_name=project_name, scenario_name=scenario_name, networks=response_networks)
    except Exception as e:
        logger.exception(f"Error listing PyPSA networks for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Failed to list networks: {str(e)}")

@router.get("/{project_name}/scenario/{scenario_name}/network/{network_file_name}/info",
            response_model=PyPSANetworkInfoDetailResponse,
            summary="Get Detailed Information for a Specific PyPSA Network File")
async def get_network_info_api(
    project_name: str = FastAPIPath(..., description="Project name"),
    scenario_name: str = FastAPIPath(..., description="Scenario name containing the network file"),
    network_file_name: str = FastAPIPath(..., description="The .nc network file name (e.g., 'results_2025.nc', 'network.nc')"),
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        info = await service.get_network_info(project_name, scenario_name, network_file_name)
        return info
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting PyPSA network info for {project_name}/{scenario_name}/{network_file_name}")
        raise HTTPException(status_code=500, detail=f"Failed to get network info: {str(e)}")

@router.post("/{project_name}/scenario/{scenario_name}/network/{network_file_name}/extract_data",
             response_model=PyPSADataResponse,
             summary="Extract Data from a Specific PyPSA Network")
async def extract_pypsa_data_api(
    project_name: str = FastAPIPath(..., description="Project name"),
    scenario_name: str = FastAPIPath(..., description="Scenario name"),
    network_file_name: str = FastAPIPath(..., description="Network file name (e.g., 'network.nc')"),
    payload: PyPSADataExtractionRequest, # Contains extraction_func_name, filters, kwargs
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    try:
        # The payload's network_file_name might be redundant if we always use the path param.
        # For now, service uses path param. Payload's network_file_name is ignored.
        extracted_data_dict = await service.get_network_data(
            project_name, scenario_name, network_file_name,
            payload.extraction_function_name, payload.filters, **payload.kwargs
        )
        return PyPSADataResponse(**extracted_data_dict)
    except FileNotFoundError as e: # From service._load_pypsa_network
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e: # From invalid extraction_func_name or bad filters/kwargs in service
        raise HTTPException(status_code=422, detail=str(e))
    except ProcessingError as e: # From pau function execution error
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error extracting PyPSA data for {project_name}/{scenario_name}/{network_file_name}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")

@router.post("/{project_name}/compare_networks",
             response_model=PyPSAComparisonResponse,
             summary="Compare Multiple PyPSA Networks")
async def compare_pypsa_networks_api(
    project_name: str = FastAPIPath(..., description="Project name under which networks reside"),
    payload: PyPSAComparisonRequest,
    service: PypsaService = Depends(get_pypsa_service_dependency)
):
    if payload.project_name != project_name: # Ensure consistency
        raise HTTPException(status_code=400, detail="Project name in payload must match path parameter.")
    try:
        results = await service.compare_networks_data(
            project_name=project_name,
            network_specs= [spec.model_dump() for spec in payload.network_specs],
            comparison_func_name=payload.comparison_function_name,
            params=payload.parameters
        )
        # The service returns the data that should directly map to PyPSAComparisonResponse.comparison_results
        return PyPSAComparisonResponse(
            comparison_results=results,
            metadata={ # Construct metadata here
                "project_name": project_name,
                "networks_compared_labels": [spec.label or f"{spec.scenario_name}/{spec.network_file_name}" for spec in payload.network_specs],
                "comparison_function": payload.comparison_function_name,
                "parameters_used": payload.parameters,
                "timestamp": datetime.now().isoformat()
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AttributeError as e:
        raise HTTPException(status_code=400, detail=f"Comparison function error: {str(e)}")
    except ProcessingError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Error comparing PyPSA networks for project {project_name}")
        raise HTTPException(status_code=500, detail=f"Network comparison failed: {str(e)}")

@router.get("/system_status",
            response_model=PyPSASystemStatusResponse,
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

logger.info("PyPSA API router finalized for FastAPI.")
print("PyPSA API router finalized for FastAPI.")
