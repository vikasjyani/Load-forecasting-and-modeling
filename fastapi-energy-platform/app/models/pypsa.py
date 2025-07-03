# fastapi-energy-platform/app/models/pypsa.py
"""
Pydantic models for PyPSA operations.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

# --- Request Models ---

class PyPSAJobRunPayload(BaseModel):
    project_name: str = Field(..., description="Name of the project.")
    scenario_name: str = Field(..., min_length=1, max_length=100, description="Name of the PyPSA scenario to run/create.")
    # Further configuration options for the PyPSA run can be added here.
    # These might override settings typically found in an Excel input file.
    ui_settings_overrides: Dict[str, Any] = Field(default_factory=dict, description="Settings from UI to override defaults or Excel inputs.")
    # Example: {"snapshots": "2023-01-01/2023-01-07", "solver_name": "glpk"}

class PyPSADataExtractionRequest(BaseModel):
    network_file_identifier: str = Field(..., description="Identifier for the network file (e.g., year, specific run name part like '2025_results').")
    network_file_name: str = Field(..., description="Name of the .nc network file (e.g., 'results_2025.nc', 'network.nc').")
    extraction_function_name: str = Field(..., description="Name of the data extraction function in pypsa_analysis_utils.")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Filters for data extraction (e.g., date range, components).")
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional keyword arguments for the extraction function.")

class PyPSANetworkSpecifier(BaseModel):
    scenario_name: str
    network_file_name: str # The specific .nc file
    label: Optional[str] = None # Custom label for this network in comparison results

class PyPSAComparisonRequest(BaseModel):
    project_name: str # Path parameter in API, but good to have for service layer if it processes this directly
    network_specs: List[PyPSANetworkSpecifier] = Field(..., min_items=2)
    comparison_function_name: str = Field(..., description="Name of the comparison function in pypsa_analysis_utils, e.g., 'compare_networks_results'")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters for the comparison function.")


# --- Response Models ---

class PyPSAJobStatusResponse(BaseModel):
    id: str
    project_name: str
    scenario_name: str
    status: str
    progress: int
    current_step: Optional[str] = None
    start_time_iso: str
    end_time_iso: Optional[str] = None
    log_summary: Optional[List[str]] = None # e.g., last few log messages
    error_message: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None

class PyPSANetworkSnapshotInfo(BaseModel):
    count: int
    start: Optional[str] = None
    end: Optional[str] = None
    freq: Optional[str] = None

class PyPSAComponentModel(BaseModel):
    count: int
    columns: List[str]

class PyPSANetworkInfoDetailResponse(BaseModel): # More detailed than PyPSANetworkInfoResponse
    file_name: str
    full_path_on_server: str # For debug, might not be in final client response
    snapshots: PyPSANetworkSnapshotInfo
    components: Dict[str, PyPSAComponentModel]
    objective_value: Optional[float] = None

class PyPSANetworkInfoResponse(BaseModel): # For listing available networks
    name: str
    relative_path: str
    full_path: str
    size_mb: Optional[float] = None
    last_modified_iso: Optional[str] = None
    # snapshot_count: Optional[int] = None # Removed as it requires loading network; get via DetailResponse

class PyPSANetworkListResponse(BaseModel):
    project_name: str
    scenario_name: Optional[str] = None # If listing for a specific scenario
    networks: List[PyPSANetworkInfoResponse]

class PyPSADataResponse(BaseModel):
    data: Dict[str, Any] # The extracted data, structure depends on extraction_func
    colors: Optional[Dict[str, str]] = None # Optional color palette
    metadata: Dict[str, Any]

class PyPSAComparisonResponse(BaseModel):
    # The structure of this will depend heavily on the output of pau.compare_networks_results
    # Assuming it returns a dictionary that can be directly used or needs specific modeling.
    # For now, a generic Dict.
    comparison_results: Dict[str, Any]
    metadata: Dict[str, Any] # e.g., networks_compared, comparison_type, parameters_used

class PyPSACacheItemInfo(BaseModel):
    path: str
    mtime: float
    # Could add size_in_memory if tracked by a more advanced cache manager

class PyPSASystemStatusResponse(BaseModel):
    network_cache_current_size: int
    network_cache_max_size: Union[int, str] # Can be int or "Not Set"
    cached_network_files_info: List[PyPSACacheItemInfo]
    active_simulation_jobs: int
    job_manager_status: str

# Add other models as PyPSA functionalities are built out
logger_models = logging.getLogger(__name__) # Using default logger for messages from this file
logger_models.info("PyPSA Pydantic models defined.")
