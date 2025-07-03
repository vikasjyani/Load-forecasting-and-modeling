# fastapi-energy-platform/app/models/loadprofile_analysis.py
"""
Pydantic models for Load Profile Analysis features.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

# Re-using some common structures if applicable, or define new ones.
# from app.models.common import ...
# from app.models.loadprofile import LoadProfileCategory # Example

class ProfileIdentifier(BaseModel):
    project_name: str
    profile_id: str

class AnalysisRequestBase(ProfileIdentifier):
    unit: Optional[str] = Field(default="kW", description="Unit for analysis results if applicable.")
    # Add common filters like date range if needed for most analyses
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class StatisticalSummary(BaseModel):
    min_value: float
    max_value: float
    mean_value: float
    median_value: float
    std_dev: float
    q1_value: float # 25th percentile
    q3_value: float # 75th percentile
    total_sum: Optional[float] = None # e.g. total energy kWh
    count: int
    duration_hours: Optional[float] = None # If applicable
    load_factor: Optional[float] = None # If applicable (avg/peak)

class ProfileAnalysisResult(BaseModel):
    profile_id: str
    analysis_type: str
    parameters_used: Optional[Dict[str, Any]] = None
    summary: Optional[Dict[str, Any]] = None # For generic key-value summaries
    chart_data: Optional[Dict[str, Any]] = None # For data structured for charts
    detailed_results: Optional[Any] = None # Could be list of dicts, or more specific model
    error: Optional[str] = None

class AvailableProfileForAnalysis(BaseModel):
    profile_id: str
    project_name: str # Assuming profiles are project-specific
    # Add other relevant metadata from LoadProfileService.list_saved_profiles if needed
    method_used: Optional[str] = None
    created_at: Optional[datetime] = None
    years_generated: Optional[List[int]] = None
    frequency: Optional[str] = None
    file_info: Optional[Dict[str, Any]] = None
    quick_validation_status: Optional[Dict[str, Any]] = None # e.g. {'valid': True, 'issues': []}

class ProfileComparisonRequest(BaseModel):
    project_name: str
    profile_ids: List[str] = Field(..., min_items=2, max_items=5)
    comparison_type: str = Field(default="overview", description="Type of comparison, e.g., 'overview', 'statistical', 'seasonal'")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters for the comparison, e.g., unit, metrics")

class ProfileComparisonResult(BaseModel):
    profile_ids_compared: List[str]
    comparison_type: str
    comparison_data: Dict[str, Any] # Structure will depend on comparison_type
    # Example: {"profile1_vs_profile2": {"peak_diff_percent": 10.5, ...}}

class BatchAnalysisRequest(BaseModel):
    project_name: str
    profile_ids: List[str] = Field(..., min_items=1, max_items=10)
    analysis_types: List[str] = Field(..., min_items=1, description="List of analysis types to perform on each profile")
    common_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Common parameters for all analyses")

class BatchAnalysisResponse(BaseModel):
    project_name: str
    results: List[ProfileAnalysisResult] # One result object per profile per analysis type
    summary: Dict[str, int] # e.g. {"total_analyses_run": X, "successful": Y, "failed": Z}

# Add more specific models as analysis types are implemented, e.g., for PeakAnalysisResult, DecompositionResult etc.
logger_models = logging.getLogger(__name__)
logger_models.info("Load Profile Analysis Pydantic models defined.")
