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
# For now, direct loading or a very simple cache.
_network_cache: Dict[str, pypsa.Network] = {}
_network_mtimes: Dict[str, float] = {}

async def get_network(project_name: str, scenario_name: str, network_filename: str) -> pypsa.Network:
    # This path construction needs to be robust and configurable
    # base_path = Path("user_projects_data") / project_name / "results" / "PyPSA_Modeling" / scenario_name
    # For now, assume network_filename IS the scenario_name for .nc files
    # and project_name is part of the base path.
    # The structure from original pypsa_bp used network_rel_path which was scenario_name/results_year/network.nc
    # This needs to be harmonized. Let's assume for now network_filename is like "scenario_year_network.nc"
    # and it's directly under project_name/results/PyPSA_Modeling/

    # This needs to align with where `run_pypsa_model_core` saves NetCDF files.
    # The core runner saves to project_path/results/PyPSA_Modeling/scenario_name/scenario_name_year_network.nc
    # So, network_filename should probably be scenario_name_year_network.nc
    # And the API path might include scenario_name and year or just the full filename.

    # Let's simplify: the API will take project_name, scenario_name, and year.
    # The service will construct the expected .nc file path.
    pypsa_results_base = Path("user_projects_data") / project_name / "results" / "PyPSA_Modeling"
    nc_file_path = pypsa_results_base / scenario_name / f"{scenario_name}_{network_filename}.nc" # network_filename here could be year

    if not nc_file_path.exists():
        raise ResourceNotFoundError(resource_type="PyPSA Network", resource_id=str(nc_file_path))

    current_mtime = nc_file_path.stat().st_mtime
    if str(nc_file_path) in _network_cache and _network_mtimes.get(str(nc_file_path)) == current_mtime:
        logger.info(f"Cache hit for network: {nc_file_path}")
        return _network_cache[str(nc_file_path)]

    logger.info(f"Loading PyPSA network: {nc_file_path}")
    try:
        # network = await asyncio.to_thread(pypsa.Network, str(nc_file_path)) # If pypsa.Network() is blocking
        network = pypsa.Network(str(nc_file_path)) # Assuming sync for now
        _network_cache[str(nc_file_path)] = network
        _network_mtimes[str(nc_file_path)] = current_mtime
        if len(_network_cache) > 3: # Simple cache size limit
            oldest_key = next(iter(_network_cache))
            del _network_cache[oldest_key]
            del _network_mtimes[oldest_key]
        return network
    except Exception as e:
        logger.exception(f"Error loading network {nc_file_path}")
        raise ProcessingError(message=f"Failed to load PyPSA network: {str(e)}")


# --- Pydantic Models ---
class PyPSAJobRunPayload(BaseModel):
    project_name: str
    scenario_name: str = Field(..., min_length=1, max_length=100)
    # Include other settings that can be overridden from UI
    # e.g., snapshot_condition, weightings_freq_hours, base_year_config, etc.
    # For now, keeping it simple, assuming most settings come from Excel.
    ui_settings_overrides: Dict[str, Any] = Field(default_factory=dict)

class PyPSADataRequest(BaseModel):
    # project_name: str # Will be path param
    # scenario_name: str # Will be path param
    network_file_identifier: str # e.g., "2025" for year, or full "scenario_2025_network"
    extraction_function: str
    filters: Optional[Dict[str, Any]] = None
    kwargs: Optional[Dict[str, Any]] = None


# --- API Endpoints ---
# Note: HTML rendering routes from Flask blueprint are omitted.

@router.post("/run_model", status_code=202, summary="Run PyPSA Optimization Model")
async def run_pypsa_model_api(
    payload: PyPSAJobRunPayload,
    background_tasks: BackgroundTasks,
    # settings: AppSettings = Depends(get_app_settings) # If needed for project_path base
):
    """
    Triggers a PyPSA model optimization run for a given project and scenario.
    The job runs in the background. Use the returned job_id to track status.
    `ui_settings_overrides` can be used to pass settings from the UI that override
    those in the PyPSA input Excel template.
    """
    job_id = str(uuid.uuid4())
    project_data_root = Path("user_projects_data") # This should come from settings
    project_path_str = str(project_data_root / payload.project_name)

    pypsa_jobs[job_id] = {
        "id": job_id, "status": "Queued", "progress": 0, "log": [],
        "scenario_name": payload.scenario_name, "project_path": project_path_str,
        "start_time": datetime.now().isoformat()
    }

    # run_pypsa_model_core is synchronous and CPU-bound.
    # It should be run in a separate process or thread pool to not block FastAPI.
    # BackgroundTasks.add_task runs it in the same event loop if the function is async,
    # or in a threadpool if the function is sync (FastAPI default for sync route handlers).
    # For truly CPU-bound tasks, ProcessPoolExecutor is better if GIL is an issue.
    # For now, using BackgroundTasks which will use a threadpool for the sync function.
    background_tasks.add_task(
        run_pypsa_model_core,
        job_id,
        project_path_str,
        payload.scenario_name,
        payload.ui_settings_overrides,
        pypsa_jobs # Pass the shared job store
    )

    logger.info(f"PyPSA job {job_id} queued for project '{payload.project_name}', scenario '{payload.scenario_name}'.")
    return {
        "message": "PyPSA model run initiated.",
        "job_id": job_id,
        "status_url": f"/api/v1/pypsa/job_status/{job_id}" # Example
    }

@router.get("/job_status/{job_id}", summary="Get PyPSA Job Status")
async def get_pypsa_job_status_api(job_id: str):
    job = pypsa_jobs.get(job_id)
    if not job:
        raise ResourceNotFoundError(resource_type="PyPSA Job", resource_id=job_id)
    # Potentially add more details like elapsed time, current step from job dict
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress"),
        "current_step": job.get("current_step"),
        "log_summary": job.get("log", [])[-5:], # Last 5 log entries
        "error": job.get("error")
    }

@router.get("/{project_name}/scenario/{scenario_name}/network/{network_file_id}/extract_data", summary="Extract Data from PyPSA Network")
async def extract_pypsa_data_api(
    project_name: str = FastAPIPath(..., description="Project name"),
    scenario_name: str = FastAPIPath(..., description="Scenario name within the project"),
    network_file_id: str = FastAPIPath(..., description="Identifier for the network file (e.g., year or full name part)"),
    extraction_func_name: str = Query(..., description="Name of the extraction function from pypsa_analysis_utils"),
    # Filters and kwargs can be passed as part of the query string or a JSON body if complex
    # For simplicity with GET, using Query for some common filters.
    resolution: Optional[str] = Query("1H", description="Time resolution for data, e.g., '1H', 'D', 'W', 'M', 'Y'"),
    period: Optional[str] = Query(None, description="Specific period/year if network is multi-period"),
    # For more complex filters/kwargs, a POST with JSON body would be better.
    # For now, we assume they are simple enough for query or handled by service defaults.
):
    try:
        network = await get_network(project_name, scenario_name, network_file_id)

        if not hasattr(pau, extraction_func_name):
            raise CustomValidationError(message=f"Unknown extraction function: {extraction_func_name}")

        func_to_call = getattr(pau, extraction_func_name)

        # Prepare arguments for the extraction function
        # Snapshots slice can be derived from query params if needed (e.g. start_date, end_date)
        # For now, passing None, which means all snapshots in the loaded network.
        # This is where filters and kwargs from the request would be processed.
        call_kwargs = {"resolution": resolution, "period": period} # Example

        # Data extraction functions in pau might be sync; run in threadpool.
        # result_data = await asyncio.to_thread(func_to_call, n=network, snapshots_slice=None, **call_kwargs)
        result_data = func_to_call(n=network, snapshots_slice=None, **call_kwargs) # Assuming sync for now

        # Color palette
        colors = {}
        if hasattr(pau, 'get_color_palette'):
            colors = pau.get_color_palette(network)

        return {
            "data": result_data, # pau functions should return JSON-serializable dicts
            "colors": colors,
            "metadata": {
                "project": project_name, "scenario": scenario_name, "network_file": network_file_id,
                "extraction_function": extraction_func_name, "params": call_kwargs
            }
        }
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e.detail if isinstance(e.detail, str) else e.detail.get("message")))
    except CustomValidationError as e:
        raise HTTPException(status_code=422, detail=e.detail)
    except Exception as e:
        logger.exception(f"Error extracting PyPSA data for {project_name}/{scenario_name}/{network_file_id}")
        raise HTTPException(status_code=500, detail=f"Data extraction failed: {str(e)}")


# Omitted: /api/available_networks, /api/system_status from Flask blueprint.
# These would involve scanning filesystem or system introspection, which can be complex
# and might be better suited for an admin/management part of the API or a separate service.

logger.info("PyPSA API router defined for FastAPI.")
print("PyPSA API router defined for FastAPI.")
