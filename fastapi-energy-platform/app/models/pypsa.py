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
    extraction_function_name: str = Field(..., description="Name of the data extraction function in pypsa_analysis_utils.")
    filters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Filters for data extraction (e.g., date range, components).")
    kwargs: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional keyword arguments for the extraction function.")


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

class PyPSANetworkInfoResponse(BaseModel):
    name: str
    relative_path: str
    full_path: str # For server-side reference, might not be exposed directly to client always
    size_mb: Optional[float] = None
    last_modified_iso: Optional[str] = None
    snapshot_count: Optional[int] = None
    # components_summary: Optional[Dict[str, int]] = None

class PyPSANetworkListResponse(BaseModel):
    project_name: str
    scenario_name: Optional[str] = None # If listing for a specific scenario
    networks: List[PyPSANetworkInfoResponse]

class PyPSADataResponse(BaseModel):
    data: Dict[str, Any] # The extracted data, structure depends on extraction_func
    colors: Optional[Dict[str, str]] = None # Optional color palette
    metadata: Dict[str, Any]

# Add other models as PyPSA functionalities are built out (e.g., for comparison results)
logger_models = logging.getLogger(__name__) # Using default logger for messages from this file
logger_models.info("PyPSA Pydantic models defined.")
